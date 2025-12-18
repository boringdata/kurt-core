"""
Sitemap discovery functionality.

Discovers URLs from sitemap.xml files.
"""

import logging
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


def discover_sitemap_urls(base_url: str) -> list[str]:
    """
    Discover URLs from sitemap.xml.

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
