#!/bin/bash
# Start FastAPI server script

set -e

cd "$(dirname "$0")/.."

echo "=============================================="
echo "FastAPI Server"
echo "======================"
echo ""

# Check if server is already running
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Server is already running at http://localhost:8000"
    echo ""
    echo "API Docs: http://localhost:8000/docs"
    echo "Health: http://localhost:8000/health"
    exit 0
fi

# Check if uvicorn is available
if ! python3 -m uvicorn --help > /dev/null 2>&1; then
    echo "❌ uvicorn not found. Installing..."
    pip install uvicorn[standard]
fi

echo "Starting FastAPI server..."
echo "Server will be available at: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start server
python3 -m uvicorn ui.fastapi_app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload

