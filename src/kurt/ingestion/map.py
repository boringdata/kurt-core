"""
URL discovery and mapping functions for Kurt.

This module handles discovering URLs from various sources:
- Sitemaps (sitemap.xml files)
- Blogroll pages (blog indexes, release notes, changelogs)
- LLM-powered extraction of chronological content

Key Functions:
- map_sitemap: Discover URLs from sitemap
- map_blogrolls: Discover URLs from blogroll/changelog pages (with dates)
- identify_blogroll_candidates: Find potential blogroll pages from sitemap URLs
- extract_chronological_content: LLM-powered extraction of posts from HTML pages
"""

import logging
import re
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path
from urllib.parse import urljoin, urlparse

import dspy
import httpx
import trafilatura
from dspy import ChainOfThought, Signature
from pydantic import BaseModel, Field

from kurt.db.database import get_session
from kurt.db.models import Document, IngestionStatus, SourceType

logger = logging.getLogger(__name__)


def normalize_url(url: str) -> str:
    """
    Normalize URL by removing anchors and query strings.

    This prevents duplicate documents from being created for URLs that
    only differ by anchor or query parameters.

    Args:
        url: URL to normalize

    Returns:
        Normalized URL without anchor or query string

    Example:
        >>> normalize_url("https://example.com/blog?page=1#latest")
        "https://example.com/blog"
        >>> normalize_url("https://example.com/blog")
        "https://example.com/blog"
    """
    from urllib.parse import urlparse, urlunparse

    parsed = urlparse(url)
    # Remove fragment (anchor) and query string
    normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
    return normalized


# ============================================================================
# Sitemap Discovery
# ============================================================================


def _discover_sitemap_urls(base_url: str) -> list[str]:
    """
    Discover sitemap URLs using httpx (reliable fetching).

    Workflow:
    1. Check robots.txt for sitemap location
    2. Try common sitemap URLs (/sitemap.xml, /sitemap_index.xml)
    3. Parse sitemap XML to extract URLs

    Args:
        base_url: Base URL to search for sitemaps

    Returns:
        List of URLs found in sitemap(s)

    Raises:
        ValueError: If no sitemap found or accessible
    """
    import xml.etree.ElementTree as ET
    from urllib.parse import urlparse

    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    sitemap_urls = []

    # Step 1: Check robots.txt
    try:
        response = httpx.get(f"{base}/robots.txt", timeout=10.0, follow_redirects=True)
        if response.status_code == 200:
            for line in response.text.split("\n"):
                if line.lower().startswith("sitemap:"):
                    sitemap_url = line.split(":", 1)[1].strip()
                    sitemap_urls.append(sitemap_url)
    except Exception:
        pass  # robots.txt not found or not accessible

    # Step 2: Try common sitemap locations
    common_paths = ["/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml"]
    for path in common_paths:
        if f"{base}{path}" not in sitemap_urls:
            sitemap_urls.append(f"{base}{path}")

    # Step 3: Fetch and parse sitemaps
    all_urls = []

    for sitemap_url in sitemap_urls:
        try:
            response = httpx.get(sitemap_url, timeout=30.0, follow_redirects=True)
            if response.status_code != 200:
                continue

            # Parse XML
            root = ET.fromstring(response.content)

            # Check if it's a sitemap index (contains <sitemap> tags)
            sitemaps = root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap")
            if sitemaps:
                # It's a sitemap index - recursively fetch child sitemaps
                for sitemap in sitemaps:
                    loc = sitemap.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
                    if loc is not None and loc.text:
                        child_sitemap_url = loc.text.strip()
                        try:
                            child_response = httpx.get(
                                child_sitemap_url, timeout=30.0, follow_redirects=True
                            )
                            if child_response.status_code == 200:
                                child_root = ET.fromstring(child_response.content)
                                urls = child_root.findall(
                                    ".//{http://www.sitemaps.org/schemas/sitemap/0.9}url"
                                )
                                for url_elem in urls:
                                    loc_elem = url_elem.find(
                                        "{http://www.sitemaps.org/schemas/sitemap/0.9}loc"
                                    )
                                    if loc_elem is not None and loc_elem.text:
                                        all_urls.append(loc_elem.text.strip())
                        except Exception:
                            continue
            else:
                # It's a regular sitemap - extract URLs
                urls = root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}url")
                for url_elem in urls:
                    loc = url_elem.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
                    if loc is not None and loc.text:
                        all_urls.append(loc.text.strip())

            # If we found URLs, we're done
            if all_urls:
                return all_urls

        except Exception:
            continue  # Try next sitemap URL

    # No sitemap found
    if not all_urls:
        raise ValueError(f"No sitemap found for {base_url}")

    return all_urls


