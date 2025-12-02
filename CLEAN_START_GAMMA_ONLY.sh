#!/bin/bash
# Clean start with Gamma-only mode

echo "============================================================"
echo "CLEAN START - GAMMA-ONLY MODE"
echo "============================================================"
echo ""

# Step 1: Kill all Python processes
echo "🧹 Step 1: Cleaning up all processes..."
pkill -f "python.*main.py" 2>/dev/null
pkill -f "python.*uvicorn" 2>/dev/null
pkill -f "uvicorn" 2>/dev/null
sleep 2

# Force kill if still running
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 8000 still in use, force killing..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    sleep 1
fi

# Verify cleanup
if ps aux | grep -E "python.*main.py|python.*uvicorn" | grep -v grep > /dev/null; then
    echo "⚠️  Some processes still running, force killing..."
    killall -9 python 2>/dev/null
    sleep 1
fi

echo "✅ Cleanup complete"
echo ""

# Step 2: Set environment variables
echo "🔧 Step 2: Setting environment variables..."
export GAMMA_ONLY_TEST_MODE=true
export FUTBOT_LOG_LEVEL=INFO

echo "✅ Environment variables set:"
echo "   GAMMA_ONLY_TEST_MODE=$GAMMA_ONLY_TEST_MODE"
echo "   FUTBOT_LOG_LEVEL=$FUTBOT_LOG_LEVEL"
echo ""

# Step 3: Verify port is free
echo "🔍 Step 3: Verifying port 8000 is free..."
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "❌ Port 8000 still in use!"
    echo "   Run: lsof -i :8000"
    exit 1
else
    echo "✅ Port 8000 is free"
fi
echo ""

# Step 4: Start server in background
echo "🚀 Step 4: Starting server with Gamma-only mode (background)..."
echo ""

# Create logs directory if it doesn't exist
mkdir -p logs

# Start server in background
nohup python3 main.py --mode api --port 8000 > logs/gamma_only_server.log 2>&1 &
SERVER_PID=$!

# Wait a moment for server to start
sleep 3

# Check if server started successfully
if ps -p $SERVER_PID > /dev/null 2>&1; then
    echo "✅ Server started successfully (PID: $SERVER_PID)"
    echo ""
    echo "📊 Server Status:"
    curl -s http://localhost:8000/health | python3 -m json.tool | grep -E "status|is_running" | head -2 || echo "  Server starting..."
    echo ""
    echo "📍 Dashboard: http://localhost:8000/dashboard"
    echo "📜 Logs: tail -f logs/gamma_only_server.log"
    echo ""
    echo "Watch for these startup messages:"
    echo "  - 🔬 GAMMA_ONLY_TEST_MODE=true (env var: true)"
    echo "  - ✅ Created X agents (Gamma Scalper only)"
    echo ""
    echo "To verify Gamma-only mode:"
    echo "  ./VERIFY_GAMMA_MODE.sh"
    echo ""
    echo "To start trading loop:"
    echo "  ./START_TRADING_LOOP.sh"
    echo ""
    echo "============================================================"
else
    echo "❌ Server failed to start"
    echo "Check logs: tail -20 logs/gamma_only_server.log"
    exit 1
fi

