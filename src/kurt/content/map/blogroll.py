"""
Blogroll and chronological content discovery for Kurt.

This module handles discovering blog posts, release notes, and changelog entries
from blogroll/archive pages using LLM-powered extraction.
"""

import logging
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

import dspy
import httpx
import trafilatura
from dspy import ChainOfThought, Signature
from pydantic import BaseModel, Field
from sqlmodel import select

from kurt.config import KurtConfig
from kurt.db.database import get_session
from kurt.db.models import Document, IngestionStatus, SourceType
from kurt.utils.url_utils import normalize_url_for_deduplication as normalize_url

logger = logging.getLogger(__name__)

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


# ============================================================================
# Pydantic Models for LLM Extraction
# ============================================================================


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


# ============================================================================
# Blogroll Candidate Identification
# ============================================================================


def identify_blogroll_candidates(
    sitemap_urls: list[str],
    llm_model: str = KurtConfig.DEFAULT_INDEXING_LLM_MODEL,
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


# ============================================================================
# Chronological Content Extraction
# ============================================================================


def extract_chronological_content(
    url: str,
    llm_model: str = KurtConfig.DEFAULT_INDEXING_LLM_MODEL,
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


# ============================================================================
# High-level Blogroll Mapping
# ============================================================================


def map_blogrolls(
    sitemap_urls: list[str],
    llm_model: str = KurtConfig.DEFAULT_INDEXING_LLM_MODEL,
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
