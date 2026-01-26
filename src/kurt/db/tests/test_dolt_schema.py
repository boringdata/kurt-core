"""Tests for Dolt schema initialization."""


from kurt.db.dolt import (
    OBSERVABILITY_TABLES,
    SCHEMA_FILE,
    get_schema_sql,
    get_table_ddl,
    split_sql_statements,
)


class TestSchemaFile:
    """Tests for schema file loading."""

    def test_schema_file_exists(self):
        """Schema file should exist at expected location."""
        assert SCHEMA_FILE.exists(), f"Schema file not found: {SCHEMA_FILE}"

    def test_get_schema_sql_returns_content(self):
        """get_schema_sql should return non-empty SQL."""
        sql = get_schema_sql()
        assert sql, "Schema SQL should not be empty"
        assert "CREATE TABLE" in sql.upper()

    def test_schema_contains_all_tables(self):
        """Schema should define all observability tables."""
        sql = get_schema_sql()
        for table in OBSERVABILITY_TABLES:
            assert table in sql, f"Table {table} not found in schema"


class TestSplitSqlStatements:
    """Tests for SQL statement splitting."""

    def test_split_simple_statements(self):
        """Should split statements separated by newlines."""
        sql = """CREATE TABLE a (id INT);
CREATE TABLE b (id INT);"""
        stmts = split_sql_statements(sql)
        assert len(stmts) == 2
        assert "CREATE TABLE a" in stmts[0]
        assert "CREATE TABLE b" in stmts[1]

    def test_skip_comments(self):
        """Should skip comment-only lines."""
        sql = """
        -- This is a comment
        CREATE TABLE test (id INT);
        -- Another comment
        """
        stmts = split_sql_statements(sql)
        assert len(stmts) == 1
        assert "CREATE TABLE test" in stmts[0]

    def test_handle_multiline_statement(self):
        """Should handle multi-line CREATE TABLE."""
        sql = """
        CREATE TABLE test (
            id INT PRIMARY KEY,
            name VARCHAR(255)
        );
        """
        stmts = split_sql_statements(sql)
        assert len(stmts) == 1
        assert "id INT PRIMARY KEY" in stmts[0]
        assert "name VARCHAR(255)" in stmts[0]

    def test_skip_empty_lines(self):
        """Should skip empty lines."""
        sql = """

        CREATE TABLE a (id INT);


        CREATE TABLE b (id INT);

        """
        stmts = split_sql_statements(sql)
        assert len(stmts) == 2

    def test_real_schema_splits_correctly(self):
        """Actual schema should split into multiple statements."""
        sql = get_schema_sql()
        stmts = split_sql_statements(sql)

        # Should have CREATE TABLE statements
        create_stmts = [s for s in stmts if "CREATE TABLE" in s.upper()]
        assert len(create_stmts) >= 5, "Should have at least 5 CREATE TABLE statements"

        # Core observability tables should each have exactly one CREATE TABLE statement
        # Note: OBSERVABILITY_TABLES includes "documents" which is a VIEW, not a table
        core_tables = ["workflow_runs", "step_logs", "step_events", "llm_traces"]
        for table in core_tables:
            # Match "CREATE TABLE ... <table_name> (" to avoid matching FK references
            matching = [s for s in create_stmts if f"TABLE IF NOT EXISTS {table} (" in s or f"TABLE {table} (" in s]
            assert len(matching) == 1, f"Expected exactly one CREATE for {table}"


class TestTableDDL:
    """Tests for individual table DDL extraction."""

    def test_get_workflow_runs_ddl(self):
        """Should extract workflow_runs DDL."""
        ddl = get_table_ddl("workflow_runs")
        assert ddl is not None
        assert "workflow_runs" in ddl
        assert "id VARCHAR(36) PRIMARY KEY" in ddl
        assert "status VARCHAR(20)" in ddl
        assert "idx_workflow_runs_status" in ddl

    def test_get_step_logs_ddl(self):
        """Should extract step_logs DDL."""
        ddl = get_table_ddl("step_logs")
        assert ddl is not None
        assert "step_logs" in ddl
        assert "run_id VARCHAR(36)" in ddl
        assert "UNIQUE KEY uq_step_logs_run_step" in ddl

    def test_get_step_events_ddl(self):
        """Should extract step_events DDL."""
        ddl = get_table_ddl("step_events")
        assert ddl is not None
        assert "step_events" in ddl
        assert "id BIGINT PRIMARY KEY AUTO_INCREMENT" in ddl
        assert "idx_step_events_run_id" in ddl

    def test_unknown_table_returns_none(self):
        """Should return None for unknown table."""
        ddl = get_table_ddl("nonexistent_table")
        assert ddl is None


