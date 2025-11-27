#!/bin/bash
# Restart the FutBot API server

echo "=== Restarting FutBot API Server ==="
echo ""

# Find and kill existing server
echo "1. Stopping existing server..."
SERVER_PID=$(ps aux | grep -i "python.*main.py.*api\|uvicorn.*fastapi_app" | grep -v grep | awk '{print $2}' | head -1)

if [ -n "$SERVER_PID" ]; then
    echo "   Found server process: $SERVER_PID"
    kill $SERVER_PID 2>/dev/null
    sleep 2
    
    # Force kill if still running
    if ps -p $SERVER_PID > /dev/null 2>&1; then
        echo "   Force killing..."
        kill -9 $SERVER_PID 2>/dev/null
    fi
    echo "   ✅ Server stopped"
else
    echo "   No running server found"
fi

echo ""
echo "2. Starting new server..."

# Activate virtual environment and start server
cd "$(dirname "$0")/.." || exit 1

if [ ! -d ".venv" ]; then
    echo "   ❌ Virtual environment not found!"
    echo "   Run: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

source .venv/bin/activate

# Start server in background
echo "   Starting server on port 8000..."
nohup python main.py --mode api --port 8000 > logs/api_server.log 2>&1 &
NEW_PID=$!

sleep 3

# Check if server started successfully
if ps -p $NEW_PID > /dev/null 2>&1; then
    echo "   ✅ Server started (PID: $NEW_PID)"
    echo ""
    echo "3. Verifying server..."
    sleep 2
    
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "   ✅ Server is responding!"
        echo ""
        echo "=== Server Restarted Successfully ==="
        echo ""
        echo "Server PID: $NEW_PID"
        echo "Logs: logs/api_server.log"
        echo "Health: http://localhost:8000/health"
        echo "API Docs: http://localhost:8000/docs"
        echo ""
        echo "To stop server: kill $NEW_PID"
    else
        echo "   ⚠️  Server started but not responding yet"
        echo "   Check logs: tail -f logs/api_server.log"
    fi
else
    echo "   ❌ Failed to start server"
    echo "   Check logs: tail -f logs/api_server.log"
    exit 1
fi

