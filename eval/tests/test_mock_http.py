#!/usr/bin/env python3
"""Test that HTTP mocking works correctly.

This script tests:
1. Mock client loads URLs correctly
2. requests library is patched
3. httpx library is patched
4. URL mappings work
"""

import sys
from pathlib import Path

# Add eval to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from framework.mock_http import create_mock_client


def test_mock_loading():
    """Test that mock files are loaded correctly."""
    print("🧪 Test 1: Loading mock files")

    mock_client = create_mock_client()
    mock_client.load_mocks()

    # Check that URLs were loaded
    assert len(mock_client.url_to_file) > 0, "No URLs loaded!"
    print(f"   ✅ Loaded {len(mock_client.url_to_file)} URL mappings")

    # Check specific URLs
    expected_urls = [
        "https://acme-corp.com/home",
        "https://acme-corp.com/about",
        "https://docs.acme-corp.com/getting-started",
    ]

    for url in expected_urls:
        if url in mock_client.url_to_file:
            print(f"   ✅ Found: {url}")
        else:
            print(f"   ❌ Missing: {url}")

    return mock_client


def test_requests_library():
    """Test that requests library is properly mocked."""
    print("\n🧪 Test 2: requests library patching")

    import requests

    mock_client = create_mock_client()
    mock_client.load_mocks()
    mock_client.start()

    try:
        # Test fetching ACME homepage
        response = requests.get("https://acme-corp.com/home")

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"   ✅ Status code: {response.status_code}")

        content = response.text
        assert "ACME" in content, "Expected 'ACME' in content"
        assert len(content) > 100, f"Content too short: {len(content)} chars"
        print(f"   ✅ Content length: {len(content)} chars")

        # Check headers
        assert "X-Mock-Source" in response.headers, "Missing mock source header"
        print(f"   ✅ Mock source: {response.headers['X-Mock-Source']}")

    finally:
        mock_client.stop()


def test_httpx_library():
    """Test that httpx library is properly mocked."""
    print("\n🧪 Test 3: httpx library patching")

    import httpx

    mock_client = create_mock_client()
    mock_client.load_mocks()
    mock_client.start()

    try:
        # Test fetching ACME docs
        response = httpx.get("https://docs.acme-corp.com/getting-started")

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"   ✅ Status code: {response.status_code}")

        content = response.text
        assert "Getting Started" in content, "Expected 'Getting Started' in content"
        print(f"   ✅ Content length: {len(content)} chars")

    finally:
        mock_client.stop()


def test_context_manager():
    """Test using mock client as context manager."""
    print("\n🧪 Test 4: Context manager")

    import requests

    with create_mock_client():
        response = requests.get("https://acme-corp.com/about")
        assert response.status_code == 200
        print(f"   ✅ Inside context: status {response.status_code}")

    # Should be restored now
    print("   ✅ Context manager cleanup completed")


def test_sitemap_xml():
    """Test that XML files work correctly."""
    print("\n🧪 Test 5: XML/Sitemap files")

    import requests

    with create_mock_client():
        response = requests.get("https://acme-corp.com/sitemap.xml")

        assert response.status_code == 200
        print(f"   ✅ Status code: {response.status_code}")

        content = response.text
        assert '<?xml version="1.0"' in content, "Not valid XML"
        assert "<urlset" in content, "Not a sitemap"
        assert "https://acme-corp.com" in content, "Missing URLs"
        print("   ✅ Valid sitemap XML")


def test_missing_url():
    """Test behavior with non-mocked URL."""
    print("\n🧪 Test 6: Non-mocked URL handling")

    import requests

    with create_mock_client():
        try:
            # This URL doesn't have a mock
            response = requests.get("https://example.com/not-mocked")
            print(f"   ⚠️  Got response: {response.status_code} (should fall through)")
        except requests.exceptions.ConnectionError:
            print("   ✅ ConnectionError raised (expected for non-mocked URL)")


def main():
    """Run all tests."""
    print("=" * 70)
    print("Testing HTTP Mocking Infrastructure")
    print("=" * 70)

    try:
        # Test 1: Loading
        test_mock_loading()

        # Test 2: requests library
        test_requests_library()

        # Test 3: httpx library
        test_httpx_library()

        # Test 4: Context manager
        test_context_manager()

        # Test 5: XML/Sitemap
        test_sitemap_xml()

        # Test 6: Missing URLs
        test_missing_url()

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        print(f"\nMock files location: {Path(__file__).parent / 'mock'}")
        print("HTTP mocking is working correctly!")

        return 0

    except AssertionError as e:
        print("\n" + "=" * 70)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 70)
        return 1
    except Exception as e:
        print("\n" + "=" * 70)
        print(f"❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
