#!/bin/bash

# Phase 1 Complete Validation Script
# This script validates all improvements: strict_data_mode, price integrity, trade augmentation

set -e

echo "🔍 PHASE 1 VALIDATION SCRIPT"
echo "============================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Verify strict data mode works
echo "📋 STEP 1: Verifying strict_data_mode..."
echo "Starting simulation with strict_data_mode=true..."

RESPONSE=$(curl -s -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["QQQ"],
    "broker_type": "cached",
    "offline_mode": true,
    "testing_mode": true,
    "replay_speed": 500.0,
    "start_time": "2025-11-26T09:30:00Z",
    "end_time": "2025-11-26T10:00:00Z",
    "fixed_investment_amount": 10000.0
  }')

echo "Response: $RESPONSE"
sleep 5

# Check for SyntheticBarFallback in logs
SYNTHETIC_COUNT=$(grep -c "SyntheticBarFallback" /tmp/futbot_server.log 2>/dev/null || echo "0")
CACHED_COUNT=$(grep -c "Loading cached data" /tmp/futbot_server.log 2>/dev/null || echo "0")

if [ "$SYNTHETIC_COUNT" -eq "0" ]; then
    echo -e "${GREEN}✅ PASS: No synthetic bars used${NC}"
else
    echo -e "${RED}❌ FAIL: Found $SYNTHETIC_COUNT synthetic bar fallbacks${NC}"
    echo "Recent synthetic bar logs:"
    grep "SyntheticBarFallback" /tmp/futbot_server.log | tail -5
fi

if [ "$CACHED_COUNT" -gt "0" ]; then
    echo -e "${GREEN}✅ PASS: Cached data loaded ($CACHED_COUNT times)${NC}"
else
    echo -e "${YELLOW}⚠️  WARNING: No 'Loading cached data' messages found${NC}"
fi

echo ""

# Step 2: Verify price integrity
echo "📋 STEP 2: Verifying price integrity..."
echo "Fetching round-trip trades..."

TRADES_JSON=$(curl -s "http://localhost:8000/trades/roundtrips?symbol=QQQ&limit=5")

if [ -z "$TRADES_JSON" ] || [ "$TRADES_JSON" = "null" ]; then
    echo -e "${RED}❌ FAIL: No trades returned${NC}"
    exit 1
fi

# Extract entry prices
ENTRY_PRICES=$(echo "$TRADES_JSON" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    trades = data.get('trades', [])
    if not trades:
        print('NO_TRADES')
    else:
        prices = [t.get('entry_price', 0) for t in trades if t.get('entry_price')]
        if prices:
            print(' '.join(map(str, prices)))
        else:
            print('NO_PRICES')
except Exception as e:
    print(f'ERROR: {e}')
")

if [ "$ENTRY_PRICES" = "NO_TRADES" ] || [ "$ENTRY_PRICES" = "NO_PRICES" ]; then
    echo -e "${YELLOW}⚠️  WARNING: No trades or prices found${NC}"
    echo "Full response:"
    echo "$TRADES_JSON" | python3 -m json.tool | head -20
else
    echo "Entry prices found: $ENTRY_PRICES"
    
    # Check if prices are in expected range (600-650 for QQQ in Nov 2025)
    INVALID_PRICES=0
    for price in $ENTRY_PRICES; do
        if (( $(echo "$price < 550" | bc -l) )) || (( $(echo "$price > 650" | bc -l) )); then
            INVALID_PRICES=$((INVALID_PRICES + 1))
            echo -e "${RED}❌ Invalid price: $price (expected 550-650)${NC}"
        fi
    done
    
    if [ "$INVALID_PRICES" -eq "0" ]; then
        echo -e "${GREEN}✅ PASS: All entry prices in expected range (550-650)${NC}"
    else
        echo -e "${RED}❌ FAIL: $INVALID_PRICES prices outside expected range${NC}"
    fi
fi

echo ""

# Step 3: Verify trade augmentation
echo "📋 STEP 3: Verifying trade augmentation (regime/volatility metadata)..."

REQUIRED_FIELDS=("regime_at_entry" "vol_bucket_at_entry" "agent" "gross_pnl" "pnl_pct" "duration_minutes")
MISSING_FIELDS=0

for field in "${REQUIRED_FIELDS[@]}"; do
    if echo "$TRADES_JSON" | python3 -c "
import sys, json
data = json.load(sys.stdin)
trades = data.get('trades', [])
if trades and '$field' in trades[0]:
    print('FOUND')
else:
    print('MISSING')
" | grep -q "FOUND"; then
        echo -e "${GREEN}✅ Field '$field' present${NC}"
    else
        echo -e "${RED}❌ Field '$field' missing${NC}"
        MISSING_FIELDS=$((MISSING_FIELDS + 1))
    fi
done

if [ "$MISSING_FIELDS" -eq "0" ]; then
    echo -e "${GREEN}✅ PASS: All required fields present${NC}"
else
    echo -e "${RED}❌ FAIL: $MISSING_FIELDS required fields missing${NC}"
fi

echo ""

# Step 4: Display sample trade
echo "📋 STEP 4: Sample trade structure..."
echo "$TRADES_JSON" | python3 -c "
import sys, json
data = json.load(sys.stdin)
trades = data.get('trades', [])
if trades:
    trade = trades[0]
    print('Sample Trade:')
    print(f'  Symbol: {trade.get(\"symbol\")}')
    print(f'  Entry Price: {trade.get(\"entry_price\")}')
    print(f'  Entry Time: {trade.get(\"entry_time\")}')
    print(f'  Regime: {trade.get(\"regime_at_entry\")}')
    print(f'  Volatility: {trade.get(\"vol_bucket_at_entry\")}')
    print(f'  Agent: {trade.get(\"agent\")}')
    print(f'  P&L: \${trade.get(\"gross_pnl\", 0):.2f} ({trade.get(\"pnl_pct\", 0):.2f}%)')
    print(f'  Duration: {trade.get(\"duration_minutes\", 0):.2f} minutes')
else:
    print('No trades found')
"

echo ""
echo "============================"
echo "✅ VALIDATION COMPLETE"
echo ""
echo "Next steps:"
echo "1. Manually verify prices match Webull (see PRICE_VALIDATION_GUIDE.md)"
echo "2. Check /stats endpoint for regime synchronization"
echo "3. Proceed to full-day backtest benchmark"


