#!/bin/bash
# Start FutBot in Gamma-only mode (background)

echo "============================================================"
echo "STARTING FUTBOT - GAMMA-ONLY MODE"
echo "============================================================"
echo ""

# Kill old processes
echo "🔪 Killing old processes..."
pkill -f "python.*main.py" 2>/dev/null || true
pkill -f "python.*uvicorn" 2>/dev/null || true
sleep 2

# Free port 8000
echo "🧹 Freeing port 8000..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
sleep 1

# Verify port is free
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 8000 still in use, force killing..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

echo "✅ Cleanup complete"
echo ""

# Set environment variables
export GAMMA_ONLY_TEST_MODE=true
export FUTBOT_LOG_LEVEL=INFO

echo "🔧 Environment variables set:"
echo "   GAMMA_ONLY_TEST_MODE=$GAMMA_ONLY_TEST_MODE"
echo "   FUTBOT_LOG_LEVEL=$FUTBOT_LOG_LEVEL"
echo ""

# Check for required dependencies
echo "🔍 Checking dependencies..."
if ! python3 -c "import uvicorn" 2>/dev/null; then
    echo "⚠️  uvicorn not found. Installing dependencies..."
    pip3 install uvicorn fastapi websockets python-dotenv > /dev/null 2>&1
    if ! python3 -c "import uvicorn" 2>/dev/null; then
        echo "❌ Failed to install uvicorn"
        echo "   Run manually: pip3 install uvicorn fastapi"
        exit 1
    fi
    echo "✅ Dependencies installed"
fi

# Create logs directory
mkdir -p logs

# Start server in background with environment variables explicitly passed
echo "🚀 Starting server in background with GAMMA_ONLY_TEST_MODE=true..."
nohup env GAMMA_ONLY_TEST_MODE=true FUTBOT_LOG_LEVEL=INFO python3 main.py --mode api --port 8000 > logs/gamma_only_server.log 2>&1 &
SERVER_PID=$!

# Wait for server to start
echo "⏳ Waiting for server to start..."
sleep 5

# Check if server is running
if ps -p $SERVER_PID > /dev/null 2>&1; then
    echo "✅ Server started successfully (PID: $SERVER_PID)"
    echo ""
    
    # Check health
    echo "📊 Checking server health..."
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Server is responding"
        curl -s http://localhost:8000/health | python3 -m json.tool | grep -E "status|is_running" | head -2
    else
        echo "⚠️  Server not responding yet (may still be starting)"
    fi
    
    echo ""
    echo "📍 Dashboard: http://localhost:8000/dashboard"
    echo "📜 Logs: tail -f logs/gamma_only_server.log"
    echo ""
    echo "Watch for Gamma-only mode indicators:"
    echo "  tail -f logs/gamma_only_server.log | grep -i 'GAMMA_ONLY\|Gamma Scalper only'"
    echo ""
    echo "Next steps:"
    echo "  1. Verify mode: ./VERIFY_GAMMA_MODE.sh"
    echo "  2. Start trading: ./START_TRADING_LOOP.sh"
    echo "  3. Monitor: ./CHECK_GAMMA_ACTIVITY.sh"
    echo ""
    echo "============================================================"
else
    echo "❌ Server failed to start"
    echo ""
    echo "Check logs:"
    echo "  tail -50 logs/gamma_only_server.log"
    exit 1
fi

