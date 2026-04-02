"""Golden test data - expected output snapshots for e2e validation.

These fixtures contain expected data structures and content patterns
for validating e2e test outputs against known-good baselines.

Usage:
    from kurt.tools.e2e.fixtures.golden_data import GOLDEN_SITEMAP_RESULT
    assert actual.count >= GOLDEN_SITEMAP_RESULT["min_urls"]
"""


# =============================================================================
# Map Engine Golden Data
# =============================================================================

GOLDEN_SITEMAP_RESULT = {
    "source": "https://docs.python.org/3/",
    "engine": "sitemap",
    "min_urls": 3,
    "max_urls": 1000,
    "expected_url_patterns": [
        r"https://docs\.python\.org/3",
    ],
    "metadata_keys": ["engine", "source", "doc_type"],
}

GOLDEN_RSS_RESULT = {
    "source": "https://feeds.bbci.co.uk/news/rss.xml",
    "engine": "rss",
    "min_urls": 5,
    "max_urls": 100,
    "expected_url_patterns": [
        r"https://www\.bbc\.(com|co\.uk)",
    ],
    "metadata_keys": ["engine", "source", "doc_type"],
}

GOLDEN_CRAWL_RESULT = {
    "source": "https://example.com",
    "engine": "crawl",
    "min_urls": 1,
    "max_urls": 50,
    "expected_url_patterns": [
        r"https://example\.com",
    ],
    "metadata_keys": ["engine", "source", "doc_type", "max_depth"],
}

# =============================================================================
# Fetch Engine Golden Data
# =============================================================================

GOLDEN_TRAFILATURA_RESULT = {
    "url": "https://example.com",
    "engine": "trafilatura",
    "expected_success": True,
    "min_content_length": 50,
    "expected_content_patterns": [
        r"[Ee]xample",
        r"[Dd]omain",
    ],
    "metadata_keys": ["engine"],
}

GOLDEN_HTTPX_RESULT = {
    "url": "https://example.com",
    "engine": "httpx",
    "expected_success": True,
    "min_content_length": 50,
    "metadata_keys": ["engine"],
}

GOLDEN_TAVILY_RESULT = {
    "url": "https://www.python.org/about/",
    "engine": "tavily",
    "expected_success": True,
    "min_content_length": 500,
    "expected_content_patterns": [
        r"[Pp]ython",
    ],
    "metadata_keys": ["engine", "source_url"],
}

# =============================================================================
# Pipeline Golden Data
# =============================================================================

GOLDEN_SITEMAP_FETCH_PIPELINE = {
    "map_source": "https://docs.python.org/3/",
    "map_engine": "sitemap",
    "fetch_engine": "trafilatura",
    "min_discovered_urls": 3,
    "min_successful_fetches": 1,
    "expected_content_patterns": [
        r"[Pp]ython",
    ],
}

GOLDEN_RSS_FETCH_PIPELINE = {
    "map_source": "https://feeds.bbci.co.uk/news/rss.xml",
    "map_engine": "rss",
    "fetch_engine": "trafilatura",
    "min_discovered_urls": 5,
    "min_successful_fetches": 1,
}

GOLDEN_CRAWL_FETCH_PIPELINE = {
    "map_source": "https://docs.python.org/3/library/json.html",
    "map_engine": "crawl",
    "fetch_engine": "trafilatura",
    "min_discovered_urls": 1,
    "min_successful_fetches": 1,
    "expected_content_patterns": [
        r"[Jj]son|JSON",
    ],
}

# =============================================================================
# Sample Content Snapshots
# =============================================================================

GOLDEN_EXAMPLE_COM_CONTENT = {
    "url": "https://example.com",
    "expected_title_pattern": r"[Ee]xample [Dd]omain",
    "expected_content_snippets": [
        "Example Domain",
        # Note: Content varies based on extraction method
    ],
    "min_word_count": 5,
    "max_word_count": 500,
}

GOLDEN_PYTHON_DOCS_JSON = {
    "url": "https://docs.python.org/3/library/json.html",
    "expected_title_pattern": r"json.*JSON",
    "expected_content_snippets": [
        "json",
        "encoder",
        "decoder",
        "dumps",
        "loads",
    ],
    "min_word_count": 500,
}

GOLDEN_PYTHON_ORG_ABOUT = {
    "url": "https://www.python.org/about/",
    "expected_title_pattern": r"[Aa]bout [Pp]ython",
    "expected_content_snippets": [
        "Python",
        "programming",
        "language",
    ],
    "min_word_count": 200,
}

