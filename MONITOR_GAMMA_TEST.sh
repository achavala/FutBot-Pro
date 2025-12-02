#!/bin/bash
# Monitor Gamma-only test execution

echo "============================================================"
echo "GAMMA-ONLY TEST MONITOR"
echo "============================================================"
echo ""

# Check server status
echo "📊 Server Status:"
curl -s http://localhost:8000/health | python3 -m json.tool | grep -E "is_running|status|bar_count" | head -5
echo ""

# Check if trading loop is running
IS_RUNNING=$(curl -s http://localhost:8000/health | python3 -c "import sys, json; print(json.load(sys.stdin).get('is_running', False))" 2>/dev/null || echo "false")

if [ "$IS_RUNNING" = "true" ]; then
    echo "✅ Trading loop is running"
    echo ""
    echo "Watch for these indicators:"
    echo "  - 🔬 GAMMA_ONLY_TEST_MODE=true"
    echo "  - ✅ Created X agents (Gamma Scalper only)"
    echo "  - [GAMMA SCALP] entries"
    echo "  - [DeltaHedge] hedge trades"
    echo ""
    echo "Monitor logs:"
    echo "  tail -f logs/*.log | grep -i 'gamma\|deltahedge\|multileg'"
    echo ""
    echo "Check positions:"
    echo "  curl -s http://localhost:8000/options/multi-leg-positions | python3 -m json.tool"
    echo ""
    echo "Check trades:"
    echo "  curl -s http://localhost:8000/options/multi-leg-trades | python3 -m json.tool"
else
    echo "⚠️  Trading loop is NOT running"
    echo ""
    echo "Start it via:"
    echo "  Option 1: Dashboard → http://localhost:8000/dashboard → Click 'Start Live'"
    echo "  Option 2: API → ./START_TRADING_GAMMA_ONLY.sh"
    echo "  Option 3: curl -X POST http://localhost:8000/start-live \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"symbols\": [\"SPY\"], \"offline_mode\": true}'"
fi

echo ""
echo "After 1-2 complete Gamma packages, export timelines:"
echo "  ./EXPORT_TIMELINES.sh"
echo ""

