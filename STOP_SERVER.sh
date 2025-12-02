#!/bin/bash
# Stop FutBot server

echo "============================================================"
echo "STOPPING FUTBOT SERVER"
echo "============================================================"
echo ""

# Find server processes
PIDS=$(ps aux | grep "python.*main.py.*--mode api" | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo "ℹ️  No server process found"
else
    echo "🛑 Stopping server processes..."
    for PID in $PIDS; do
        echo "   Killing PID: $PID"
        kill $PID 2>/dev/null
    done
    
    sleep 2
    
    # Force kill if still running
    for PID in $PIDS; do
        if ps -p $PID > /dev/null 2>&1; then
            echo "   Force killing PID: $PID"
            kill -9 $PID 2>/dev/null
        fi
    done
    
    echo "✅ Server stopped"
fi

# Free port 8000
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "🧹 Freeing port 8000..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    echo "✅ Port 8000 freed"
fi

echo ""
echo "✅ Cleanup complete"
echo ""

