#!/bin/bash
#
# Setup script for kurt-cloud repository
#
# This script helps initialize the kurt-cloud repository with
# the correct structure and dependencies on kurt-core.
#
# Usage:
#   ./scripts/setup_kurt_cloud.sh [path-to-kurt-cloud]
#
# Example:
#   ./scripts/setup_kurt_cloud.sh ../kurt-cloud

set -e

KURT_CLOUD_DIR="${1:-../kurt-cloud}"
KURT_CORE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "🚀 Setting up kurt-cloud repository"
echo "   kurt-core: $KURT_CORE_DIR"
echo "   kurt-cloud: $KURT_CLOUD_DIR"
echo ""

# Create kurt-cloud directory
if [ ! -d "$KURT_CLOUD_DIR" ]; then
    echo "📁 Creating kurt-cloud directory..."
    mkdir -p "$KURT_CLOUD_DIR"
fi

cd "$KURT_CLOUD_DIR"

# Initialize git if needed
if [ ! -d ".git" ]; then
    echo "🔧 Initializing git repository..."
    git init
fi

# Create pyproject.toml
echo "📝 Creating pyproject.toml..."
cat > pyproject.toml <<'EOF'
[project]
name = "kurt-cloud"
version = "0.1.0"
description = "Kurt Cloud - Managed multi-tenant metadata service"
requires-python = ">=3.10"
dependencies = [
    "kurt-core>=0.3.0",
    "supabase>=2.0.0",
    "fastapi>=0.104.0",
    "uvicorn>=0.24.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "ruff>=0.1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]  # Line too long
EOF

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p supabase/migrations
mkdir -p supabase/functions
mkdir -p web/app
mkdir -p scripts
mkdir -p tests

# Create README
echo "📝 Creating README..."
cat > README.md <<'EOF'
# Kurt Cloud

Managed multi-tenant metadata service for Kurt.

## Architecture

- **PostgreSQL**: Supabase (managed)
- **Schema**: Imported from kurt-core SQLModel models
- **Auth**: Supabase Auth with device flow
- **Web**: Next.js dashboard

## Setup

### 1. Install Dependencies

```bash
uv pip install -e ".[dev]"
```

### 2. Initialize Supabase

```bash
# Install Supabase CLI
brew install supabase/tap/supabase

# Login
supabase login

# Initialize project
supabase init
```

### 3. Generate Schema Migration

```bash
# Generate SQL from kurt-core models
cd ../kurt-core
uv run python scripts/generate_postgres_schema.py \
  > ../kurt-cloud/supabase/migrations/$(date +%Y%m%d%H%M%S)_init_schema.sql
```

### 4. Apply Migrations

```bash
supabase db push
```

## Development

### Generate New Migration

When kurt-core models change:

```bash
cd ../kurt-core
uv run python scripts/generate_postgres_schema.py \
  > ../kurt-cloud/supabase/migrations/$(date +%Y%m%d%H%M%S)_update_schema.sql

cd ../kurt-cloud
supabase db push
```

### Run Tests

```bash
pytest
```

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for deployment instructions.
EOF

# Create .gitignore
echo "📝 Creating .gitignore..."
cat > .gitignore <<'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Environment
.env
.env.local
.venv
venv/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Supabase
.branches/
.temp/

# Node (for web dashboard)
node_modules/
.next/
out/
EOF

# Create .env.example
echo "📝 Creating .env.example..."
cat > .env.example <<'EOF'
# Supabase Configuration
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# Next.js (Web Dashboard)
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
EOF

# Create sync script
echo "📝 Creating schema sync script..."
cat > scripts/sync_schema.sh <<'SYNCEOF'
#!/bin/bash
#
# Sync schema from kurt-core to kurt-cloud
#
# This generates a new migration file from kurt-core models.

set -e

