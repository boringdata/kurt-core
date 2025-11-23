# Kurt Web UI

A web-based IDE interface for Kurt, featuring a rich text editor powered by Tiptap and a FastAPI backend.

## Overview

This worktree (`kurt-core-web`) contains the web UI implementation for Kurt, providing:

- **Rich Text Editor**: Tiptap-based editor with formatting capabilities
- **File Browser**: Navigate and manage files in your project
- **FastAPI Backend**: RESTful API for file operations
- **Storage Abstraction**: Support for both local filesystem and S3 storage

## Architecture

### Backend (Python/FastAPI)

- **Location**: `src/kurt/web_api/`
- **Main Files**:
  - `server.py` - FastAPI application with CORS-enabled endpoints
  - `src/kurt/storage.py` - Storage abstraction layer

#### API Endpoints

- `GET /api/tree?path=.` - List directory contents
- `GET /api/file?path=<filepath>` - Read file contents
- `PUT /api/file?path=<filepath>` - Write/update file contents (JSON body: `{"content": "..."}`)

#### Storage Backends

**LocalStorage** (default):
- Reads/writes files from project root
- Path validation prevents escaping project directory
- No additional configuration needed

**S3Storage** (optional):
- Requires `s3fs` package (included in `requirements-web.txt`)
- Configuration via environment variables:
  ```bash
  export KURT_STORAGE=s3
  export KURT_S3_BUCKET=your-bucket-name
  export KURT_S3_PREFIX=optional/prefix/  # optional
  ```

### Frontend (React/Vite/Tiptap)

- **Location**: `web/`
- **Key Components**:
  - `FileTree.jsx` - File browser component
  - `Editor.jsx` - Tiptap rich text editor
  - `App.jsx` - Main application layout

#### Features

- Rich text editing with Tiptap (bold, italic, headings, lists, etc.)
- File tree navigation (top-level only - nested expansion not yet implemented)
- Auto-save on file changes
- Responsive layout

## Installation & Setup

### 1. Install Python Dependencies

From the worktree root:

```bash
cd /Users/julien/Documents/wik/wikumeo/projects/kurt-core-web
uv pip install -r requirements-web.txt
```

Or using pip:

```bash
pip install -r requirements-web.txt
```

### 2. Install Frontend Dependencies

```bash
cd web
npm install
```

### 3. Start the Servers

#### Option A: Manual Start (Recommended for Development)

**Terminal 1 - Backend:**
```bash
cd /Users/julien/Documents/wik/wikumeo/projects/kurt-core-web
KURT_TELEMETRY_DISABLED=1 python -m uvicorn kurt.web_api.server:app --host 127.0.0.1 --port 8765 --reload
```

**Terminal 2 - Frontend:**
```bash
cd /Users/julien/Documents/wik/wikumeo/projects/kurt-core-web/web
npm run dev
```

#### Option B: Using `kurt serve` (TODO)

The integrated CLI command is planned but not yet implemented:

```bash
# Future:
kurt serve [--no-browser]
```

This would automatically:
- Start the FastAPI backend on port 8765
- Start the Vite dev server on port 5173
- Open the browser to http://localhost:5173

### 4. Access the UI

Open your browser to: http://localhost:5173

## Configuration

### Ports

- **Frontend (Vite)**: 5173
- **Backend (FastAPI)**: 8765

To change ports, update:
- Frontend: `web/vite.config.ts`
- Backend: uvicorn command arguments
- CORS: `src/kurt/web_api/server.py` (allow_origins)

### Storage Mode

```bash
# Local filesystem (default)
unset KURT_STORAGE

# S3 backend
export KURT_STORAGE=s3
export KURT_S3_BUCKET=my-bucket
export KURT_S3_PREFIX=projects/kurt/  # optional
```

## Current Limitations

### Known Gaps

1. **File Tree**: Only shows top-level directory entries. No nested expand/collapse yet.
2. **No Authentication**: API endpoints are not protected. Do NOT expose this server to untrusted networks.
3. **Save Behavior**: Simple overwrite - no autosave, conflict detection, or version history.
4. **No File Operations**: Cannot create/delete/rename files from the UI yet.
5. **Error Handling**: Basic error handling - needs improvement for better UX.
6. **Frontend Dependencies**: npm install may show 2 moderate severity vulnerabilities (need audit).

