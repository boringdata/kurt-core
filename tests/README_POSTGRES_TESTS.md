# PostgreSQL Tests

This directory contains tests for Kurt's PostgreSQL integration and multi-tenant features.

## Test Structure

```
tests/
├── config/
│   └── test_postgres_config.py      # Configuration and .env loading tests
├── db/
│   ├── test_database_factory.py     # Database client factory tests
│   └── test_postgresql_client.py    # PostgreSQL client tests (requires DB)
└── commands/
    └── test_migrate_db.py           # Migration command tests
```

## Running Tests

### Unit Tests (No Database Required)

```bash
# Run all unit tests (mocked, no real PostgreSQL needed)
pytest tests/config/test_postgres_config.py
pytest tests/db/test_database_factory.py
pytest tests/commands/test_migrate_db.py

# Or run all non-integration tests
pytest -m "not integration"
```

### Integration Tests (Requires PostgreSQL)

Integration tests require a running PostgreSQL instance.

#### Option 1: Use Supabase (Recommended)

1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Get your connection string from Settings → Database
3. Set environment variable:

```bash
export TEST_POSTGRES_URL="postgresql://postgres:YOUR-PASSWORD@db.xxx.supabase.co:5432/postgres"
```

4. Run integration tests:

```bash
pytest tests/db/test_postgresql_client.py -m integration
```

#### Option 2: Use Docker

1. Start PostgreSQL container:

```bash
docker run -d \
  --name kurt-test-postgres \
  -e POSTGRES_PASSWORD=testpass \
  -e POSTGRES_DB=kurt_test \
  -p 5432:5432 \
  postgres:15-alpine

# Install pgvector extension
docker exec kurt-test-postgres \
  psql -U postgres -d kurt_test -c "CREATE EXTENSION IF NOT EXISTS vector"
```

2. Set environment variable:

```bash
export TEST_POSTGRES_URL="postgresql://postgres:testpass@localhost:5432/kurt_test"
```

3. Run integration tests:

```bash
pytest tests/db/test_postgresql_client.py -m integration
```

4. Clean up:

```bash
docker stop kurt-test-postgres
docker rm kurt-test-postgres
```

#### Option 3: Use Local PostgreSQL

1. Install PostgreSQL locally
2. Create test database:

```bash
createdb kurt_test
psql kurt_test -c "CREATE EXTENSION vector"
```

3. Set environment variable:

```bash
export TEST_POSTGRES_URL="postgresql://localhost:5432/kurt_test"
```

4. Run integration tests:

```bash
pytest tests/db/test_postgresql_client.py -m integration
```

### Run All Tests

```bash
# Run all tests (skip integration if TEST_POSTGRES_URL not set)
pytest

# Run all tests including integration
export TEST_POSTGRES_URL="postgresql://..."
pytest

# Run with coverage
pytest --cov=kurt.db --cov=kurt.config --cov-report=html
```

## Test Markers

Tests are marked with pytest markers:

- `@pytest.mark.integration` - Requires real PostgreSQL database
- `@pytest.mark.asyncio` - Async tests (requires pytest-asyncio)

## What's Tested

### Configuration Tests (`test_postgres_config.py`)
- ✅ KurtConfig supports DATABASE_URL and WORKSPACE_ID
- ✅ Loading from .env file
- ✅ .env overrides kurt.config
- ✅ Environment variables override both
- ✅ Configuration priority (shell > .env > kurt.config)
- ✅ Writing config with DATABASE_URL

### Factory Tests (`test_database_factory.py`)
- ✅ Returns SQLiteClient by default
- ✅ Returns PostgreSQLClient when DATABASE_URL is set
- ✅ Both clients implement DatabaseClient interface
- ✅ Mode switching based on config
- ✅ Connection string validation

### PostgreSQL Client Tests (`test_postgresql_client.py`)
- ✅ Connection to PostgreSQL
- ✅ Document CRUD operations
- ✅ Entity CRUD operations
- ✅ Workspace isolation (multi-tenancy)
- ✅ Async session support
- ✅ Password masking

### Migration Command Tests (`test_migrate_db.py`)
- ✅ Command registration
- ✅ Required arguments validation
- ✅ Help text
- ✅ Config update after migration
- ✅ Password masking

## Continuous Integration

For CI/CD pipelines, use GitHub Actions with PostgreSQL service:

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: kurt_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Install pgvector
        run: |
          sudo apt-get update
          sudo apt-get install -y postgresql-client
          PGPASSWORD=testpass psql -h localhost -U postgres -d kurt_test \
            -c "CREATE EXTENSION IF NOT EXISTS vector"

      - name: Run tests
        env:
          TEST_POSTGRES_URL: postgresql://postgres:testpass@localhost:5432/kurt_test
        run: |
          pytest --cov=kurt --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Troubleshooting

### "TEST_POSTGRES_URL not set" - Tests Skipped

Integration tests are automatically skipped if `TEST_POSTGRES_URL` is not set. This is intentional to allow running unit tests without a database.

To run integration tests, set the environment variable:

```bash
export TEST_POSTGRES_URL="postgresql://..."
```

### Connection Refused

Make sure PostgreSQL is running and accessible:

```bash
# Test connection
psql "$TEST_POSTGRES_URL" -c "SELECT 1"
```

### pgvector Extension Missing

Some tests require the pgvector extension:

```bash
# Install extension
psql "$TEST_POSTGRES_URL" -c "CREATE EXTENSION IF NOT EXISTS vector"
```

### Permission Denied

Make sure your PostgreSQL user has permissions:

```sql
-- Grant all permissions on database
GRANT ALL PRIVILEGES ON DATABASE kurt_test TO postgres;

-- Grant all permissions on schema
GRANT ALL ON SCHEMA public TO postgres;
```

## Writing New Tests

### Unit Tests (Mocked)

```python
from unittest.mock import patch

def test_my_feature():
    """Test description."""
    with patch("kurt.db.base.get_config_or_default") as mock_config:
        mock_config.return_value = KurtConfig(
            DATABASE_URL="postgresql://..."
        )

        # Your test code here
```

### Integration Tests (Real Database)

```python
import pytest

@pytest.mark.integration
def test_my_feature(postgres_url, workspace_id):
    """Test description."""
    client = PostgreSQLClient(
        database_url=postgres_url,
        workspace_id=workspace_id
    )

    # Your test code here
```

## Coverage Goals

Target coverage for PostgreSQL integration:

- Configuration loading: > 90%
- Database client factory: > 95%
- PostgreSQL client: > 80% (excluding async edge cases)
- Migration command: > 70% (complex CLI interactions)

Current coverage:

```bash
# Generate coverage report
pytest --cov=kurt.db --cov=kurt.config --cov-report=term-missing
```
