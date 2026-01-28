# Project Context

## Purpose
Kurt Cloud is a managed service extending kurt-core with authentication, multi-tenant workspaces, and team collaboration. Currently uses Supabase for auth and database.

## Tech Stack
- **Language**: Python 3.11+
- **Package Manager**: uv
- **Web Framework**: FastAPI
- **Database**: PostgreSQL (currently Supabase, migrating to Neon)
- **Auth**: Supabase Auth (migrating to Neon Auth)
- **ORM**: SQLAlchemy
- **Migrations**: Alembic
- **Deployment**: Vercel

## Architecture
- `src/api/` - FastAPI routes and middleware
- `src/db/` - Database models and migrations
- `src/workspaces/` - Workspace service layer
- `src/cli/` - CLI commands

## Multi-Tenancy Model
- Hybrid isolation: RLS on shared tables + per-workspace schemas
- Each workspace gets: `ws_<id>` schema, `ws_<id>_dbos` user
- DBOS tables live in workspace schema (no native multi-tenancy)

## External Dependencies
- **kurt-core**: Workflow engine (mounted at `/core`)
- **Supabase**: Auth + Database (being replaced)
- **Neon**: Target database with scale-to-zero + JWT auth