class TestSchemaContent:
    """Tests for schema content correctness."""

    def test_workflow_runs_has_required_columns(self):
        """workflow_runs should have all required columns."""
        ddl = get_table_ddl("workflow_runs")
        required = ["id", "workflow", "status", "started_at", "completed_at", "error", "inputs", "metadata"]
        for col in required:
            assert col in ddl, f"Missing column: {col}"

    def test_step_logs_has_required_columns(self):
        """step_logs should have all required columns."""
        ddl = get_table_ddl("step_logs")
        required = [
            "id",
            "run_id",
            "step_id",
            "tool",
            "status",
            "started_at",
            "completed_at",
            "input_count",
            "output_count",
            "error_count",
            "errors",
            "metadata",
        ]
        for col in required:
            assert col in ddl, f"Missing column: {col}"

    def test_step_events_has_required_columns(self):
        """step_events should have all required columns."""
        ddl = get_table_ddl("step_events")
        required = [
            "id",
            "run_id",
            "step_id",
            "substep",
            "status",
            "created_at",
            "current",
            "total",
            "message",
            "metadata",
        ]
        for col in required:
            assert col in ddl, f"Missing column: {col}"

    def test_step_events_id_is_auto_increment(self):
        """step_events.id should be BIGINT AUTO_INCREMENT for streaming."""
        ddl = get_table_ddl("step_events")
        assert "BIGINT" in ddl.upper()
        assert "AUTO_INCREMENT" in ddl.upper()

    def test_step_events_has_streaming_index(self):
        """step_events should have index for streaming cursor (run_id, id)."""
        ddl = get_table_ddl("step_events")
        # Check for index on (run_id, id) for efficient streaming
        assert "idx_step_events_run_id" in ddl
        assert "run_id, id" in ddl

    def test_step_logs_has_unique_constraint(self):
        """step_logs should have unique constraint on (run_id, step_id)."""
        ddl = get_table_ddl("step_logs")
        assert "UNIQUE" in ddl.upper()
        assert "run_id, step_id" in ddl


class TestObservabilityTables:
    """Tests for OBSERVABILITY_TABLES constant."""

    def test_contains_expected_tables(self):
        """Should contain all observability tables."""
        expected = ["workflow_runs", "step_logs", "step_events", "documents", "llm_traces"]
        assert OBSERVABILITY_TABLES == expected

    def test_order_is_correct_for_creation(self):
        """Tables should be in dependency order (workflow_runs first)."""
        # workflow_runs has no dependencies
        # step_logs references workflow_runs
        # step_events references nothing (no FK to avoid bottleneck)
        # documents has no dependencies
        # llm_traces has no dependencies
        assert OBSERVABILITY_TABLES[0] == "workflow_runs"
        assert "step_logs" in OBSERVABILITY_TABLES
        assert "step_events" in OBSERVABILITY_TABLES
        assert "documents" in OBSERVABILITY_TABLES
        assert "llm_traces" in OBSERVABILITY_TABLES


class TestLLMTracesContent:
    """Tests for llm_traces table schema."""

    def test_get_llm_traces_ddl(self):
        """Should extract llm_traces DDL."""
        ddl = get_table_ddl("llm_traces")
        assert ddl is not None
        assert "llm_traces" in ddl
        assert "id VARCHAR(36) PRIMARY KEY" in ddl

    def test_llm_traces_has_required_columns(self):
        """llm_traces should have all required columns."""
        ddl = get_table_ddl("llm_traces")
        required = [
            "id",
            "run_id",
            "step_id",
            "model",
            "provider",
            "prompt",
            "response",
            "structured_output",
            "tokens_in",
            "tokens_out",
            "cost_usd",
            "latency_ms",
            "error",
            "retry_count",
            "created_at",
        ]
        for col in required:
            assert col in ddl, f"Missing column: {col}"

    def test_llm_traces_has_indexes(self):
        """llm_traces should have required indexes."""
        ddl = get_table_ddl("llm_traces")
        assert "idx_llm_traces_run" in ddl
        assert "idx_llm_traces_created" in ddl
        assert "idx_llm_traces_model" in ddl
