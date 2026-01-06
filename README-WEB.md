# Kurt Web UI

A web-based IDE interface for Kurt, featuring a rich text editor powered by Tiptap and a FastAPI backend.

## Overview

This module provides the web UI implementation for Kurt:

-   **Rich Text Editor**: Tiptap-based editor with formatting capabilities
-   **File Browser**: Navigate and manage files in your project
-   **FastAPI Backend**: RESTful API for file operations + WebSocket PTY for terminal
-   **Storage Abstraction**: Support for both local filesystem and S3 storage

## Architecture

### Backend (Python/FastAPI)

-   **Location**: `src/kurt/web/api/`
-   **Main Files**:
    -   `server.py` - FastAPI application with CORS-enabled endpoints + static file serving
    -   `pty_bridge.py` - WebSocket PTY bridge for terminal sessions
    -   `storage.py` - Storage abstraction layer

#### API Endpoints

-   `GET /api/tree?path=.` - List directory contents
-   `GET /api/file?path=<filepath>` - Read file contents
-   `PUT /api/file?path=<filepath>` - Write/update file contents
-   `DELETE /api/file?path=<filepath>` - Delete file
-   `POST /api/file/rename` - Rename file
-   `POST /api/file/move` - Move file
-   `GET /api/git/diff?path=<filepath>` - Get git diff for file
-   `GET /api/git/status` - Get git status
-   `GET /api/search?q=<query>` - Search files
-   `POST /api/approval/request` - Create approval request
-   `GET /api/approval/pending` - Get pending approvals
-   `POST /api/approval/decision` - Approve/deny request
-   `WebSocket /ws/pty` - Terminal PTY session

### Frontend (React/Vite/Tiptap)

-   **Location**: `src/kurt/web/client/`
-   **Key Components**:
    -   `FileTree.jsx` - File browser component
    -   `Editor.jsx` - Tiptap rich text editor
    -   `Terminal.jsx` - xterm.js terminal
    -   `App.jsx` - Main application layout with dockview panels

## Installation & Setup

### 1. Install Python Dependencies

```bash
# Using uv (recommended)
uv pip install -e ".[web]"

# Or using pip
pip install -e ".[web]"
```

### 2. Production Mode (Recommended)

Run the pre-built frontend via FastAPI:

```bash
kurt serve
```

This will:
-   Start FastAPI on port 8765
-   Serve the pre-built frontend static files
-   Open browser to http://127.0.0.1:8765

Options:
```bash
kurt serve --host 0.0.0.0 --port 8000  # Custom host/port
kurt serve --no-browser                 # Don't open browser
kurt serve --reload                     # Enable auto-reload
```

### 3. Development Mode

For frontend development with hot reload, run servers separately:

**Terminal 1 - Backend:**
```bash
uvicorn kurt.web.api.server:app --reload --port 8765
```

**Terminal 2 - Frontend:**
```bash
cd src/kurt/web/client
npm install  # First time only
npm run dev
```

Then open http://127.0.0.1:5173

## Configuration

### Ports

-   **Production**: Single port (default 8765) serves both API and frontend
-   **Development**: API on 8765, Vite dev server on 5173

### Storage Mode

```bash
# Local filesystem (default)
unset KURT_STORAGE

# S3 backend
export KURT_STORAGE=s3
export KURT_S3_BUCKET=my-bucket
export KURT_S3_PREFIX=projects/kurt/  # optional
```

### Claude PreToolUse Hook (edit approval)

To intercept Claude edits and show approvals in the web UI, enable the hook:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ./scripts/claude_pretool_hook.py"
          }
        ]
      }
    ]
  }
}
```

## Project Structure

```
src/kurt/
├── web/
│   ├── api/
│   │   ├── server.py       # FastAPI + static file serving
│   │   ├── pty_bridge.py   # WebSocket PTY handler
│   │   └── storage.py      # Storage abstraction
│   └── client/
│       ├── src/
│       │   ├── components/ # React components
│       │   ├── panels/     # Dockview panels
│       │   ├── App.jsx     # Main layout
│       │   └── main.jsx    # Entry point
│       ├── dist/           # Built frontend (included in package)
│       ├── package.json
│       └── vite.config.ts
├── commands/
│   └── web.py              # `kurt serve` command
```

## Building the Package

The frontend is automatically built when creating a wheel:

```bash
pip install build
python -m build --wheel
```

The hatch build hook (`hatch_build.py`) runs `npm install && npm run build` automatically.

## Security Considerations

This server is for local development:

-   No authentication or authorization
-   Binds to localhost only (127.0.0.1) by default
-   File access limited to project root
-   Do NOT expose to public networks

## Troubleshooting

### Backend won't start

**Error**: `No module named uvicorn`

**Solution**: Install web dependencies:
```bash
uv pip install -e ".[web]"
```

### CORS errors in browser console

**Solution**: In dev mode, ensure:
1. Frontend runs on http://localhost:5173
2. Backend runs on http://127.0.0.1:8765

### File operations fail

**Error**: "Path outside of project root"

**Solution**: LocalStorage validates all paths for security. Ensure you're not accessing files outside the project directory.

## References

-   **FastAPI**: https://fastapi.tiangolo.com/
-   **Tiptap**: https://tiptap.dev/
-   **Vite**: https://vite.dev/
-   **xterm.js**: https://xtermjs.org/
-   **dockview**: https://dockview.dev/
