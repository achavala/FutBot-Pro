#!/bin/bash

echo "🛑 Killing all processes on port 8000..."

# Kill processes on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null

# Kill all uvicorn processes
pkill -9 -f "uvicorn" 2>/dev/null

# Kill all Python FastAPI processes
pkill -9 -f "python.*fastapi" 2>/dev/null
pkill -9 -f "python.*main.py" 2>/dev/null
pkill -9 -f "python.*ui/fastapi_app" 2>/dev/null

# Wait for processes to die
sleep 3

# Verify port is free
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "❌ Port 8000 is still in use!"
    echo "Processes using port 8000:"
    lsof -ti:8000 | xargs ps -p
    exit 1
else
    echo "✅ Port 8000 is now FREE"
fi

# Now start the server
echo "🚀 Starting server..."
cd "$(dirname "$0")"
source .venv/bin/activate
python3 -m uvicorn ui.fastapi_app:app --host 0.0.0.0 --port 8000 --reload

