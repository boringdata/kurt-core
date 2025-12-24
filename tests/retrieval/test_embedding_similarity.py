"""Tests for embedding-based similarity retrieval.

This module tests that different embeddings produce different retrieval results
based on semantic similarity (cosine similarity of embeddings).
"""

import pytest
from sqlmodel import select

from kurt.db.database import get_session
from kurt.db.models import Document, Entity
from tests.retrieval.conftest import cosine_similarity


class TestEmbeddingSimilarity:
    """Test that embeddings affect similarity-based retrieval."""

    def test_embedding_similarity_groups(self, minimal_retrieval_fixture):
        """Test that documents in same similarity group have higher cosine similarity."""
        fixture = minimal_retrieval_fixture
        session = get_session()

        docs = session.exec(select(Document)).all()
        assert len(docs) == 5

        # Docs 0 and 3 are in similarity group 1 (DuckDB/database)
        # Docs 1 and 4 are in similarity group 2 (cloud/MotherDuck)
        # Doc 2 is in similarity group 3 (data formats)

        # Test: Doc 0 and Doc 3 should be more similar than Doc 0 and Doc 2
        sim_same_group = cosine_similarity(docs[0].embedding, docs[3].embedding)
        sim_diff_group = cosine_similarity(docs[0].embedding, docs[2].embedding)

        assert sim_same_group > sim_diff_group, \
            f"Same group similarity ({sim_same_group:.3f}) should be > different group ({sim_diff_group:.3f})"

        # Should have meaningful similarity difference (at least 0.2)
        assert sim_same_group - sim_diff_group > 0.2, \
            f"Similarity difference too small: {sim_same_group - sim_diff_group:.3f}"

    def test_document_ranking_by_similarity(self, minimal_retrieval_fixture):
        """Test that documents can be ranked by embedding similarity to a query."""
        fixture = minimal_retrieval_fixture
        session = get_session()

        docs = session.exec(select(Document)).all()

        # Use Doc 0 (DuckDB Introduction, group 1) as query
        query_doc = docs[0]

        # Rank all other docs by similarity to query
        rankings = []
        for doc in docs[1:]:
            sim = cosine_similarity(query_doc.embedding, doc.embedding)
            rankings.append((doc.title, sim))

        # Sort by similarity (descending)
        rankings.sort(key=lambda x: x[1], reverse=True)

        # Doc 3 (SQL Tutorial, also group 1) should rank higher than Doc 2 (Parquet, group 3)
        sql_tutorial_rank = next(i for i, (title, _) in enumerate(rankings) if "SQL" in title)
        parquet_rank = next(i for i, (title, _) in enumerate(rankings) if "Parquet" in title)

        assert sql_tutorial_rank < parquet_rank, \
            f"SQL Tutorial (group 1) should rank higher than Parquet (group 3): {sql_tutorial_rank} vs {parquet_rank}"

    def test_entity_similarity_affects_retrieval(self, minimal_retrieval_fixture):
        """Test that entity embeddings affect similarity-based entity retrieval."""
        fixture = minimal_retrieval_fixture
        session = get_session()

        entities = session.exec(select(Entity)).all()
        assert len(entities) == 10

        # Entities 0 (DuckDB), 3 (SQL), 4 (OLAP), 7 (Analytics), 8 (Pandas) are in group 1
        # Entity 1 (MotherDuck), 5 (Serverless), 6 (Cloud Storage) are in group 2
        # Entity 2 (Parquet), 9 (S3) are in group 3

        # Test: DuckDB should be more similar to SQL than to Parquet
        duckdb = next(e for e in entities if e.name == "DuckDB")
        sql = next(e for e in entities if e.name == "SQL")
        parquet = next(e for e in entities if e.name == "Parquet")

        sim_duckdb_sql = cosine_similarity(duckdb.embedding, sql.embedding)
        sim_duckdb_parquet = cosine_similarity(duckdb.embedding, parquet.embedding)

        assert sim_duckdb_sql > sim_duckdb_parquet, \
            f"DuckDB-SQL similarity ({sim_duckdb_sql:.3f}) should be > DuckDB-Parquet ({sim_duckdb_parquet:.3f})"

    def test_different_embeddings_different_results(self, minimal_retrieval_fixture):
        """Test that different query embeddings produce different retrieval results."""
        fixture = minimal_retrieval_fixture
        session = get_session()

        docs = session.exec(select(Document)).all()

        # Query 1: Use Doc 0 (DuckDB, group 1) as query
        query1 = docs[0]
        results1 = [(doc.title, cosine_similarity(query1.embedding, doc.embedding))
                    for doc in docs if doc.id != query1.id]
        results1.sort(key=lambda x: x[1], reverse=True)

        # Query 2: Use Doc 1 (MotherDuck, group 2) as query
        query2 = docs[1]
        results2 = [(doc.title, cosine_similarity(query2.embedding, doc.embedding))
                    for doc in docs if doc.id != query2.id]
        results2.sort(key=lambda x: x[1], reverse=True)

        # Top results should be different
        top_result1 = results1[0][0]
        top_result2 = results2[0][0]

        assert top_result1 != top_result2, \
            "Different query embeddings should produce different top results"

        # Verify: DuckDB query should rank SQL Tutorial higher
        assert "SQL" in top_result1 or "DuckDB" in top_result1, \
            f"DuckDB query should retrieve database-related docs, got: {top_result1}"

        # MotherDuck query should rank Cloud Warehouses higher
        assert "Cloud" in top_result2 or "MotherDuck" in top_result2, \
            f"MotherDuck query should retrieve cloud-related docs, got: {top_result2}"

    def test_similarity_score_range(self, minimal_retrieval_fixture):
        """Test that similarity scores are in valid range [0, 1]."""
        fixture = minimal_retrieval_fixture
        session = get_session()

        docs = session.exec(select(Document)).all()

        # Check self-similarity first
        for doc in docs:
            self_sim = cosine_similarity(doc.embedding, doc.embedding)
            assert abs(self_sim - 1.0) < 0.01, \
                f"Self-similarity of {doc.title} should be ~1.0, got {self_sim}"

        # Check all pairwise similarities
        for i, doc1 in enumerate(docs):
            for doc2 in docs[i+1:]:
                sim = cosine_similarity(doc1.embedding, doc2.embedding)

                # Cosine similarity should be in [-1, 1] for normalized vectors
                assert -1 <= sim <= 1, \
                    f"Similarity between {doc1.title} and {doc2.title} out of range: {sim}"

    def test_semantic_search_simulation(self, minimal_retrieval_fixture):
        """Simulate semantic search: rank docs by similarity to query embedding."""
        fixture = minimal_retrieval_fixture
        session = get_session()

        # Simulate user query: "Tell me about SQL and analytics"
        # This should match group 1 entities (DuckDB, SQL, Analytics)

        # Get a database/SQL entity as proxy for query
        entities = session.exec(select(Entity)).all()
        sql_entity = next(e for e in entities if e.name == "SQL")

        # Find documents by ranking their similarity to SQL entity
        docs = session.exec(select(Document)).all()
        ranked_docs = [
            (doc.title, cosine_similarity(sql_entity.embedding, doc.embedding))
            for doc in docs
        ]
        ranked_docs.sort(key=lambda x: x[1], reverse=True)

        # Top doc should be DuckDB Intro or SQL Tutorial (both group 1)
        top_doc = ranked_docs[0][0]
        assert "DuckDB" in top_doc or "SQL" in top_doc, \
            f"SQL query should retrieve database docs, got: {top_doc}"

        # Bottom doc should be from different group
        bottom_doc = ranked_docs[-1][0]
        # Should not be as highly ranked
        assert ranked_docs[0][1] > ranked_docs[-1][1] + 0.1, \
            "Top and bottom docs should have meaningful similarity difference"