def crawl_website(
    homepage: str,
    max_depth: int = 2,
    max_pages: int = 100,
    allow_external: bool = False,
    include_patterns: tuple = (),
    exclude_patterns: tuple = (),
) -> list[str]:
    """
    Crawl a website using trafilatura's focused_crawler.

    This is used as a fallback when no sitemap is found or when explicit
    crawling is requested with --max-depth.

    Args:
        homepage: Starting URL for crawl
        max_depth: Maximum crawl depth (approximate - trafilatura uses max_seen_urls)
        max_pages: Maximum number of pages to discover
        allow_external: If True, follow external links (outside domain)
        include_patterns: Include URL patterns (glob)
        exclude_patterns: Exclude URL patterns (glob)

    Returns:
        List of discovered URLs (strings)

    Note:
        - Trafilatura's focused_crawler doesn't have explicit depth control,
          so we use max_seen_urls as a proxy for depth
        - The crawler automatically respects robots.txt
        - Navigation pages (archives, categories) are prioritized
    """
    from fnmatch import fnmatch
    from urllib.parse import urlparse

    from trafilatura.spider import focused_crawler

    # Convert max_depth to max_seen_urls
    # Depth 1 = ~10 URLs, Depth 2 = ~50 URLs, Depth 3+ = ~100+ URLs
    depth_to_urls = {
        1: 10,
        2: 50,
        3: 100,
    }
    max_seen_urls = depth_to_urls.get(max_depth, max_depth * 50) if max_depth else 100
    max_seen_urls = min(max_seen_urls, max_pages)  # Respect max_pages limit

    logger.info(f"Crawling {homepage} with max_seen_urls={max_seen_urls} (depth={max_depth})")

    # Run focused crawler
    to_visit, known_links = focused_crawler(
        homepage=homepage,
        max_seen_urls=max_seen_urls,
        max_known_urls=max_pages,
    )

    # Convert to list
    all_urls = list(known_links)

    # Filter external links if not allowed
    if not allow_external:
        homepage_domain = urlparse(homepage).netloc
        filtered_urls = []
        for url in all_urls:
            url_domain = urlparse(url).netloc
            if url_domain == homepage_domain:
                filtered_urls.append(url)
        all_urls = filtered_urls
        logger.info(f"Filtered to {len(all_urls)} internal URLs (allow_external=False)")

    # Apply include/exclude patterns
    if include_patterns:
        filtered = []
        for url in all_urls:
            if any(fnmatch(url, pattern) for pattern in include_patterns):
                filtered.append(url)
        all_urls = filtered
        logger.info(f"Applied include patterns: {len(all_urls)} URLs match")

    if exclude_patterns:
        filtered = []
        for url in all_urls:
            if not any(fnmatch(url, pattern) for pattern in exclude_patterns):
                filtered.append(url)
        all_urls = filtered
        logger.info(f"Applied exclude patterns: {len(all_urls)} URLs remain")

    # Apply final limit
    if len(all_urls) > max_pages:
        all_urls = all_urls[:max_pages]
        logger.info(f"Limited to {max_pages} URLs")

    logger.info(f"Crawling discovered {len(all_urls)} URLs")
    return all_urls


def map_sitemap(
    url: str,
    fetch_all: bool = False,
    limit: int = None,
    discover_blogrolls: bool = False,
    max_blogrolls: int = 10,
    llm_model: str = "openai/gpt-4o-mini",
    include_patterns: tuple = (),
    exclude_patterns: tuple = (),
) -> list[dict]:
    """
    Discover sitemap and create documents in database with NOT_FETCHED status.

    Uses trafilatura's sitemap_search() which handles:
    - Common sitemap locations (/sitemap.xml, etc.)
    - Sitemap indexes (nested sitemaps)
    - robots.txt parsing
    - URL normalization

    Args:
        url: Base URL or specific sitemap URL
        fetch_all: If True, fetch content for all documents immediately
        limit: Maximum number of URLs to process (creates + fetches only this many)
        discover_blogrolls: If True, also discover posts from blogroll/changelog pages
        max_blogrolls: Maximum number of blogroll pages to scrape (if discover_blogrolls=True)
        llm_model: LLM model to use for blogroll extraction

    Returns:
        List of created documents with keys:
            - document_id: UUID
            - url: str
            - title: str
            - status: str ('NOT_FETCHED' or 'FETCHED' if fetch_all=True)
            - is_chronological: bool (only if discovered from blogroll)
            - discovery_method: str (only if discovered from blogroll)

    Raises:
        ValueError: If no sitemap found

    Example:
        # Basic sitemap mapping
        docs = map_sitemap("https://example.com")

        # With blogroll discovery
        docs = map_sitemap("https://example.com", discover_blogrolls=True)
        # Returns sitemap docs + additional posts found on blogroll pages
    """
    from sqlmodel import select

    # Import fetch functions here to avoid circular imports
    from kurt.ingestion.fetch import fetch_document

    # Use custom sitemap discovery (more reliable than trafilatura)
    urls = _discover_sitemap_urls(url)

    # Apply filters
    from fnmatch import fnmatch

    if include_patterns:
        filtered = []
        for discovered_url in urls:
            if any(fnmatch(discovered_url, pattern) for pattern in include_patterns):
                filtered.append(discovered_url)
        urls = filtered

    if exclude_patterns:
        filtered = []
        for discovered_url in urls:
            if not any(fnmatch(discovered_url, pattern) for pattern in exclude_patterns):
                filtered.append(discovered_url)
        urls = filtered

    # Apply limit to URL processing
    if limit:
        urls = list(urls)[:limit]

    session = get_session()
    created_docs = []

    for discovered_url in urls:
        # Check if document already exists
        stmt = select(Document).where(Document.source_url == discovered_url)
        existing_doc = session.exec(stmt).first()

        if existing_doc:
            # Skip if already exists
            created_docs.append(
                {
                    "document_id": existing_doc.id,
                    "url": existing_doc.source_url,
                    "title": existing_doc.title,
                    "status": existing_doc.ingestion_status.value,
                    "created": False,
                    "fetched": False,
                }
            )
            continue

        # Generate title from URL
        title = discovered_url.rstrip("/").split("/")[-1] or discovered_url

        # Create document
        doc = Document(
            title=title,
            source_type=SourceType.URL,
            source_url=discovered_url,
            ingestion_status=IngestionStatus.NOT_FETCHED,
            discovery_method="sitemap",
            discovery_url=url,  # The sitemap URL
        )

        session.add(doc)
        session.commit()
        session.refresh(doc)

        doc_result = {
            "document_id": doc.id,
            "url": doc.source_url,
            "title": doc.title,
            "status": doc.ingestion_status.value,
            "created": True,
            "fetched": False,
        }

        # Fetch content if requested
        if fetch_all:
            try:
                fetch_result = fetch_document(str(doc.id))
                doc_result["status"] = fetch_result["status"]
                doc_result["fetched"] = True
                doc_result["content_length"] = fetch_result["content_length"]
            except Exception as e:
                # Continue on fetch errors
                doc_result["fetch_error"] = str(e)

        created_docs.append(doc_result)

    # Optionally discover additional posts from blogroll/changelog pages
    if discover_blogrolls:
        print("\n--- Discovering blogroll/changelog pages ---")
        sitemap_urls = [doc["url"] for doc in created_docs]
        blogroll_docs = map_blogrolls(
            sitemap_urls,
            llm_model=llm_model,
            max_blogrolls=max_blogrolls,
        )
        created_docs.extend(blogroll_docs)

    return created_docs


