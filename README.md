# Antigravity CLI Chat Viewer

A viewer for Antigravity chat logs. 

##  Features

- Markdown Support: Full rendering of Markdown, including tables, lists, and formatted text.
- Code Highlighting: Beautifully formatted code blocks for developer-centric logs.
- Artifact Integration: Seamlessly browse and view "Brain" artifacts associated with your chats.
- Tool Call Visibility: Clear visualization of agent "Planning Actions" and tool executions.
- Unified Distribution: Serves the modern frontend directly from the Python process.

## Tech Stack

- Backend: Python 3.12+, aiohttp, aiosqlite, Protobuf
- Frontend: Next.js 15, TypeScript, Tailwind CSS 4, Lucide Icons, React Markdown

## Getting Started

### Prerequisites

- [uv](https://github.com/astral-sh/uv) (recommended for Python dependency management)
- Node.js & npm (for frontend development/building)

### Installation

1. Clone the repository and install Python dependencies:
   ```bash
   uv sync
   ```

2. (Optional) Install frontend dependencies if you plan to modify the UI:
   ```bash
   cd frontend
   npm install
   ```

## Running the Application

### Production Mode (Simplest)

If you just want to use the app, ensure the frontend is built, then run the backend:

1. Build the frontend (if not already built):
   ```bash
   cd frontend
   npm run build
   cd ..
   ```

2. Start the server:
   ```bash
   python main.py
   ```
   Visit `http://localhost:7396` in your browser.

### Development Mode

For active development, run both the backend and frontend separately for hot-reloading:

1. Start the Backend API:
   ```bash
   python main.py
   ```

2. Start the Frontend Dev Server:
   ```bash
   cd frontend
   npm run dev
   ```
   Visit `http://localhost:3000`.

## Packaging

To create a static export of the frontend that the Python backend can serve:
```bash
cd frontend
npm run build
```
This generates the `frontend/out` directory, which `main.py` automatically detects and serves.

## Configuration

`main.py` supports several CLI arguments:

- `--db-dir`: Directory where your `.db` conversation files are located (Default: `~/.gemini/antigravity-cli/conversations`).
- `--brain-dir`: Directory for brain artifacts (Default: `~/.gemini/antigravity-cli/brain`).
- `--port`: Port to run the server on (Default: `7396`).
- `--host`: Host to bind the server to (Default: `localhost`).

Example:
```bash
python main.py --db-dir ./my_logs --port 8080
```