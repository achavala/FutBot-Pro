#!/bin/bash
# Start trading loop for Gamma-only test

echo "============================================================"
echo "STARTING GAMMA-ONLY TRADING LOOP"
echo "============================================================"
echo ""

# Check if server is running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ Error: Server not running"
    echo "   Start server first: GAMMA_ONLY_TEST_MODE=true ./START_VALIDATION.sh"
    exit 1
fi

echo "✅ Server is running"
echo ""
echo "Starting trading loop..."
echo ""
echo "Option 1: Use Dashboard (recommended)"
echo "  1. Open: http://localhost:8000/dashboard"
echo "  2. Click 'Start Live' or 'Simulate' button"
echo ""
echo "Option 2: Start via API"
echo "  Run: curl -X POST http://localhost:8000/start-live \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"symbols\": [\"SPY\"], \"offline_mode\": true}'"
echo ""

# Try to start via API
echo "Attempting to start via API..."
RESPONSE=$(curl -s -X POST http://localhost:8000/start-live \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["SPY"], "offline_mode": true}' 2>&1)

if echo "$RESPONSE" | grep -q "error\|Error\|failed\|Failed"; then
    echo "⚠️  API start may have failed. Check response:"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    echo ""
    echo "Try using the dashboard instead: http://localhost:8000/dashboard"
else
    echo "✅ Trading loop started"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
fi

echo ""
echo "Monitor logs for:"
echo "  - 🔬 GAMMA_ONLY_TEST_MODE=true"
echo "  - ✅ Created X agents (Gamma Scalper only)"
echo "  - [GAMMA SCALP] entries"
echo "  - [DeltaHedge] hedge trades"
echo ""
echo "After 1-2 complete Gamma packages, export timelines:"
echo "  ./EXPORT_TIMELINES.sh"
echo ""

