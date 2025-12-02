#!/bin/bash

# System Validation Script
# Run this to quickly validate all system components

echo "=========================================="
echo "  FutBot Pro - System Validation"
echo "=========================================="
echo ""

API_BASE="http://localhost:8000"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: API Health
echo "1️⃣  Testing API Health..."
HEALTH=$(curl -s "${API_BASE}/health" 2>/dev/null)
if [ $? -eq 0 ] && echo "$HEALTH" | grep -q "ok"; then
    echo -e "${GREEN}✅ API is healthy${NC}"
else
    echo -e "${RED}❌ API health check failed${NC}"
    exit 1
fi
echo ""

# Test 2: Available Cached Dates
echo "2️⃣  Checking Available Cached Dates..."
CACHE_RESPONSE=$(curl -s "${API_BASE}/cache/available-dates?timeframe=1min" 2>/dev/null)
if [ $? -eq 0 ]; then
    TOTAL_DATES=$(echo "$CACHE_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('total_dates', 0))" 2>/dev/null)
    if [ -n "$TOTAL_DATES" ] && [ "$TOTAL_DATES" -gt 0 ]; then
        echo -e "${GREEN}✅ Found ${TOTAL_DATES} dates with cached data${NC}"
        echo "$CACHE_RESPONSE" | python3 -m json.tool | head -30
    else
        echo -e "${YELLOW}⚠️  No cached dates found. Please collect historical data first.${NC}"
    fi
else
    echo -e "${RED}❌ Failed to fetch cached dates${NC}"
fi
echo ""

# Test 3: Stock Trades
echo "3️⃣  Checking Stock Trades..."
STOCK_TRADES=$(curl -s "${API_BASE}/trades/roundtrips?limit=5" 2>/dev/null)
if [ $? -eq 0 ]; then
    TRADE_COUNT=$(echo "$STOCK_TRADES" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('trades', [])))" 2>/dev/null)
    if [ -n "$TRADE_COUNT" ]; then
        if [ "$TRADE_COUNT" -gt 0 ]; then
            echo -e "${GREEN}✅ Found ${TRADE_COUNT} stock trades${NC}"
            echo "$STOCK_TRADES" | python3 -m json.tool | head -40
        else
            echo -e "${YELLOW}⚠️  No stock trades found (run a simulation first)${NC}"
        fi
    fi
else
    echo -e "${RED}❌ Failed to fetch stock trades${NC}"
fi
echo ""

# Test 4: Options Trades
echo "4️⃣  Checking Options Trades..."
OPTIONS_TRADES=$(curl -s "${API_BASE}/trades/options/roundtrips?limit=5" 2>/dev/null)
if [ $? -eq 0 ]; then
    OPTIONS_COUNT=$(echo "$OPTIONS_TRADES" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('trades', [])))" 2>/dev/null)
    if [ -n "$OPTIONS_COUNT" ]; then
        if [ "$OPTIONS_COUNT" -gt 0 ]; then
            echo -e "${GREEN}✅ Found ${OPTIONS_COUNT} options trades${NC}"
            echo "$OPTIONS_TRADES" | python3 -m json.tool | head -40
        else
            echo -e "${YELLOW}⚠️  No options trades found (options agent may not have generated intents)${NC}"
        fi
    fi
else
    echo -e "${RED}❌ Failed to fetch options trades${NC}"
fi
echo ""

# Test 5: System Status
echo "5️⃣  Checking System Status..."
STATUS=$(curl -s "${API_BASE}/live/status" 2>/dev/null)
if [ $? -eq 0 ]; then
    IS_RUNNING=$(echo "$STATUS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('is_running', False))" 2>/dev/null)
    MODE=$(echo "$STATUS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('mode', 'unknown'))" 2>/dev/null)
    BARS=$(echo "$STATUS" | python3 -c "import sys, json; data=json.load(sys.stdin); bars=data.get('bars_per_symbol', {}); print(sum(bars.values()) if bars else 0)" 2>/dev/null)
    
    echo "   Mode: $MODE"
    echo "   Running: $IS_RUNNING"
    echo "   Total Bars: $BARS"
    
    if [ "$IS_RUNNING" = "True" ]; then
        echo -e "${YELLOW}⚠️  Simulation is currently running${NC}"
    else
        echo -e "${GREEN}✅ System is idle (ready for simulation)${NC}"
    fi
else
    echo -e "${RED}❌ Failed to fetch system status${NC}"
fi
echo ""

# Test 6: Options Dashboard Endpoints
echo "6️⃣  Testing Options Dashboard Endpoints..."
ENDPOINTS=(
    "/visualizations/options-equity-curve"
    "/visualizations/options-drawdown"
    "/visualizations/options-pnl-by-symbol"
    "/visualizations/options-vs-stock"
)

for endpoint in "${ENDPOINTS[@]}"; do
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}${endpoint}" 2>/dev/null)
    if [ "$RESPONSE" = "200" ]; then
        echo -e "${GREEN}✅ ${endpoint}${NC}"
    else
        echo -e "${YELLOW}⚠️  ${endpoint} returned ${RESPONSE}${NC}"
    fi
done
echo ""

# Summary
echo "=========================================="
echo "  Validation Complete"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "1. If no cached dates found → Run: python scripts/collect_historical_data.py --stocks SPY QQQ --months 3"
echo "2. If no trades found → Start a simulation from the dashboard"
echo "3. If options trades missing → Check that options agent is enabled and conditions are met"
echo "4. Navigate to Analytics → Options Dashboard to view visualizations"
echo ""


