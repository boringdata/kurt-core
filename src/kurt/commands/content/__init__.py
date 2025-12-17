"""Content management commands - unified document operations."""

import click


class LazyGroup(click.Group):
    """A Click group that lazily loads subcommands for the content module."""

    def __init__(self, *args, lazy_subcommands=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.lazy_subcommands = lazy_subcommands or {}

    def list_commands(self, ctx):
        return sorted(self.lazy_subcommands.keys())

    def get_command(self, ctx, name):
        if name in self.lazy_subcommands:
            # Lazy import the subcommand
            if name == "fetch":
                from .fetch import fetch_cmd

                return fetch_cmd
            elif name == "map":
                from .map import map_cmd

                return map_cmd
            elif name == "search":
                from .search import search_cmd

                return search_cmd
            elif name == "links":
                from .search import links_cmd

                return links_cmd
            elif name == "cluster":
                from .cluster import cluster_urls_cmd

                return cluster_urls_cmd
            elif name == "list":
                from .list import list_documents_cmd

                return list_documents_cmd
            elif name == "list-entities":
                from .list_entities import list_entities_cmd

                return list_entities_cmd
            elif name == "get":
                from .get import get_document_cmd

                return get_document_cmd
            elif name == "index":
                from .index import index

                return index
            elif name == "delete":
                from .delete import delete_document_cmd

                return delete_document_cmd
            elif name == "stats":
                from .stats import stats_cmd

                return stats_cmd
            elif name == "list-clusters":
                from .list_clusters import list_clusters_cmd

                return list_clusters_cmd
            elif name == "sync-metadata":
                from .sync_metadata import sync_metadata

                return sync_metadata
        return None


@click.group(
    cls=LazyGroup,
    lazy_subcommands={
        "fetch": True,
        "map": True,
        "search": True,
        "links": True,
        "cluster": True,
        "list": True,
        "list-entities": True,
        "get": True,
        "index": True,
        "delete": True,
        "stats": True,
        "list-clusters": True,
        "sync-metadata": True,
    },
)
def content():
    """
    Manage documents and metadata.

    \b
    Available commands:
    - fetch: Fetch and index content from URLs
    - map: Discover content without downloading
    - search: Search document content with ripgrep
    - links: Show links from/to a document
    - cluster: Organize documents into topic clusters
    - list: View all documents with filters
    - list-entities: List entities from knowledge graph (topics, technologies, etc.)
    - get: View single document details
    - index: Extract metadata with LLM
    - delete: Remove documents
    - stats: View statistics
    - list-clusters: View topic clusters
    - sync-metadata: Update file frontmatter
    """
    pass
