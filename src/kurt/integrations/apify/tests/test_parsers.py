"""Tests for the Apify parsers module."""

from datetime import datetime

import pytest

from kurt.integrations.apify.parsers import (
    FieldMapping,
    ParsedItem,
    extract_author,
    extract_field,
    extract_title,
    get_nested,
    parse_date,
    parse_item,
    parse_items,
)


class TestGetNested:
    """Test get_nested function."""

    def test_simple_field(self):
        """Test getting a simple field."""
        item = {"name": "test", "value": 42}
        assert get_nested(item, "name") == "test"
        assert get_nested(item, "value") == 42

    def test_nested_field(self):
        """Test getting a nested field with dot notation."""
        item = {"author": {"name": "John", "id": 123}}
        assert get_nested(item, "author.name") == "John"
        assert get_nested(item, "author.id") == 123

    def test_deeply_nested_field(self):
        """Test getting a deeply nested field."""
        item = {"user": {"profile": {"name": "Alice"}}}
        assert get_nested(item, "user.profile.name") == "Alice"

    def test_missing_field(self):
        """Test getting a missing field returns None."""
        item = {"name": "test"}
        assert get_nested(item, "missing") is None

    def test_missing_nested_field(self):
        """Test getting a missing nested field returns None."""
        item = {"author": {"name": "John"}}
        assert get_nested(item, "author.missing") is None
        assert get_nested(item, "missing.field") is None


class TestExtractField:
    """Test extract_field function."""

    def test_string_field_spec(self):
        """Test extraction with string field spec."""
        item = {"text": "Hello world"}
        assert extract_field(item, "text") == "Hello world"

    def test_list_field_spec_first_match(self):
        """Test extraction with list - uses first match."""
        item = {"content": "First", "text": "Second"}
        assert extract_field(item, ["content", "text"]) == "First"

    def test_list_field_spec_second_match(self):
        """Test extraction with list - falls through to second."""
        item = {"text": "Found"}
        assert extract_field(item, ["missing", "text"]) == "Found"

    def test_callable_field_spec(self):
        """Test extraction with callable field spec."""
        item = {"parts": ["Hello", "World"]}
        extractor = lambda x: " ".join(x.get("parts", []))
        assert extract_field(item, extractor) == "Hello World"

    def test_callable_with_error(self):
        """Test callable that raises exception returns None."""
        item = {"data": "test"}
        extractor = lambda x: x["missing"]["value"]
        assert extract_field(item, extractor) is None


class TestParseDate:
    """Test parse_date function."""

    def test_iso_date(self):
        """Test parsing ISO date string."""
        result = parse_date("2024-01-15T10:30:00")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_iso_date_with_z(self):
        """Test parsing ISO date with Z suffix."""
        result = parse_date("2024-01-15T10:30:00Z")
        assert result.year == 2024

    def test_none_returns_now(self):
        """Test that None returns current datetime."""
        result = parse_date(None)
        assert isinstance(result, datetime)
        assert result.date() == datetime.now().date()

    def test_invalid_date_returns_now(self):
        """Test that invalid date returns current datetime."""
        result = parse_date("not a date")
        assert isinstance(result, datetime)


class TestExtractAuthor:
    """Test extract_author function."""

    def test_string_author(self):
        """Test extracting string author."""
        item = {"author": "JohnDoe"}
        mapping = FieldMapping()
        assert extract_author(item, mapping) == "JohnDoe"

    def test_dict_author_with_username(self):
        """Test extracting author from dict with username."""
        item = {"author": {"username": "johnd", "name": "John Doe"}}
        mapping = FieldMapping()
        assert extract_author(item, mapping) == "johnd"

    def test_dict_author_with_name(self):
        """Test extracting author from dict with name (no username)."""
        item = {"author": {"name": "John Doe"}}
        mapping = FieldMapping()
        assert extract_author(item, mapping) == "John Doe"


