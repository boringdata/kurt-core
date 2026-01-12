"""Tavily extract fetch provider."""

from __future__ import annotations

import os
from typing import Any

import httpx

from .models import BatchFetchResult


def _extract_tavily_metadata(result_item: dict[str, Any], response_data: dict) -> dict:
    """Extract and normalize metadata from Tavily extract response."""
    metadata = {}

    if "url" in result_item:
        metadata["source_url"] = result_item["url"]

    if "favicon" in result_item and result_item["favicon"]:
        metadata["favicon"] = result_item["favicon"]

    if "images" in result_item and result_item["images"]:
        metadata["images"] = result_item["images"]

    # Add response-level metadata
    if "response_time" in response_data:
        metadata["response_time"] = response_data["response_time"]
    if "request_id" in response_data:
        metadata["request_id"] = response_data["request_id"]

    return metadata


def fetch_with_tavily(urls: str | list[str]) -> BatchFetchResult:
    """
    Fetch content using Tavily Extract API.

    Supports both single URL and batch operations (up to 20 URLs).

    Args:
        urls: Single URL string or list of URLs (max 20)

    Returns:
        Dict mapping URL -> (content_markdown, metadata_dict) or Exception

    Raises:
        ValueError: If TAVILY_API_KEY not set or batch exceeds 20 URLs
    """
    # Normalize input
    if isinstance(urls, str):
        url_list = [urls]
    else:
        url_list = urls

    if not url_list:
        return {}

    if len(url_list) > 20:
        raise ValueError("[Tavily] Maximum 20 URLs per request")

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("[Tavily] TAVILY_API_KEY not set in environment")

    # Tavily extract API endpoint
    api_url = "https://api.tavily.com/extract"

    payload = {
        "urls": url_list if len(url_list) > 1 else url_list[0],
        "format": "markdown",
        "extract_depth": "advanced",
        "include_images": False,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Adjust timeout based on batch size
    timeout = 60.0 + (len(url_list) - 1) * 5.0  # 60s base + 5s per additional URL

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        if status_code == 401:
            raise ValueError("[Tavily] Invalid API key") from e
        elif status_code == 403:
            raise ValueError("[Tavily] URL not supported") from e
        elif status_code == 429:
            raise ValueError("[Tavily] Rate limit exceeded") from e
        elif status_code in (432, 433):
            raise ValueError("[Tavily] Credit or plan limit exceeded") from e
        else:
            raise ValueError(f"[Tavily] API error ({status_code}): {e}") from e
    except httpx.RequestError as e:
        raise ValueError(f"[Tavily] Request error: {type(e).__name__}: {str(e)}") from e
    except Exception as e:
        raise ValueError(f"[Tavily] Unexpected error: {type(e).__name__}: {str(e)}") from e

    # Process results
    results: BatchFetchResult = {}

    # Process successful results
    for result in data.get("results", []):
        result_url = result.get("url", "")
        content = result.get("raw_content", "")

        if not result_url:
            continue

        if not content or not content.strip():
            results[result_url] = ValueError(f"[Tavily] Empty content from: {result_url}")
            continue

        metadata = _extract_tavily_metadata(result, data)
        results[result_url] = (content, metadata)

    # Process failed results
    for failed in data.get("failed_results", []):
        if isinstance(failed, dict):
            failed_url = failed.get("url", "")
            error_msg = failed.get("error", "Unknown error")
            if failed_url:
                results[failed_url] = ValueError(f"[Tavily] {failed_url}: {error_msg}")
        elif isinstance(failed, str):
            results[failed] = ValueError(f"[Tavily] Failed: {failed}")

    # Mark any requested URLs not in results as failed
    for url in url_list:
        if url not in results:
            results[url] = ValueError(f"[Tavily] No result for: {url}")

    return results
