#!/bin/bash
# Restart server with Gamma-only mode

echo "============================================================"
echo "RESTARTING SERVER WITH GAMMA-ONLY MODE"
echo "============================================================"
echo ""

# Find and kill existing server
echo "🔍 Finding existing server process..."
PID=$(ps aux | grep "python.*main.py.*--mode api" | grep -v grep | awk '{print $2}' | head -1)

if [ -n "$PID" ]; then
    echo "🛑 Stopping server (PID: $PID)..."
    kill $PID 2>/dev/null
    sleep 2
    
    # Force kill if still running
    if ps -p $PID > /dev/null 2>&1; then
        echo "⚠️  Process still running, force killing..."
        kill -9 $PID 2>/dev/null
        sleep 1
    fi
    echo "✅ Server stopped"
else
    echo "ℹ️  No server process found"
fi

# Check if port 8000 is free
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 8000 still in use, killing process..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    sleep 1
fi

echo ""
echo "🚀 Starting server with GAMMA_ONLY_TEST_MODE=true..."
echo ""
echo "Watch for these startup messages:"
echo "  - 🔬 GAMMA_ONLY_TEST_MODE=true (env var: true)"
echo "  - ✅ Created X agents (Gamma Scalper only)"
echo ""

# Start server with Gamma-only mode
GAMMA_ONLY_TEST_MODE=true ./START_VALIDATION.sh