class TestExtractTitle:
    """Test extract_title function."""

    def test_explicit_title(self):
        """Test extracting explicit title."""
        item = {"title": "My Title", "text": "Content here"}
        mapping = FieldMapping()
        assert extract_title(item, mapping) == "My Title"

    def test_fallback_to_text(self):
        """Test fallback to first line of text."""
        item = {"text": "First line\nSecond line\nThird line"}
        mapping = FieldMapping()
        assert extract_title(item, mapping) == "First line"

    def test_fallback_to_url(self):
        """Test fallback to URL when no title or text."""
        item = {"url": "https://example.com/page"}
        mapping = FieldMapping()
        assert extract_title(item, mapping) == "https://example.com/page"

    def test_untitled_fallback(self):
        """Test 'Untitled' fallback when nothing found."""
        item = {}
        mapping = FieldMapping()
        assert extract_title(item, mapping) == "Untitled"

    def test_max_length(self):
        """Test title truncation to max length."""
        item = {"title": "A" * 300}
        mapping = FieldMapping()
        result = extract_title(item, mapping, max_length=50)
        assert len(result) == 50


class TestParseItem:
    """Test parse_item function."""

    def test_parse_basic_item(self):
        """Test parsing a basic item."""
        item = {
            "id": "123",
            "text": "Hello world",
            "url": "https://example.com/post/123",
            "likeCount": 42,
            "replyCount": 5,
            "createdAt": "2024-01-15T10:30:00Z",
        }
        result = parse_item(item, "twitter")

        assert result is not None
        assert result.id == "123"
        assert result.text == "Hello world"
        assert result.url == "https://example.com/post/123"
        assert result.score == 42
        assert result.comment_count == 5
        assert result.source == "twitter"

    def test_parse_item_with_custom_mapping(self):
        """Test parsing with custom field mapping."""
        item = {"content": "My content", "link": "https://example.com"}
        mapping = FieldMapping(text="content", url="link")
        result = parse_item(item, "custom", mapping)

        assert result is not None
        assert result.text == "My content"
        assert result.url == "https://example.com"

    def test_parse_item_generates_id(self):
        """Test that missing ID is auto-generated."""
        item = {"text": "Hello world", "url": "https://example.com"}
        result = parse_item(item, "test")

        assert result is not None
        assert result.id is not None
        assert len(result.id) == 12  # MD5 hash truncated to 12 chars

    def test_parse_invalid_item_returns_none(self):
        """Test that item without text or URL returns None."""
        item = {"likeCount": 42}
        result = parse_item(item, "test")
        assert result is None


class TestParseItems:
    """Test parse_items function."""

    def test_parse_multiple_items(self):
        """Test parsing multiple items."""
        items = [
            {"text": "Post 1", "url": "https://example.com/1"},
            {"text": "Post 2", "url": "https://example.com/2"},
            {"text": "Post 3", "url": "https://example.com/3"},
        ]
        results = parse_items(items, "test")

        assert len(results) == 3
        assert results[0].text == "Post 1"
        assert results[2].text == "Post 3"

    def test_parse_items_skips_invalid(self):
        """Test that invalid items are skipped."""
        items = [
            {"text": "Valid", "url": "https://example.com/1"},
            {},  # Invalid - no text or url
            {"text": "Also valid", "url": "https://example.com/2"},
        ]
        results = parse_items(items, "test")

        assert len(results) == 2

    def test_parse_items_empty_list(self):
        """Test parsing empty list."""
        results = parse_items([], "test")
        assert results == []


class TestFieldMapping:
    """Test FieldMapping dataclass."""

    def test_default_mapping(self):
        """Test default field mapping values."""
        mapping = FieldMapping()

        assert isinstance(mapping.text, list)
        assert "text" in mapping.text
        assert "content" in mapping.text

        assert isinstance(mapping.url, list)
        assert "url" in mapping.url

    def test_custom_mapping(self):
        """Test custom field mapping."""
        mapping = FieldMapping(text="custom_text", url="custom_url")

        assert mapping.text == "custom_text"
        assert mapping.url == "custom_url"


class TestParsedItem:
    """Test ParsedItem dataclass."""

    def test_parsed_item_creation(self):
        """Test creating ParsedItem."""
        item = ParsedItem(
            id="123",
            text="Hello",
            url="https://example.com",
            title="Test Title",
            author="author",
            timestamp=datetime.now(),
            score=42,
            comment_count=5,
            source="twitter",
            raw={"original": "data"},
        )

        assert item.id == "123"
        assert item.text == "Hello"
        assert item.score == 42
        assert item.source == "twitter"
        assert item.raw == {"original": "data"}
