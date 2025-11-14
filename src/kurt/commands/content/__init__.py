"""Content management commands - unified document operations."""

import click

from .cluster import cluster_urls_cmd
from .delete import delete_document_cmd
from .fetch import fetch_cmd
from .get import get_document_cmd
from .index import index
from .list import list_documents_cmd
from .list_clusters import list_clusters_cmd
from .list_technologies import list_technologies_cmd
from .list_topics import list_topics_cmd
from .map import map_cmd
from .search import search_cmd
from .stats import stats_cmd
from .sync_metadata import sync_metadata


@click.group()
def content():
    """
    Manage documents and metadata.

    \b
    Available commands:
    - fetch: Fetch and index content from URLs
    - map: Discover content without downloading
    - search: Search document content with ripgrep
    - cluster: Organize documents into topic clusters
    - list: View all documents with filters
    - list-topics: List all topics from metadata/graph
    - list-technologies: List all technologies from metadata/graph
    - get: View single document details
    - index: Extract metadata with LLM
    - delete: Remove documents
    - stats: View statistics
    - list-clusters: View topic clusters
    - sync-metadata: Update file frontmatter
    """
    pass


# Register all subcommands
content.add_command(fetch_cmd, name="fetch")
content.add_command(map_cmd, name="map")
content.add_command(search_cmd, name="search")
content.add_command(cluster_urls_cmd, name="cluster")
content.add_command(list_documents_cmd, name="list")
content.add_command(list_topics_cmd, name="list-topics")
content.add_command(list_technologies_cmd, name="list-technologies")
content.add_command(get_document_cmd, name="get")
content.add_command(index)
content.add_command(delete_document_cmd, name="delete")
content.add_command(stats_cmd, name="stats")
content.add_command(list_clusters_cmd, name="list-clusters")
content.add_command(sync_metadata, name="sync-metadata")
