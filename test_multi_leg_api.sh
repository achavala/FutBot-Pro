#!/bin/bash
# Test multi-leg API endpoints using curl

API_BASE="http://localhost:8000"

echo "============================================================"
echo "MULTI-LEG API ENDPOINT TESTS"
echo "============================================================"
echo ""

# Test 1: Get options positions
echo "TEST 1: GET /options/positions"
echo "------------------------------------------------------------"
response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "${API_BASE}/options/positions")
http_status=$(echo "$response" | grep "HTTP_STATUS:" | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_STATUS:/d')

if [ "$http_status" = "200" ]; then
    echo "✅ Status: $http_status"
    single_count=$(echo "$body" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('positions', [])))" 2>/dev/null || echo "0")
    multi_count=$(echo "$body" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('multi_leg_positions', [])))" 2>/dev/null || echo "0")
    echo "   Single-leg positions: $single_count"
    echo "   Multi-leg positions: $multi_count"
    
    if [ "$multi_count" -gt 0 ]; then
        echo ""
        echo "   Multi-Leg Positions:"
        echo "$body" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for pos in data.get('multi_leg_positions', []):
        print(f\"      - {pos['trade_type'].upper()} {pos['direction']} {pos['symbol']}\")
        print(f\"        Call: \${pos['call_strike']:.2f} @ \${pos['call_entry_price']:.2f}\")
        print(f\"        Put: \${pos['put_strike']:.2f} @ \${pos['put_entry_price']:.2f}\")
        print(f\"        P&L: \${pos['combined_unrealized_pnl']:.2f}\")
        print(f\"        Filled: {pos['both_legs_filled']}\")
except:
    pass
" 2>/dev/null
    fi
else
    echo "⚠️ Status: $http_status"
    echo "   Response: $(echo "$body" | head -c 200)"
fi

echo ""
echo ""

# Test 2: Get multi-leg trades
echo "TEST 2: GET /trades/options/multi-leg"
echo "------------------------------------------------------------"
response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "${API_BASE}/trades/options/multi-leg?limit=10")
http_status=$(echo "$response" | grep "HTTP_STATUS:" | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_STATUS:/d')

if [ "$http_status" = "200" ]; then
    echo "✅ Status: $http_status"
    trade_count=$(echo "$body" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('trades', [])))" 2>/dev/null || echo "0")
    echo "   Multi-leg trades: $trade_count"
    
    if [ "$trade_count" -gt 0 ]; then
        echo ""
        echo "   Recent Trades:"
        echo "$body" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for trade in data.get('trades', [])[:3]:
        pnl_sign = '✅' if trade['combined_pnl'] >= 0 else '❌'
        print(f\"      {pnl_sign} {trade['trade_type'].upper()} {trade['direction']}\")
        print(f\"         P&L: \${trade['combined_pnl']:.2f} ({trade['combined_pnl_pct']:.1f}%)\")
        print(f\"         Duration: {trade['duration_minutes']:.1f}m\")
except:
    pass
" 2>/dev/null
    fi
else
    echo "⚠️ Status: $http_status"
fi

echo ""
echo ""

# Test 3: Check live status
echo "TEST 3: GET /live/status"
echo "------------------------------------------------------------"
response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "${API_BASE}/live/status")
http_status=$(echo "$response" | grep "HTTP_STATUS:" | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_STATUS:/d')

if [ "$http_status" = "200" ]; then
    echo "✅ Status: $http_status"
    is_running=$(echo "$body" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('is_running', False))" 2>/dev/null || echo "false")
    mode=$(echo "$body" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('mode', 'unknown'))" 2>/dev/null || echo "unknown")
    bar_count=$(echo "$body" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('bar_count', 0))" 2>/dev/null || echo "0")
    echo "   Running: $is_running"
    echo "   Mode: $mode"
    echo "   Bar Count: $bar_count"
else
    echo "⚠️ Status: $http_status"
fi

echo ""
echo "============================================================"
echo "✅ API TESTS COMPLETE"
echo "============================================================"
echo ""
echo "Next Steps:"
echo "1. Start live trading to generate multi-leg positions"
echo "2. Check dashboard at http://localhost:8000/dashboard"
echo "3. Navigate to Analytics → Options Dashboard"
echo "4. View Multi-Leg Positions and Trade History tables"


