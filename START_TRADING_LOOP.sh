#!/bin/bash
# Start trading loop via API

echo "============================================================"
echo "STARTING TRADING LOOP"
echo "============================================================"
echo ""

# Check if server is running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ Server not running"
    echo "   Start it first: ./CLEAN_START_GAMMA_ONLY.sh"
    exit 1
fi

echo "✅ Server is running"
echo ""

# Check if trading loop is already running
IS_RUNNING=$(curl -s http://localhost:8000/health | python3 -c "import sys, json; print(json.load(sys.stdin).get('is_running', False))" 2>/dev/null || echo "false")

if [ "$IS_RUNNING" = "true" ]; then
    echo "ℹ️  Trading loop is already running"
    echo ""
    echo "Check status:"
    curl -s http://localhost:8000/health | python3 -m json.tool | grep -E "is_running|bar_count" | head -3
    exit 0
fi

echo "🚀 Starting trading loop..."
echo ""

# Try /live/start endpoint
RESPONSE=$(curl -s -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["SPY"], "offline_mode": true}' 2>&1)

if echo "$RESPONSE" | python3 -c "import sys, json; json.load(sys.stdin)" 2>/dev/null; then
    echo "✅ Trading loop started successfully"
    echo ""
    echo "$RESPONSE" | python3 -m json.tool
else
    echo "⚠️  API call may have failed or returned non-JSON"
    echo ""
    echo "Response:"
    echo "$RESPONSE"
    echo ""
    echo "💡 Alternative: Use dashboard"
    echo "   Open: http://localhost:8000/dashboard"
    echo "   Click: 'Start Live' or 'Simulate'"
fi

echo ""
echo "📊 Monitor activity:"
echo "   ./CHECK_GAMMA_ACTIVITY.sh"
echo ""
echo "📝 Watch logs:"
echo "   tail -f logs/*.log | grep -i 'gamma\|deltahedge\|multileg'"
echo ""