# ============================================================================
# Blogroll and Chronological Content Discovery
# ============================================================================

# Common URL patterns for chronological content
BLOGROLL_PATTERNS = [
    "/blog",
    "/blog/",
    "/news",
    "/news/",
    "/releases",
    "/releases/",
    "/release-notes",
    "/release-notes/",
    "/changelog",
    "/changelog/",
    "/updates",
    "/updates/",
    "/announcements",
    "/announcements/",
    "/articles",
    "/articles/",
    "/dbt-versions/",
]

# Category-level blogroll patterns
CATEGORY_PATTERNS = [
    "/blog/category/",
    "/blog/categories/",
    "/category/",
    "/categories/",
    "/tag/",
    "/tags/",
]


class ExtractedPost(BaseModel):
    """Extracted post information from chronological content page."""

    url: str = Field(description="Full URL to the post/document")
    title: str = Field(description="Title of the post")
    date: str | None = Field(
        default=None, description="Published date in ISO format (YYYY-MM-DD) if found"
    )
    excerpt: str | None = Field(default=None, description="Brief excerpt or description")


class ChronologicalContentExtraction(BaseModel):
    """Collection of extracted posts from a chronological content page."""

    posts: list[ExtractedPost] = Field(description="List of posts extracted from the page")


class ExtractChronologicalContentSignature(Signature):
    """Extract chronological content (blog posts, release notes) from HTML/markdown."""

    content: str = dspy.InputField(
        desc="HTML or markdown content of a blogroll, release notes, or changelog page"
    )
    base_url: str = dspy.InputField(desc="Base URL of the page for resolving relative links")
    extraction: ChronologicalContentExtraction = dspy.OutputField(
        desc="Extracted posts with URLs, titles, dates, and excerpts"
    )


class BlogrollCandidate(BaseModel):
    """A candidate URL identified as likely containing chronological content."""

    url: str = Field(description="The full URL of the candidate page")
    type: str = Field(
        description="Type of page: 'blog_index', 'changelog', 'release_notes', 'archive', 'category', or 'tag'"
    )
    priority: int = Field(
        description="Priority score 1-10, where 10 is highest priority (main indexes, changelogs)"
    )
    reasoning: str = Field(description="Brief explanation of why this URL is a good candidate")


class BlogrollCandidateList(BaseModel):
    """List of identified blogroll/changelog candidates."""

    candidates: list[BlogrollCandidate] = Field(
        description="Prioritized list of URLs that likely contain chronological content with dates"
    )


class IdentifyBlogrollCandidatesSignature(Signature):
    """Identify URLs from a sitemap that are most likely to contain chronological content listings."""

    urls_sample: str = dspy.InputField(desc="Pre-filtered URLs from the sitemap to analyze")
    base_domain: str = dspy.InputField(desc="The base domain being analyzed (e.g., 'getdbt.com')")
    candidates: BlogrollCandidateList = dspy.OutputField(
        desc="List of ALL candidate URLs that match criteria for scraping chronological content"
    )


