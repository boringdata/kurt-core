"""Analytics statistics and utilities for Kurt telemetry."""

from typing import Optional


def get_analytics_stats(include_pattern: Optional[str] = None) -> dict:
    """
    Get analytics statistics with percentile-based traffic thresholds.

    Calculates traffic distribution and returns
    percentile thresholds for categorizing pages as HIGH/MEDIUM/LOW/ZERO traffic.

    Args:
        include_pattern: Optional glob pattern to filter documents

    Returns:
        Dictionary with analytics statistics:
            - has_data: bool
            - total_pageviews: int
            - avg_pageviews: float
            - median_pageviews: float
            - p75_pageviews: float (75th percentile - HIGH threshold)
            - p25_pageviews: float (25th percentile - LOW threshold)
            - tier_counts: dict with zero/low/medium/high counts
            - trend_counts: dict with increasing/decreasing/stable counts

    Example:
        stats = get_analytics_stats(include_pattern="*docs.company.com*")
        print(f"HIGH traffic threshold (p75): {stats['p75_pageviews']} views/month")
    """
    from fnmatch import fnmatch

    from kurt.db.database import get_session
    from kurt.db.models import Document, DocumentAnalytics, TrendType

    session = get_session()

    # Build query for documents with analytics
    from sqlmodel import select

    stmt = select(DocumentAnalytics).join(Document, Document.id == DocumentAnalytics.document_id)

    all_analytics = session.exec(stmt).all()

    # Apply glob filtering if provided
    if include_pattern:
        # Need to get the documents to apply glob
        filtered_analytics = []
        for analytics in all_analytics:
            doc = session.get(Document, analytics.document_id)
            if doc and (
                (doc.source_url and fnmatch(doc.source_url, include_pattern))
                or (doc.content_path and fnmatch(str(doc.content_path), include_pattern))
            ):
                filtered_analytics.append(analytics)
        analytics = filtered_analytics
    else:
        analytics = list(all_analytics)

    if not analytics:
        return {
            "has_data": False,
            "total_pageviews": 0,
            "avg_pageviews": 0,
            "median_pageviews": 0,
            "p75_pageviews": 0,
            "p25_pageviews": 0,
            "tier_counts": {"zero": 0, "low": 0, "medium": 0, "high": 0},
            "trend_counts": {"increasing": 0, "decreasing": 0, "stable": 0},
        }

    # Extract pageviews and sort
    pageviews = [a.pageviews_30d or 0 for a in analytics]
    pageviews_sorted = sorted(pageviews)
    total_pageviews = sum(pageviews)

    # Count zero traffic pages
    zero_traffic = sum(1 for pv in pageviews if pv == 0)

    # Remove zeros for percentile calculation
    pageviews_nonzero = [pv for pv in pageviews_sorted if pv > 0]

    if not pageviews_nonzero:
        # All pages have zero traffic
        trend_counts = {
            "increasing": sum(1 for a in analytics if a.pageviews_trend == TrendType.increasing),
            "decreasing": sum(1 for a in analytics if a.pageviews_trend == TrendType.decreasing),
            "stable": sum(1 for a in analytics if a.pageviews_trend == TrendType.stable),
        }
        return {
            "has_data": True,
            "total_pageviews": 0,
            "avg_pageviews": 0,
            "median_pageviews": 0,
            "p75_pageviews": 0,
            "p25_pageviews": 0,
            "tier_counts": {"zero": zero_traffic, "low": 0, "medium": 0, "high": 0},
            "trend_counts": trend_counts,
        }

    # Calculate statistics
    avg = sum(pageviews_nonzero) / len(pageviews_nonzero)

    # Percentiles (using non-zero traffic only)
    def percentile(data, p):
        """Calculate percentile (0-100)"""
        if not data:
            return 0
        n = len(data)
        idx = int(n * p / 100)
        return data[min(idx, n - 1)]

    median = percentile(pageviews_nonzero, 50)
    p25 = percentile(pageviews_nonzero, 25)
    p75 = percentile(pageviews_nonzero, 75)

    # Categorize pages using percentiles
    tier_counts = {
        "zero": zero_traffic,
        "low": sum(1 for pv in pageviews_nonzero if pv <= p25),
        "medium": sum(1 for pv in pageviews_nonzero if p25 < pv <= p75),
        "high": sum(1 for pv in pageviews_nonzero if pv > p75),
    }

    # Count trends
    trend_counts = {
        "increasing": sum(1 for a in analytics if a.pageviews_trend == TrendType.increasing),
        "decreasing": sum(1 for a in analytics if a.pageviews_trend == TrendType.decreasing),
        "stable": sum(1 for a in analytics if a.pageviews_trend == TrendType.stable),
    }

    return {
        "has_data": True,
        "total_pageviews": total_pageviews,
        "avg_pageviews": round(avg, 1),
        "median_pageviews": median,
        "p75_pageviews": p75,
        "p25_pageviews": p25,
        "tier_counts": tier_counts,
        "trend_counts": trend_counts,
    }
