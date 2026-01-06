# Kurt Web UI

Kurt in your browser. Edit, browse, execute—fully synced with your local filesystem.

## Features

- **File Explorer** — Navigate your project at a glance
- **Rich Editor** — Syntax-highlighted editing powered by Tiptap
- **Integrated Terminal** — Run commands without leaving the browser
- **Live Sync** — Real-time two-way sync via WebSocket

## Quickstart

1. Install Node dependencies

```bash
cd web
npm install
```

2. Install Python dependencies for the API (in your Python venv)

```bash
pip install -r ../requirements-web.txt
```

3. Start the server from the repo root:

```bash
kurt serve
```

This will start:
- FastAPI backend at `http://127.0.0.1:8765`
- Claude CLI bridge at `ws://127.0.0.1:8767`
- Vite dev server at `http://127.0.0.1:5173`