def identify_blogroll_candidates(
    sitemap_urls: list[str],
    llm_model: str = "openai/gpt-4o-mini",
    max_candidates: int = 20,
) -> list[dict]:
    """
    Identify potential blogroll/changelog pages from sitemap URLs using hybrid approach.

    Uses a two-stage approach:
    1. Pre-filter with pattern matching to reduce URL set
    2. LLM semantic analysis for final prioritization

    This combines efficiency of regex filtering with semantic understanding of LLMs.

    Args:
        sitemap_urls: List of URLs discovered from sitemap
        llm_model: LLM model to use for analysis (default: gpt-4o-mini)
        max_candidates: Maximum number of candidates to return (default: 20)

    Returns:
        List of candidate pages sorted by priority:
            - url: str (candidate URL)
            - type: str (blog_index, changelog, release_notes, archive, category, tag)
            - priority: int (1-10, higher = more important)
            - reasoning: str (why this is a good candidate)

    Example:
        >>> urls = [
        ...     "https://www.getdbt.com/blog",
        ...     "https://docs.getdbt.com/docs/dbt-versions/dbt-cloud-release-notes",
        ... ]
        >>> identify_blogroll_candidates(urls)
        [
            {
                "url": "https://www.getdbt.com/blog",
                "type": "blog_index",
                "priority": 10,
                "reasoning": "Main blog index page"
            },
            ...
        ]
    """
    # Normalize all URLs
    normalized_urls = list(set(normalize_url(url) for url in sitemap_urls))

    # Get base domain
    if not normalized_urls:
        return []

    parsed_first = urlparse(normalized_urls[0])
    base_domain = parsed_first.netloc

    # STAGE 1: Pre-filter with pattern matching
    # Look for URLs containing key patterns for chronological content
    patterns = [
        "blog",
        "news",
        "changelog",
        "release",
        "updates",
        "versions",
        "whats-new",
        "announcements",
        "archive",
        "category",
        "upgrade",
    ]

    pre_filtered = []
    for url in normalized_urls:
        url_lower = url.lower()
        parsed = urlparse(url)
        path = parsed.path.lower()

        # Check if URL contains any of our patterns
        if any(pattern in url_lower for pattern in patterns):
            # Calculate path depth
            path_segments = [p for p in path.split("/") if p]
            path_depth = len(path_segments)
            last_segment = path_segments[-1] if path_segments else ""

            # EXCLUSIONS: Skip these entirely
            # 1. Author pages
            if "/author/" in path or "/authors/" in path:
                continue

            # 2. Tag pages (too granular, too many)
            if "/tags/" in path or "/tag/" in path or path.endswith("/tags"):
                continue

            # 3. Pagination pages (we auto-follow pagination anyway)
            if re.match(r".*/page/\d+$", path):
                continue

            # 4. Individual blog posts (deep paths under /blog/)
            if "/blog/" in path and path_depth >= 3:
                # Allow special blog subdirectories (indexes)
                special_blog_paths = ["archive", "category", "categories", "page"]
                if not any(special in path for special in special_blog_paths):
                    # This looks like an individual post: /blog/2024/10/my-post
                    continue

            # 5. Very long last segments (likely individual posts)
            if len(last_segment) > 50:
                continue

            # 6. Common individual post patterns in URL
            individual_post_keywords = [
                "announcing-",
                "introducing-",
                "guide-to-",
                "how-to-",
                "what-is-",
                "tutorial-",
                "-guide-to-",
                "-how-to-",
                "understanding-",
            ]
            if any(keyword in last_segment for keyword in individual_post_keywords):
                continue

            # If we made it here, it's a good candidate
            pre_filtered.append(url)

    print(f"Pre-filtered: {len(pre_filtered)} candidates from {len(normalized_urls)} URLs")

    # If pre-filtering produced too few results, widen the net
    if len(pre_filtered) < max_candidates * 2:
        # Add URLs with short paths (likely index pages)
        for url in normalized_urls:
            if url in pre_filtered:
                continue

            parsed = urlparse(url)
            path_segments = [p for p in parsed.path.split("/") if p]
            path_depth = len(path_segments)

            # Short paths are often indexes
            if path_depth <= 2:
                pre_filtered.append(url)

    # Deduplicate and limit
    # Since we're sending paths (not full URLs), we can handle more candidates
    pre_filtered = list(set(pre_filtered))[:500]  # Max 500 paths for LLM analysis

    if not pre_filtered:
        print("No candidates found after pre-filtering")
        return []

    # STAGE 2: LLM semantic analysis on filtered set
    # Configure DSPy
    lm = dspy.LM(llm_model)
    dspy.configure(lm=lm)

    # Prepare filtered URLs for LLM
    urls_text = "\n".join(pre_filtered)

    # Create detailed prompt - emphasize being INCLUSIVE
    prompt = f"""Analyze these pre-filtered URLs from {base_domain} and identify ALL pages that are good candidates for scraping chronological content (blog posts with dates, changelogs, release notes).

These URLs have been pre-filtered to exclude individual posts, tags, author pages, and pagination. Your job is to identify ALL valuable candidates, up to {max_candidates} maximum.

IMPORTANT: Be INCLUSIVE. Return ALL URLs that match these criteria (don't filter aggressively):

PRIORITIZE:
1. Main blog/news indexes (e.g., /blog, /news) - Priority 10
2. Changelog and release notes pages - Priority 10
3. Version/upgrade documentation pages - Priority 9
4. Blog archives and category pages - Priority 8

Return ALL candidates that fit these criteria, up to {max_candidates} maximum. Do not be overly selective.

For each candidate, provide:
- The exact URL (from the list below)
- Type: blog_index, changelog, release_notes, version, archive, or category
- Priority: 1-10 (10 = highest)
- Reasoning: Why this URL is valuable for date extraction

Pre-filtered URLs ({len(pre_filtered)} total):
{urls_text}"""

    # Use LLM to identify candidates
    identifier = ChainOfThought(IdentifyBlogrollCandidatesSignature)

    try:
        result = identifier(urls_sample=prompt, base_domain=base_domain)

        # Convert to list format
        candidates = []
        seen_urls = set()  # Deduplicate
        for candidate in result.candidates.candidates[:max_candidates]:
            normalized = normalize_url(candidate.url)
            if normalized not in seen_urls:
                candidates.append(
                    {
                        "url": normalized,
                        "type": candidate.type,
                        "priority": candidate.priority,
                        "reasoning": candidate.reasoning,
                    }
                )
                seen_urls.add(normalized)

        # Sort by priority (highest first)
        candidates.sort(key=lambda x: -x["priority"])

        return candidates

    except Exception as e:
        print(f"Error using LLM to identify candidates: {e}")
        # Fallback: return empty list
        return []