KURT_CORE_DIR="${1:-../kurt-core}"
TIMESTAMP=$(date +%Y%m%d%H%M%S)
MIGRATION_FILE="supabase/migrations/${TIMESTAMP}_schema_update.sql"

echo "🔄 Syncing schema from kurt-core..."
echo "   Source: $KURT_CORE_DIR/src/kurt/db/models.py"
echo "   Target: $MIGRATION_FILE"
echo ""

# Generate schema SQL
cd "$KURT_CORE_DIR"
uv run python scripts/generate_postgres_schema.py > "../kurt-cloud/$MIGRATION_FILE"

echo "✓ Schema migration created: $MIGRATION_FILE"
echo ""
echo "Next steps:"
echo "  1. Review the migration file"
echo "  2. Apply with: supabase db push"
SYNCEOF

chmod +x scripts/sync_schema.sh

# Initialize Supabase
echo "🔧 Initializing Supabase..."
if [ ! -f "supabase/config.toml" ]; then
    supabase init 2>/dev/null || echo "⚠️  Supabase CLI not installed. Run: brew install supabase/tap/supabase"
fi

# Generate initial migration
if [ ! "$(ls -A supabase/migrations 2>/dev/null)" ]; then
    echo "📦 Generating initial schema migration..."
    cd "$KURT_CORE_DIR"
    TIMESTAMP=$(date +%Y%m%d%H%M%S)
    uv run python scripts/generate_postgres_schema.py \
      > "$KURT_CLOUD_DIR/supabase/migrations/${TIMESTAMP}_init_schema.sql" 2>/dev/null \
      || echo "⚠️  Could not generate schema. Run manually: ./scripts/sync_schema.sh"
fi

# Create initial RLS migration
if [ ! -f "supabase/migrations/"*"_rls_policies.sql" ]; then
    echo "🔒 Creating RLS policies migration..."
    TIMESTAMP=$(date +%Y%m%d%H%M%S)_
    cat > "supabase/migrations/${TIMESTAMP}rls_policies.sql" <<'RLSEOF'
-- Row-Level Security Policies for Kurt Cloud
--
-- This migration sets up workspace isolation using RLS.
-- Users can only access data in their workspace.

-- Helper function to get workspace_id from JWT
CREATE OR REPLACE FUNCTION auth.workspace_id()
RETURNS uuid AS $$
  SELECT COALESCE(
    (auth.jwt() ->> 'workspace_id')::uuid,
    '00000000-0000-0000-0000-000000000000'::uuid
  );
$$ LANGUAGE SQL STABLE;

-- Documents: workspace isolation
CREATE POLICY workspace_isolation_documents ON documents
  FOR ALL
  USING (tenant_id = auth.workspace_id());

-- Entities: workspace isolation
CREATE POLICY workspace_isolation_entities ON entities
  FOR ALL
  USING (tenant_id = auth.workspace_id());

-- Document Entities: workspace isolation via document
CREATE POLICY workspace_isolation_document_entities ON document_entities
  FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM documents
      WHERE documents.id = document_entities.document_id
      AND documents.tenant_id = auth.workspace_id()
    )
  );

-- Entity Relationships: workspace isolation via entity
CREATE POLICY workspace_isolation_entity_relationships ON entity_relationships
  FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM entities
      WHERE entities.id = entity_relationships.source_entity_id
      AND entities.tenant_id = auth.workspace_id()
    )
  );

-- Grant authenticated users access
GRANT ALL ON documents TO authenticated;
GRANT ALL ON entities TO authenticated;
GRANT ALL ON document_entities TO authenticated;
GRANT ALL ON entity_relationships TO authenticated;
RLSEOF
fi

echo ""
echo "✅ kurt-cloud setup complete!"
echo ""
echo "Next steps:"
echo "  1. cd $KURT_CLOUD_DIR"
echo "  2. supabase login"
echo "  3. supabase link --project-ref YOUR-PROJECT-ID"
echo "  4. supabase db push"
echo ""
echo "See README.md for more details."