# =============================================================================
# Error Case Golden Data
# =============================================================================

GOLDEN_404_RESPONSE = {
    "url": "https://httpbin.org/status/404",
    "expected_success": False,
    "expected_error_patterns": [
        r"404|not found|error",
    ],
}

GOLDEN_INVALID_URL = {
    "url": "https://this-domain-does-not-exist-12345.com",
    "expected_success": False,
    "expected_error_patterns": [
        r"error|failed|connect|resolve",
    ],
}

GOLDEN_NO_SITEMAP = {
    "url": "https://httpbin.org",
    "expected_urls": 0,
    "expected_error_patterns": [
        r"[Nn]o sitemap|not found",
    ],
}

# =============================================================================
# Validation Helpers
# =============================================================================

def validate_map_result(result, golden):
    """Validate a MapperResult against golden data.

    Args:
        result: MapperResult to validate
        golden: Golden data dict

    Returns:
        tuple: (is_valid, errors list)
    """
    import re
    errors = []

    # Check URL count
    if result.count < golden.get("min_urls", 0):
        errors.append(f"Too few URLs: {result.count} < {golden['min_urls']}")

    if result.count > golden.get("max_urls", float("inf")):
        errors.append(f"Too many URLs: {result.count} > {golden['max_urls']}")

    # Check URL patterns
    for pattern in golden.get("expected_url_patterns", []):
        regex = re.compile(pattern)
        matching = [u for u in result.urls if regex.search(u)]
        if not matching:
            errors.append(f"No URLs match pattern: {pattern}")

    # Check metadata keys
    for key in golden.get("metadata_keys", []):
        if key not in result.metadata:
            errors.append(f"Missing metadata key: {key}")

    # Check engine
    if golden.get("engine") and result.metadata.get("engine") != golden["engine"]:
        errors.append(f"Engine mismatch: {result.metadata.get('engine')} != {golden['engine']}")

    return len(errors) == 0, errors


def validate_fetch_result(result, golden):
    """Validate a FetchResult against golden data.

    Args:
        result: FetchResult to validate
        golden: Golden data dict

    Returns:
        tuple: (is_valid, errors list)
    """
    import re
    errors = []

    # Check success
    if golden.get("expected_success") is not None:
        if result.success != golden["expected_success"]:
            errors.append(f"Success mismatch: {result.success} != {golden['expected_success']}")

    # Check content length
    if result.success and golden.get("min_content_length"):
        if len(result.content) < golden["min_content_length"]:
            errors.append(f"Content too short: {len(result.content)} < {golden['min_content_length']}")

    # Check content patterns
    if result.success:
        for pattern in golden.get("expected_content_patterns", []):
            regex = re.compile(pattern, re.IGNORECASE)
            if not regex.search(result.content):
                errors.append(f"Content missing pattern: {pattern}")

    # Check metadata keys
    for key in golden.get("metadata_keys", []):
        if key not in result.metadata:
            errors.append(f"Missing metadata key: {key}")

    # Check engine
    if golden.get("engine") and result.metadata.get("engine") != golden["engine"]:
        errors.append(f"Engine mismatch: {result.metadata.get('engine')} != {golden['engine']}")

    return len(errors) == 0, errors


def validate_content_snapshot(content, golden):
    """Validate content against a snapshot.

    Args:
        content: Content string to validate
        golden: Golden data dict with expected snippets

    Returns:
        tuple: (is_valid, errors list)
    """
    import re
    errors = []

    # Check word count
    word_count = len(content.split())
    if golden.get("min_word_count") and word_count < golden["min_word_count"]:
        errors.append(f"Word count too low: {word_count} < {golden['min_word_count']}")

    if golden.get("max_word_count") and word_count > golden["max_word_count"]:
        errors.append(f"Word count too high: {word_count} > {golden['max_word_count']}")

    # Check title pattern
    if golden.get("expected_title_pattern"):
        regex = re.compile(golden["expected_title_pattern"], re.IGNORECASE)
        if not regex.search(content):
            errors.append(f"Title pattern not found: {golden['expected_title_pattern']}")

    # Check content snippets
    for snippet in golden.get("expected_content_snippets", []):
        if snippet.lower() not in content.lower():
            errors.append(f"Missing snippet: {snippet}")

    return len(errors) == 0, errors