def extract_chronological_content(
    url: str,
    llm_model: str = "openai/gpt-4o-mini",
    max_posts: int = 100,
    follow_pagination: bool = True,
    max_pages: int = 10,
) -> list[dict]:
    """
    Extract blog posts, release notes, or changelog entries from a page using LLM.

    This function handles both:
    - Blogroll pages (explicit dates on each post)
    - Release notes pages (date headers with links underneath)

    The LLM analyzes the page structure and extracts:
    - Post URLs (converts relative URLs to absolute)
    - Titles
    - Dates (explicit or inferred from headers)
    - Excerpts (if available)
    - Pagination links (to follow multi-page listings)

    Args:
        url: URL of blogroll, release notes, or changelog page
        llm_model: LLM model to use for extraction (default: gpt-4o-mini)
        max_posts: Maximum total posts to extract across all pages (default: 100)
        follow_pagination: If True, follow "next page" links (default: True)
        max_pages: Maximum number of pages to scrape (default: 10)

    Returns:
        List of dicts with keys:
            - url: str (full URL to post)
            - title: str (post title)
            - date: datetime or None (published date if found)
            - excerpt: str or None (post description)

    Example:
        >>> posts = extract_chronological_content(
        ...     "https://www.getdbt.com/blog",
        ...     follow_pagination=True,
        ...     max_pages=5
        ... )
        >>> len(posts)
        87  # Got posts from 5 pages
    """
    # Initialize
    all_posts = []
    seen_urls = set()
    current_url = url
    pages_scraped = 0

    # Configure DSPy with specified model
    lm = dspy.LM(llm_model)
    dspy.configure(lm=lm)

    # Get base URL for resolving relative links
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    # Use LLM to extract structured data
    extractor = ChainOfThought(ExtractChronologicalContentSignature)

    # Loop through pages
    while current_url and pages_scraped < max_pages and len(all_posts) < max_posts:
        # Fetch page content
        try:
            response = httpx.get(current_url, timeout=30.0, follow_redirects=True)
            response.raise_for_status()
            html = response.text
        except Exception as e:
            print(f"Error fetching {current_url}: {e}")
            break

        # Extract markdown using trafilatura (cleaner for LLM)
        markdown = trafilatura.extract(
            html, output_format="markdown", include_links=True, url=current_url
        )

        if not markdown:
            print(f"No content extracted from {current_url}")
            break

        try:
            # Add instruction to the content
            remaining_posts = max_posts - len(all_posts)
            content_with_instructions = f"""Extract all blog posts, release notes, or changelog entries from this page.

IMPORTANT INSTRUCTIONS:
1. For blogroll pages: Extract the URL, title, and date for each post
2. For release notes pages with date headers: Assign the header date to all links under that header
3. Convert all relative URLs to absolute URLs using base_url: {base_url}
4. Parse dates into ISO format (YYYY-MM-DD)
5. Limit to first {remaining_posts} posts
6. If a date is ambiguous or missing, set it to null

CONTENT:
{markdown[:15000]}"""  # Limit content length to avoid token limits

            result = extractor(content=content_with_instructions, base_url=base_url)

            # Parse and validate results
            for post in result.extraction.posts:
                if len(all_posts) >= max_posts:
                    break

                # Parse date if present
                date_obj = None
                if post.date:
                    try:
                        date_obj = datetime.fromisoformat(post.date)
                    except (ValueError, AttributeError):
                        # Try other common formats
                        for fmt in ["%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"]:
                            try:
                                date_obj = datetime.strptime(post.date, fmt)
                                break
                            except ValueError:
                                continue

                # Resolve relative URLs
                post_url = post.url
                if not post_url.startswith(("http://", "https://")):
                    # Resolve relative URL
                    if post_url.startswith("/"):
                        post_url = base_url + post_url
                    else:
                        post_url = base_url + "/" + post_url

                # Normalize URL to avoid duplicates
                post_url = normalize_url(post_url)

                # Skip if already seen
                if post_url in seen_urls:
                    continue

                seen_urls.add(post_url)
                all_posts.append(
                    {
                        "url": post_url,
                        "title": post.title,
                        "date": date_obj,
                        "excerpt": post.excerpt,
                    }
                )

            pages_scraped += 1

            # Find next page link if pagination is enabled
            if follow_pagination and pages_scraped < max_pages and len(all_posts) < max_posts:
                next_url = _find_next_page_link(html, current_url, base_url)
                if next_url and next_url != current_url:
                    current_url = next_url
                    print(f"  Following pagination to page {pages_scraped + 1}...")
                else:
                    break
            else:
                break

        except Exception as e:
            print(f"Error extracting content from {current_url}: {e}")
            break

    return all_posts