### Not Yet Implemented

- `kurt serve` CLI command (needs to be added to `src/kurt/cli.py`)
- Nested directory navigation
- File create/delete/rename operations
- File history/versioning
- Multi-user collaboration
- Search functionality
- Syntax highlighting (code files)
- Preview mode (markdown, etc.)
- Settings/preferences UI

## Development

### Project Structure

```
kurt-core-web/
├── src/kurt/
│   ├── web_api/
│   │   └── server.py          # FastAPI application
│   └── storage.py              # Storage abstraction
├── web/
│   ├── src/
│   │   ├── components/
│   │   │   ├── FileTree.jsx   # File browser
│   │   │   └── Editor.jsx     # Tiptap editor
│   │   ├── App.jsx            # Main layout
│   │   └── main.jsx           # Entry point
│   ├── package.json
│   ├── vite.config.ts
│   └── index.html
├── requirements-web.txt        # Python dependencies
└── README-WEB.md              # This file
```

### Adding Features

**Backend (Python)**:
1. Add new endpoints to `src/kurt/web_api/server.py`
2. Extend Storage interface in `src/kurt/storage.py` if needed
3. Update CORS settings if frontend origin changes

**Frontend (React)**:
1. Add components in `web/src/components/`
2. Update `App.jsx` for layout changes
3. Install new npm packages as needed

### Testing with Playwright

Playwright tests can be added to verify:
- File tree loading
- File open/read operations
- File save/update operations
- Editor functionality

```bash
# Install Playwright (example)
cd web
npm install -D @playwright/test
npx playwright install

# Run tests (when implemented)
npx playwright test
```

## Troubleshooting

### Backend won't start

**Error**: `No module named uvicorn`

**Solution**: Ensure you've installed the web requirements in your Python environment:
```bash
uv pip install -r requirements-web.txt
# or
pip install -r requirements-web.txt
```

### CORS errors in browser console

**Symptom**: API calls fail with CORS policy errors

**Solution**: Check that:
1. Frontend is running on http://localhost:5173 (or update CORS origins in `server.py`)
2. Backend is running on http://127.0.0.1:8765

### File operations fail

**Error**: "Path outside of project root" or "Invalid path"

**Solution**: LocalStorage validates all paths are within the project root for security. Ensure you're not trying to access files outside the project directory.

## Git Workflow

This is a git worktree on branch `feat/web-ui`. Changes are isolated from the main development branch.

```bash
# View worktrees
git worktree list

# Commit changes (in this worktree)
cd /Users/julien/Documents/wik/wikumeo/projects/kurt-core-web
git add .
git commit -m "feat(web): your changes"

# Push to remote
git push origin feat/web-ui

# Create PR (when ready)
gh pr create --title "feat: Add web-based IDE" --base main --head feat/web-ui
```

## Security Considerations

This is a development server and is NOT production-ready:

- No authentication or authorization
- Binds to localhost only (127.0.0.1)
- File access limited to project root
- CORS restricted to localhost:5173

Do NOT expose this server to:
- Public networks
- Untrusted users
- Production environments

## Future Enhancements

Planned improvements:

1. **CLI Integration**: Add `kurt serve` command to `cli.py`
2. **Nested Navigation**: Expand/collapse directories in file tree
3. **File Operations**: Create, delete, rename, move files
4. **Version History**: Track file changes before overwriting
5. **Search**: Full-text search across files
6. **Syntax Highlighting**: Code editor with language support
7. **Preview Mode**: Render markdown, images, etc.
8. **Authentication**: Basic auth or token-based access control
9. **Real-time Collaboration**: Multi-user editing with CRDT
10. **AI Integration**: Kurt's knowledge graph queries from UI

## References

- **FastAPI**: https://fastapi.tiangolo.com/
- **Tiptap**: https://tiptap.dev/
- **Vite**: https://vite.dev/
- **s3fs**: https://s3fs.readthedocs.io/

## Status

- **Branch**: `feat/web-ui`
- **Worktree**: `/Users/julien/Documents/wik/wikumeo/projects/kurt-core-web`
- **Last Updated**: 2025-11-23
- **Status**: Work in progress - basic functionality implemented, testing and features pending
