from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import httpx
from trafilatura.spider import focused_crawler

from .utils import filter_items

logger = logging.getLogger(__name__)


def discover_from_url(
    url: str,
    *,
    max_depth: int | None = None,
    max_pages: int = 1000,
    allow_external: bool = False,
    include_patterns: tuple[str, ...] = (),
    exclude_patterns: tuple[str, ...] = (),
) -> dict:
    """
    Discover URLs from web source (sitemap or crawl).
    """
    discovered_urls: list[str] = []
    discovery_method = "sitemap"

    try:
        discovered_urls = discover_sitemap_urls(url)
        logger.info("Sitemap discovered %s URLs", len(discovered_urls))
    except Exception as exc:
        if max_depth is not None:
            logger.info("Sitemap failed: %s. Falling back to crawl.", exc)
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
            logger.info("Sitemap failed: %s. Using single URL.", exc)
            discovered_urls = [url]
            discovery_method = "single_page"

    discovered_urls = filter_items(
        discovered_urls,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        max_items=max_pages,
    )

    return {
        "discovered": [{"url": u} for u in discovered_urls],
        "method": discovery_method,
        "total": len(discovered_urls),
    }


def discover_sitemap_urls(base_url: str) -> list[str]:
    """
    Discover URLs from sitemap.xml.
    """
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    sitemap_urls: list[str] = []

    try:
        response = httpx.get(f"{base}/robots.txt", timeout=10.0, follow_redirects=True)
        if response.status_code == 200:
            for line in response.text.split("\n"):
                if line.lower().startswith("sitemap:"):
                    sitemap_url = line.split(":", 1)[1].strip()
                    sitemap_urls.append(sitemap_url)
    except Exception:
        pass

    common_paths = ["/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml"]
    for path in common_paths:
        url = f"{base}{path}"
        if url not in sitemap_urls:
            sitemap_urls.append(url)

    all_urls: list[str] = []

    for sitemap_url in sitemap_urls:
        try:
            response = httpx.get(sitemap_url, timeout=30.0, follow_redirects=True)
            if response.status_code != 200:
                continue

            root = ET.fromstring(response.content)

            sitemaps = root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap")
            if sitemaps:
                for sitemap in sitemaps:
                    loc = sitemap.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
                    if loc is None or not loc.text:
                        continue
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
                urls = root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}url")
                for url_elem in urls:
                    loc_elem = url_elem.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
                    if loc_elem is not None and loc_elem.text:
                        all_urls.append(loc_elem.text.strip())

            if all_urls:
                return all_urls
        except Exception:
            continue

    if not all_urls:
        raise ValueError(f"No sitemap found for {base_url}")

    return all_urls


def crawl_website(
    homepage: str,
    *,
    max_depth: int = 2,
    max_pages: int = 100,
    allow_external: bool = False,
    include_patterns: tuple[str, ...] = (),
    exclude_patterns: tuple[str, ...] = (),
) -> list[str]:
    """
    Crawl a website using trafilatura's focused_crawler.
    """
    depth_to_urls = {1: 10, 2: 50, 3: 100}
    max_seen_urls = depth_to_urls.get(max_depth, max_depth * 50) if max_depth else 100
    max_seen_urls = min(max_seen_urls, max_pages)

    to_visit, known_links = focused_crawler(
        homepage=homepage,
        max_seen_urls=max_seen_urls,
        max_known_urls=max_pages,
    )
    _ = to_visit

    all_urls = list(known_links)

    if not allow_external:
        homepage_domain = urlparse(homepage).netloc
        all_urls = [url for url in all_urls if urlparse(url).netloc == homepage_domain]

    all_urls = filter_items(
        all_urls,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        max_items=max_pages,
    )

    return all_urls