def _find_next_page_link(html: str, current_url: str, base_url: str) -> str | None:
    """
    Find the "next page" link in HTML pagination controls using regex.

    Args:
        html: HTML content of current page
        current_url: Current page URL
        base_url: Base URL for resolving relative links

    Returns:
        URL of next page or None if not found
    """
    next_link = None

    # Strategy 1: Look for <a rel="next" href="...">
    match = re.search(
        r'<a[^>]*\srel=["\']next["\'][^>]*\shref=["\']([^"\']+)["\']', html, re.IGNORECASE
    )
    if not match:
        match = re.search(
            r'<a[^>]*\shref=["\']([^"\']+)["\'][^>]*\srel=["\']next["\']', html, re.IGNORECASE
        )

    if match:
        next_link = match.group(1)

    # Strategy 2: Look for links with "Next", "Older", pagination symbols
    if not next_link:
        # Match <a href="..." ...>Next</a> or similar
        pattern = r'<a[^>]*\shref=["\']([^"\']+)["\'][^>]*>(.*?)</a>'
        matches = re.finditer(pattern, html, re.IGNORECASE | re.DOTALL)
        for match in matches:
            link_text = match.group(2)
            if re.search(r"(next|older|→|›|»)", link_text, re.IGNORECASE):
                next_link = match.group(1)
                break

    # Strategy 3: Look for pagination class patterns
    if not next_link:
        match = re.search(
            r'<a[^>]*\sclass=["\'][^"\']*(?:next|pagination-next)[^"\']*["\'][^>]*\shref=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if match:
            next_link = match.group(1)

    # Resolve relative URL
    if next_link:
        # Decode HTML entities
        next_link = next_link.replace("&amp;", "&")

        if not next_link.startswith(("http://", "https://")):
            if next_link.startswith("/"):
                next_link = base_url + next_link
            else:
                # Relative to current URL
                next_link = urljoin(current_url, next_link)

        # Normalize and return
        return normalize_url(next_link)

    return None


def map_blogrolls(
    sitemap_urls: list[str],
    llm_model: str = "openai/gpt-4o-mini",
    max_blogrolls: int = 10,
    max_posts_per_blogroll: int = 100,
) -> list[dict]:
    """
    Discover and map documents from blogroll/changelog pages.

    This is the high-level function that:
    1. Identifies potential blogroll pages from sitemap URLs
    2. Extracts posts from those pages using LLM
    3. Creates document records for discovered posts

    Args:
        sitemap_urls: List of URLs from sitemap (output of map_sitemap)
        llm_model: LLM model to use for extraction
        max_blogrolls: Maximum number of blogroll pages to scrape
        max_posts_per_blogroll: Maximum posts to extract per page

    Returns:
        List of created documents with keys:
            - document_id: UUID
            - url: str
            - title: str
            - published_date: datetime or None
            - status: str ('NOT_FETCHED')
            - is_chronological: bool (True)
            - discovery_method: str ('blogroll')
            - discovery_url: str (the blogroll page URL)
            - created: bool (whether document was newly created)

    Example:
        >>> # First map sitemap
        >>> sitemap_docs = map_sitemap("https://www.getdbt.com/sitemap.xml")
        >>> sitemap_urls = [doc["url"] for doc in sitemap_docs]
        >>>
        >>> # Then discover additional posts from blogrolls
        >>> blogroll_docs = map_blogrolls(sitemap_urls, max_blogrolls=5)
        >>> len(blogroll_docs)
        42  # Found 42 additional blog posts not in sitemap
    """
    from sqlmodel import select

    # Identify candidate blogroll pages
    candidates = identify_blogroll_candidates(sitemap_urls)
    print(f"Found {len(candidates)} potential blogroll/changelog pages")

    # Limit to top candidates
    candidates = candidates[:max_blogrolls]

    session = get_session()
    all_documents = []

    for candidate in candidates:
        blogroll_url = candidate["url"]
        print(f"\nScraping {blogroll_url}...")

        # Extract posts from this page
        posts = extract_chronological_content(
            blogroll_url, llm_model=llm_model, max_posts=max_posts_per_blogroll
        )

        print(f"  Found {len(posts)} posts")

        # Create document records for each post
        for post in posts:
            # Check if document already exists
            stmt = select(Document).where(Document.source_url == post["url"])
            existing_doc = session.exec(stmt).first()

            if existing_doc:
                # Update discovery metadata if not set
                updated = False
                if not existing_doc.is_chronological:
                    existing_doc.is_chronological = True
                    updated = True
                if not existing_doc.discovery_method:
                    existing_doc.discovery_method = "blogroll"
                    existing_doc.discovery_url = blogroll_url
                    updated = True
                if post["date"] and not existing_doc.published_date:
                    existing_doc.published_date = post["date"]
                    updated = True

                if updated:
                    session.commit()
                    session.refresh(existing_doc)

                all_documents.append(
                    {
                        "document_id": existing_doc.id,
                        "url": existing_doc.source_url,
                        "title": existing_doc.title,
                        "published_date": existing_doc.published_date,
                        "status": existing_doc.ingestion_status.value,
                        "is_chronological": existing_doc.is_chronological,
                        "discovery_method": existing_doc.discovery_method,
                        "discovery_url": existing_doc.discovery_url,
                        "created": False,
                    }
                )
                continue

            # Create new document
            doc = Document(
                title=post["title"],
                source_type=SourceType.URL,
                source_url=post["url"],
                ingestion_status=IngestionStatus.NOT_FETCHED,
                published_date=post["date"],
                description=post["excerpt"],
                is_chronological=True,
                discovery_method="blogroll",
                discovery_url=blogroll_url,
            )

            session.add(doc)
            session.commit()
            session.refresh(doc)

            all_documents.append(
                {
                    "document_id": doc.id,
                    "url": doc.source_url,
                    "title": doc.title,
                    "published_date": doc.published_date,
                    "status": doc.ingestion_status.value,
                    "is_chronological": doc.is_chronological,
                    "discovery_method": doc.discovery_method,
                    "discovery_url": doc.discovery_url,
                    "created": True,
                }
            )

    print(f"\n✓ Total documents discovered from blogrolls: {len(all_documents)}")
    print(f"  New: {sum(1 for d in all_documents if d['created'])}")
    print(f"  Existing: {sum(1 for d in all_documents if not d['created'])}")

    return all_documents


def map_url_content(
    url: str,
    sitemap_path: str = None,
    include_blogrolls: bool = False,
    max_depth: int = None,
    max_pages: int = 1000,
    include_patterns: tuple = (),
    exclude_patterns: tuple = (),
    allow_external: bool = False,
    dry_run: bool = False,
    cluster_urls: bool = False,
) -> dict:
    """
    High-level URL mapping function - discover content from web sources.

    Handles:
    - Sitemap detection and parsing
    - Blogroll date extraction (optional)
    - Crawling fallback if no sitemap
    - Pattern filtering
    - Document creation (NOT_FETCHED status)
    - Optional clustering (if cluster_urls=True)

    Args:
        url: Base URL to map
        sitemap_path: Override sitemap location
        include_blogrolls: Enable LLM blogroll date extraction
        max_depth: Crawl depth if no sitemap found
        max_pages: Max pages to discover (default: 1000)
        include_patterns: Include URL patterns (glob)
        exclude_patterns: Exclude URL patterns (glob)
        allow_external: Follow external links
        dry_run: If True, discover URLs but don't save to database
        cluster_urls: If True, automatically cluster documents after mapping

    Returns:
        dict with:
            - discovered: List of discovered document dicts or URLs (if dry_run)
            - total: Total count
            - new: Count of new documents created (0 if dry_run)
            - existing: Count of existing documents (0 if dry_run)
            - method: Discovery method used (sitemap|blogrolls|crawl)
            - dry_run: Boolean indicating if this was a dry run
    """
    from kurt.utils.url_utils import is_single_page_url

    # DRY RUN MODE: Discover URLs without saving to database
    if dry_run:
        from kurt.ingestion.map import _discover_sitemap_urls

        discovery_method = "sitemap"

        # Discover URLs from sitemap or crawling
        try:
            # Note: sitemap_path parameter is not used by _discover_sitemap_urls yet
            discovered_urls = _discover_sitemap_urls(url)
        except Exception as e:
            # Sitemap failed - try crawling if max_depth is specified
            if max_depth is not None:
                logger.info(
                    f"Sitemap discovery failed in dry-run: {e}. Trying crawl with max_depth={max_depth}"
                )
                discovered_urls = crawl_website(
                    homepage=url,
                    max_depth=max_depth,
                    max_pages=max_pages,
                    allow_external=allow_external,
                    include_patterns=include_patterns,
                    exclude_patterns=exclude_patterns,
                )
                discovery_method = "crawl"
            else:
                # Fallback to single URL if discovery fails and no max_depth
                discovered_urls = [url]

        # Apply filters (if not already applied by crawl_website)
        if discovery_method == "sitemap":
            filtered_urls = []
            for discovered_url in discovered_urls:
                # Apply include patterns
                if include_patterns:
                    if not any(fnmatch(discovered_url, pattern) for pattern in include_patterns):
                        continue

                # Apply exclude patterns
                if exclude_patterns:
                    if any(fnmatch(discovered_url, pattern) for pattern in exclude_patterns):
                        continue

                filtered_urls.append(discovered_url)

            # Apply limit
            if max_pages:
                filtered_urls = filtered_urls[:max_pages]
        else:
            # Crawling already applied filters
            filtered_urls = discovered_urls

        return {
            "discovered": filtered_urls,  # Just URLs, not document objects
            "total": len(filtered_urls),
            "new": 0,  # Not saved
            "existing": 0,  # Not checked
            "method": discovery_method,
            "dry_run": True,
        }

    # NORMAL MODE: Single page detection
    if is_single_page_url(url):
        # Single page - just create document
        from kurt.ingestion.fetch import add_document

        doc_id = add_document(url)
        result = {
            "discovered": [{"url": url, "doc_id": str(doc_id), "created": True}],
            "total": 1,
            "new": 1,
            "existing": 0,
            "method": "single_page",
            "dry_run": False,
        }

        # Auto-cluster if requested (though clustering 1 page doesn't make sense)
        if cluster_urls:
            from kurt.ingestion.cluster import compute_topic_clusters

            cluster_result = compute_topic_clusters()
            result["clusters"] = cluster_result["clusters"]
            result["cluster_count"] = len(cluster_result["clusters"])

        return result

    # NORMAL MODE: Multi-page discovery with filters
    # Try sitemap first, fall back to crawling if requested and sitemap fails
    docs = []
    discovery_method = "sitemap"

    try:
        docs = map_sitemap(
            url,
            fetch_all=False,
            discover_blogrolls=include_blogrolls,
            max_blogrolls=50 if include_blogrolls else 10,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            limit=max_pages,
        )
    except (ValueError, Exception) as e:
        # Sitemap failed - fall back to crawling if max_depth is specified
        if max_depth is not None:
            logger.info(
                f"Sitemap discovery failed: {e}. Falling back to crawling with max_depth={max_depth}"
            )

            # Use crawler to discover URLs
            crawled_urls = crawl_website(
                homepage=url,
                max_depth=max_depth,
                max_pages=max_pages,
                allow_external=allow_external,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
            )

            # Create documents for crawled URLs
            from kurt.ingestion.fetch import add_document

            for crawled_url in crawled_urls:
                try:
                    doc_id = add_document(crawled_url)
                    docs.append(
                        {
                            "url": crawled_url,
                            "doc_id": str(doc_id),
                            "created": True,
                        }
                    )
                except Exception as doc_err:
                    logger.warning(f"Failed to create document for {crawled_url}: {doc_err}")

            discovery_method = "crawl"
        else:
            # No max_depth specified and sitemap failed - re-raise the error
            raise

    new_count = sum(1 for d in docs if d.get("created", False))
    existing_count = len(docs) - new_count

    result = {
        "discovered": docs,
        "total": len(docs),
        "new": new_count,
        "existing": existing_count,
        "method": discovery_method,
        "dry_run": False,
    }

    # Auto-cluster if requested
    if cluster_urls and len(docs) > 0:
        from kurt.ingestion.cluster import compute_topic_clusters

        cluster_result = compute_topic_clusters()
        result["clusters"] = cluster_result["clusters"]
        result["cluster_count"] = len(cluster_result["clusters"])

    return result


def _add_single_file_to_db(file_path: Path) -> dict:
    """
    Internal function: Add a single markdown file to the database.

    Args:
        file_path: Path to .md file

    Returns:
        Dict with keys: doc_id, created, skipped, reason (if skipped)
    """
    import shutil
    from uuid import uuid4

    from sqlmodel import select

    from kurt.config import load_config
    from kurt.utils.file_utils import compute_file_hash
    from kurt.utils.source_detection import validate_file_extension

    # Validate file
    is_valid, error_msg = validate_file_extension(file_path)
    if not is_valid:
        raise ValueError(error_msg)

    # Compute content hash
    content_hash = compute_file_hash(file_path)

    # Check if document already exists (by content hash)
    session = get_session()
    stmt = select(Document).where(Document.content_hash == content_hash)
    existing_doc = session.exec(stmt).first()

    if existing_doc:
        return {
            "doc_id": str(existing_doc.id),
            "created": False,
            "skipped": True,
            "reason": "Content already exists",
        }

    # Copy file to sources directory
    config = load_config()
    sources_dir = config.get_absolute_sources_path()
    target_path = sources_dir / file_path.name
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file_path, target_path)
    relative_content_path = str(target_path.relative_to(sources_dir))

    # Read file content for title extraction
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract title from first heading or filename
    title = None
    for line in content.split("\n"):
        if line.startswith("# "):
            title = line[2:].strip()
            break
    if not title:
        title = file_path.stem.replace("-", " ").replace("_", " ").title()

    # Create document record
    doc = Document(
        id=uuid4(),
        title=title,
        source_type=SourceType.FILE_UPLOAD,
        source_url=f"file://{file_path.absolute()}",
        content_path=relative_content_path,
        ingestion_status=IngestionStatus.FETCHED,
        content_hash=content_hash,
    )

    session.add(doc)
    session.commit()
    session.refresh(doc)

    return {
        "doc_id": str(doc.id),
        "created": True,
        "skipped": False,
    }


