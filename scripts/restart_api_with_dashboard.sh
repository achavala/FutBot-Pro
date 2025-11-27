#!/bin/bash

# Script to restart the API server and verify dashboard is working

echo "=== Restarting FutBot API Server ==="
echo ""

# Source the virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️  Warning: .venv not found, using system Python"
fi

# Define the FastAPI app command
APP_COMMAND="python main.py --mode api --port 8000"
LOG_FILE="logs/api_server.log"

# 1. Stop existing server
echo ""
echo "1. Stopping existing server..."
PID=$(ps aux | grep "$APP_COMMAND" | grep -v grep | awk '{print $2}')

if [ -n "$PID" ]; then
    echo "   Found server process: $PID"
    kill "$PID"
    # Wait for the process to terminate
    for i in {1..10}; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            echo "   ✅ Server stopped"
            break
        fi
        sleep 0.5
    done
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "   ⚠️  Server did not stop gracefully, forcing kill..."
        kill -9 "$PID"
        sleep 1
    fi
else
    echo "   No existing server process found."
fi

# 2. Start new server
echo ""
echo "2. Starting new server..."
# Ensure logs directory exists
mkdir -p logs
# Start the server in the background, redirecting output to a log file
nohup $APP_COMMAND > "$LOG_FILE" 2>&1 &
NEW_PID=$!
echo "   Starting server on port 8000..."
sleep 5 # Give server time to start

# Check if the new server process is running
if ps -p "$NEW_PID" > /dev/null 2>&1; then
    echo "   ✅ Server started (PID: $NEW_PID)"
else
    echo "   ❌ Failed to start server. Check $LOG_FILE for errors."
    exit 1
fi

# 3. Verify server is responsive
echo ""
echo "3. Verifying server..."
sleep 2
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✅ Server is responding!"
else
    echo "   ⚠️  Server may not be fully ready yet. Check $LOG_FILE for errors."
fi

# 4. Test dashboard endpoint
echo ""
echo "4. Testing dashboard endpoint..."
sleep 2
CONTENT_TYPE=$(curl -s -I http://localhost:8000/ 2>/dev/null | grep -i "content-type" | cut -d' ' -f2 | tr -d '\r')
if [ -n "$CONTENT_TYPE" ]; then
    if echo "$CONTENT_TYPE" | grep -q "text/html"; then
        echo "   ✅ Dashboard is serving HTML correctly!"
    else
        echo "   ⚠️  Dashboard Content-Type: $CONTENT_TYPE (expected text/html)"
        echo "   Try accessing http://localhost:8000 in your browser"
    fi
else
    echo "   ⚠️  Could not verify dashboard. Try accessing http://localhost:8000 in your browser"
fi

echo ""
echo "=== Server Restarted Successfully ==="
echo ""
echo "Server PID: $NEW_PID"
echo "Logs: $LOG_FILE"
echo "Dashboard: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "To stop server: kill $NEW_PID"
echo ""

