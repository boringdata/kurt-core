"""
Perplexity API adapter implementation.

Uses Perplexity's chat completions API for research queries.
"""

import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import requests

from kurt.integrations.research.base import Citation, ResearchAdapter, ResearchResult


class PerplexityAdapter(ResearchAdapter):
    """Adapter for Perplexity AI research API."""

    API_URL = "https://api.perplexity.ai/chat/completions"

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Perplexity client.

        Required config keys:
        - api_key: Perplexity API key
        - default_model: Model to use (default: sonar-reasoning)
        - default_recency: Time filter (default: day)
        - max_tokens: Max response tokens
        - temperature: Response temperature
        """
        self.api_key = config["api_key"]
        self.default_model = config.get("default_model", "sonar-reasoning")
        self.default_recency = config.get("default_recency", "day")
        self.max_tokens = config.get("max_tokens", 4000)
        self.temperature = config.get("temperature", 0.2)

    def test_connection(self) -> bool:
        """Test if Perplexity API connection is working."""
        try:
            # Simple test query
            result = self.search("test", recency="day")
            return result is not None
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False

    def search(
        self, query: str, recency: Optional[str] = None, model: Optional[str] = None, **kwargs
    ) -> ResearchResult:
        """
        Execute research query via Perplexity API.

        Args:
            query: Research question or topic
            recency: Time filter (hour, day, week, month)
            model: Override default model
            **kwargs: Additional parameters

        Returns:
            ResearchResult with synthesized answer and citations
        """
        start_time = time.time()

        # Build request
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        # Map recency to search_recency_filter
        recency_map = {"hour": "hour", "day": "day", "week": "week", "month": "month"}
        search_recency = recency_map.get(recency or self.default_recency, "day")

        payload = {
            "model": model or self.default_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful research assistant. Provide comprehensive, well-researched answers with citations.",
                },
                {"role": "user", "content": query},
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "search_recency_filter": search_recency,
            "return_citations": True,
            "return_images": False,
            "search_domain_filter": kwargs.get("domains", []),
        }

        # Make request
        response = requests.post(
            self.API_URL,
            headers=headers,
            json=payload,
            timeout=120,  # 2 minute timeout for long research
        )

        response.raise_for_status()
        data = response.json()

        # Extract response
        answer = data["choices"][0]["message"]["content"]

        # Extract citations
        citations = []
        if "citations" in data:
            for i, cite_url in enumerate(data["citations"], 1):
                # Try to get title from the content if available
                # Perplexity includes citation markers like [1], [2] in the text
                citation = Citation(
                    title=f"Source {i}", url=cite_url, domain=self._extract_domain(cite_url)
                )
                citations.append(citation)

        # Calculate response time
        response_time = time.time() - start_time

        # Generate result ID
        result_id = f"res_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"

        return ResearchResult(
            id=result_id,
            query=query,
            answer=answer,
            citations=citations,
            source="perplexity",
            model=model or self.default_model,
            timestamp=datetime.now(),
            response_time_seconds=response_time,
            metadata={"recency": search_recency, "model": model or self.default_model},
        )

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return url
