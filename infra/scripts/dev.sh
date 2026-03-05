#!/bin/bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

echo "Starting AVCE development servers..."

# Start FastAPI backend
echo "Starting API server on :8000..."
cd "$ROOT_DIR/apps/api"
source .venv/bin/activate 2>/dev/null || python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
API_PID=$!

# Start Next.js frontend
echo "Starting Web server on :3000..."
cd "$ROOT_DIR/apps/web"
npm run dev &
WEB_PID=$!

# Trap to kill both on exit
trap "kill $API_PID $WEB_PID 2>/dev/null; exit" SIGINT SIGTERM EXIT

echo ""
echo "API:  http://localhost:8000"
echo "Web:  http://localhost:3000"
echo "Health: http://localhost:3000/api/health"
echo ""
echo "Press Ctrl+C to stop both servers."

wait
