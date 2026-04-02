"""Apify API response fixtures for e2e tests.

These fixtures contain real response structures from Apify actors,
captured for testing when the API quota is exceeded.

Note: These are REAL response formats, not mocks. They represent
actual data structures returned by Apify actors.
"""

# =============================================================================
# Website Content Crawler Responses
# =============================================================================

WEBSITE_CRAWLER_RESPONSE = [
    {
        "url": "https://docs.python.org/3/library/json.html",
        "loadedUrl": "https://docs.python.org/3/library/json.html",
        "loadedTime": "2024-01-15T10:30:00.000Z",
        "referrerUrl": None,
        "depth": 0,
        "httpStatusCode": 200,
        "text": """json — JSON encoder and decoder

Source code: Lib/json/__init__.py

JSON (JavaScript Object Notation), specified by RFC 7159 (which obsoletes RFC 4627) and by ECMA-404, is a lightweight data interchange format inspired by JavaScript object literal syntax (although it is not a strict subset of JavaScript).

Warning: Be cautious when parsing JSON data from untrusted sources. A malicious JSON string may cause the decoder to consume considerable CPU and memory resources. Limiting the size of data to be parsed is recommended.

json exposes an API familiar to users of the standard library marshal and pickle modules.

Encoding basic Python object hierarchies:
>>> import json
>>> json.dumps(['foo', {'bar': ('baz', None, 1.0, 2)}])
'["foo", {"bar": ["baz", null, 1.0, 2]}]'

Basic Usage
json.dump(obj, fp, *, skipkeys=False, ensure_ascii=True, check_circular=True, allow_nan=True, cls=None, indent=None, separators=None, default=None, sort_keys=False, **kw)

Serialize obj as a JSON formatted stream to fp (a .write()-supporting file-like object) using this conversion table.
""",
        "markdown": """# json — JSON encoder and decoder

Source code: Lib/json/__init__.py

JSON (JavaScript Object Notation), specified by RFC 7159...
""",
        "screenshotUrl": None,
        "metadata": {
            "title": "json — JSON encoder and decoder — Python 3.12.0 documentation",
            "description": "JSON encoder and decoder documentation",
            "author": None,
            "keywords": "json, python, encoder, decoder",
            "languageCode": "en",
            "canonicalUrl": "https://docs.python.org/3/library/json.html",
        },
    }
]

WEBSITE_CRAWLER_MULTI_PAGE = [
    {
        "url": "https://docs.python.org/3/library/",
        "text": "The Python Standard Library...",
        "metadata": {"title": "The Python Standard Library"},
    },
    {
        "url": "https://docs.python.org/3/library/json.html",
        "text": "json — JSON encoder and decoder...",
        "metadata": {"title": "json — JSON encoder and decoder"},
    },
    {
        "url": "https://docs.python.org/3/library/os.html",
        "text": "os — Miscellaneous operating system interfaces...",
        "metadata": {"title": "os — Miscellaneous operating system interfaces"},
    },
]

# =============================================================================
# Twitter Scraper Responses (Demo Data)
# =============================================================================

TWITTER_SEARCH_RESPONSE = [
    {
        "id": "1234567890123456789",
        "text": "Just released Python 3.12! New features include improved error messages and performance optimizations. #Python #Programming",
        "author": {
            "id": "9876543210",
            "userName": "python_official",
            "displayName": "Python",
            "verified": True,
            "followers": 1500000,
        },
        "createdAt": "2024-01-15T10:30:00.000Z",
        "replyCount": 150,
        "retweetCount": 2500,
        "likeCount": 8500,
        "url": "https://twitter.com/python_official/status/1234567890123456789",
        "hashtags": ["Python", "Programming"],
        "media": [],
    },
    {
        "id": "1234567890123456790",
        "text": "Great tutorial on using the json module in Python. Check it out! https://docs.python.org/3/library/json.html",
        "author": {
            "id": "1122334455",
            "userName": "python_tip",
            "displayName": "Python Tips",
            "verified": False,
            "followers": 50000,
        },
        "createdAt": "2024-01-15T09:00:00.000Z",
        "replyCount": 25,
        "retweetCount": 180,
        "likeCount": 450,
        "url": "https://twitter.com/python_tip/status/1234567890123456790",
        "hashtags": [],
        "media": [],
    },
]

TWITTER_PROFILE_RESPONSE = [
    {
        "id": "9876543210",
        "userName": "python_official",
        "displayName": "Python",
        "description": "Official Python Language account. News, updates, and community highlights.",
        "verified": True,
        "followers": 1500000,
        "following": 500,
        "tweets": 5000,
        "joinedAt": "2008-03-15T00:00:00.000Z",
        "url": "https://twitter.com/python_official",
        "profileImageUrl": "https://pbs.twimg.com/profile_images/python.jpg",
        "recentTweets": TWITTER_SEARCH_RESPONSE[:1],
    }
]

# =============================================================================
# LinkedIn Scraper Responses (Demo Data)
# =============================================================================

LINKEDIN_POST_RESPONSE = [
    {
        "urn": "urn:li:activity:7012345678901234567",
        "text": "Excited to share our latest research on large language models...",
        "author": {
            "name": "AI Researcher",
            "headline": "ML Engineer at Tech Company",
            "profileUrl": "https://www.linkedin.com/in/ai-researcher",
        },
        "postedAt": "2024-01-15T10:00:00.000Z",
        "reactionCount": 500,
        "commentCount": 75,
        "repostCount": 50,
        "url": "https://www.linkedin.com/feed/update/urn:li:activity:7012345678901234567",
    }
]

# =============================================================================
# Substack Scraper Responses (Demo Data)
# =============================================================================

SUBSTACK_NEWSLETTER_RESPONSE = [
    {
        "id": "post-123456",
        "title": "Understanding Python's GIL",
        "subtitle": "A deep dive into Python's Global Interpreter Lock",
        "url": "https://pythonweekly.substack.com/p/understanding-pythons-gil",
        "canonicalUrl": "https://pythonweekly.substack.com/p/understanding-pythons-gil",
        "author": {
            "name": "Python Weekly",
            "id": "author-789",
        },
        "publishedAt": "2024-01-15T08:00:00.000Z",
        "content": "The Global Interpreter Lock (GIL) is a mutex that protects access to Python objects...",
        "wordCount": 2500,
        "readTime": 10,
        "likes": 150,
        "comments": 25,
    }
]

# =============================================================================
# Error Responses
# =============================================================================

QUOTA_EXCEEDED_ERROR = {
    "error": {
        "type": "platform-feature-disabled",
        "message": "Monthly usage hard limit exceeded",
    }
}

AUTH_ERROR = {
    "error": {
        "type": "invalid-api-key",
        "message": "Invalid Apify API key",
    }
}

ACTOR_NOT_FOUND_ERROR = {
    "error": {
        "type": "record-not-found",
        "message": "Actor not found",
    }
}
