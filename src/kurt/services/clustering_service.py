"""
Clustering service - business logic for topic clustering operations.

This service layer separates database queries and business logic from the command layer.
"""

from typing import Dict, List

from kurt.db.database import get_session
from kurt.db.models import DocumentClusterEdge, TopicCluster


def get_existing_clusters_summary() -> Dict[str, any]:
    """
    Get summary of existing clusters in the database.

    Returns:
        Dictionary with:
            - count: int (number of clusters)
            - clusters: list of TopicCluster objects

    Example:
        summary = get_existing_clusters_summary()
        print(f"Found {summary['count']} clusters")
        for cluster in summary['clusters']:
            print(f"  - {cluster.name}")
    """
    session = get_session()

    clusters = session.query(TopicCluster).all()

    return {
        "count": len(clusters),
        "clusters": clusters,
    }


def get_cluster_document_counts(cluster_names: List[str]) -> Dict[str, int]:
    """
    Get document counts for specific clusters by name.

    Args:
        cluster_names: List of cluster names to get counts for

    Returns:
        Dictionary mapping cluster names to document counts

    Example:
        counts = get_cluster_document_counts(["Documentation", "Blog Posts"])
        print(f"Documentation has {counts['Documentation']} docs")
    """
    session = get_session()

    counts = {}

    for cluster_name in cluster_names:
        # Find cluster by name
        cluster_record = (
            session.query(TopicCluster).filter(TopicCluster.name == cluster_name).first()
        )

        if cluster_record:
            # Count documents in cluster (from edges)
            doc_count = (
                session.query(DocumentClusterEdge)
                .filter(DocumentClusterEdge.cluster_id == cluster_record.id)
                .count()
            )
            counts[cluster_name] = doc_count
        else:
            counts[cluster_name] = 0

    return counts


def get_cluster_document_count(cluster_name: str) -> int:
    """
    Get document count for a single cluster by name.

    Args:
        cluster_name: Name of the cluster

    Returns:
        Number of documents in the cluster (0 if cluster not found)

    Example:
        count = get_cluster_document_count("Documentation")
        print(f"Documentation has {count} docs")
    """
    session = get_session()

    # Find cluster by name
    cluster_record = session.query(TopicCluster).filter(TopicCluster.name == cluster_name).first()

    if not cluster_record:
        return 0

    # Count documents in cluster (from edges)
    doc_count = (
        session.query(DocumentClusterEdge)
        .filter(DocumentClusterEdge.cluster_id == cluster_record.id)
        .count()
    )

    return doc_count