def map_folder_content(
    folder_path: str,
    include_patterns: tuple = (),
    exclude_patterns: tuple = (),
    dry_run: bool = False,
    cluster_urls: bool = False,
) -> dict:
    """
    High-level folder mapping function - discover content from local files.

    Args:
        folder_path: Path to folder to scan
        include_patterns: Include file patterns (glob)
        exclude_patterns: Exclude file patterns (glob)
        dry_run: If True, discover files but don't save to database
        cluster_urls: If True, automatically cluster documents after mapping

    Returns:
        dict with:
            - discovered: List of file paths (strings if dry_run, dicts otherwise)
            - total: Total count
            - new: Count of new files (0 if dry_run)
            - existing: Count of existing files (0 if dry_run)
            - dry_run: Boolean indicating if this was a dry run
            - clusters: List of clusters (if cluster_urls=True)
            - cluster_count: Number of clusters (if cluster_urls=True)
    """
    from fnmatch import fnmatch

    from kurt.utils.source_detection import discover_markdown_files

    folder = Path(folder_path)
    md_files = discover_markdown_files(folder, recursive=True)

    # Apply filters
    if include_patterns:
        filtered = []
        for file_path in md_files:
            rel_path = str(file_path.relative_to(folder))
            if any(fnmatch(rel_path, pattern) for pattern in include_patterns):
                filtered.append(file_path)
        md_files = filtered

    if exclude_patterns:
        filtered = []
        for file_path in md_files:
            rel_path = str(file_path.relative_to(folder))
            if not any(fnmatch(rel_path, pattern) for pattern in exclude_patterns):
                filtered.append(file_path)
        md_files = filtered

    # Handle dry-run mode
    if dry_run:
        # Return file paths as strings without saving to database
        return {
            "discovered": [str(file_path) for file_path in md_files],
            "total": len(md_files),
            "new": 0,
            "existing": 0,
            "dry_run": True,
        }

    # Add files to database (normal mode)
    results = []
    for file_path in md_files:
        try:
            result = _add_single_file_to_db(file_path)
            results.append(
                {
                    "path": str(file_path),
                    "doc_id": result["doc_id"],
                    "created": result["created"],
                }
            )
        except Exception as e:
            results.append(
                {
                    "path": str(file_path),
                    "error": str(e),
                    "created": False,
                }
            )

    new_count = sum(1 for r in results if r.get("created", False))
    existing_count = len(results) - new_count

    result_dict = {
        "discovered": results,
        "total": len(results),
        "new": new_count,
        "existing": existing_count,
        "dry_run": False,
    }

    # Auto-cluster if requested
    if cluster_urls and len(results) > 0:
        from kurt.ingestion.cluster import compute_topic_clusters

        cluster_result = compute_topic_clusters()
        result_dict["clusters"] = cluster_result["clusters"]
        result_dict["cluster_count"] = len(cluster_result["clusters"])

    return result_dict
