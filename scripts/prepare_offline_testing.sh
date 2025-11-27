#!/usr/bin/env bash
# Prepare system for offline testing during market closure
# Run this before market closes to collect data for next 4 days

set -euo pipefail

echo "=========================================="
echo "PREPARING SYSTEM FOR OFFLINE TESTING"
echo "=========================================="
echo ""

API_BASE="${API_BASE:-http://localhost:8000}"
DATA_DIR="${DATA_DIR:-data}"
CACHE_DIR="${CACHE_DIR:-cache}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

check_api() {
    echo "Checking API server..."
    if curl -s "$API_BASE/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ API server is running${NC}"
        return 0
    else
        echo -e "${RED}❌ API server is not running${NC}"
        echo "   Start with: python main.py --mode api --port 8000"
        return 1
    fi
}

check_directories() {
    echo "Checking directories..."
    
    if [ ! -d "$DATA_DIR" ]; then
        echo "Creating $DATA_DIR directory..."
        mkdir -p "$DATA_DIR"
    fi
    echo -e "${GREEN}✅ Data directory: $DATA_DIR${NC}"
    
    if [ ! -d "$CACHE_DIR" ]; then
        echo "Creating $CACHE_DIR directory..."
        mkdir -p "$CACHE_DIR"
    fi
    echo -e "${GREEN}✅ Cache directory: $CACHE_DIR${NC}"
    
    # Check for bar cache
    if [ ! -d "$CACHE_DIR/bars" ]; then
        echo "Creating bar cache directory..."
        mkdir -p "$CACHE_DIR/bars"
    fi
    echo -e "${GREEN}✅ Bar cache directory: $CACHE_DIR/bars${NC}"
}

check_data_availability() {
    echo ""
    echo "Checking data availability..."
    
    # Check for cached bars
    SYMBOLS=("SPY" "QQQ" "BTC/USD")
    TOTAL_BARS=0
    
    for symbol in "${SYMBOLS[@]}"; do
        # Clean symbol for filename
        clean_symbol=$(echo "$symbol" | tr '/' '_')
        bar_count=$(find "$CACHE_DIR/bars" -name "*${clean_symbol}*" -type f 2>/dev/null | wc -l | tr -d ' ')
        
        if [ "$bar_count" -gt 0 ]; then
            echo -e "${GREEN}✅ Found cached bars for $symbol${NC}"
            TOTAL_BARS=$((TOTAL_BARS + bar_count))
        else
            echo -e "${YELLOW}⚠️  No cached bars for $symbol${NC}"
        fi
    done
    
    if [ "$TOTAL_BARS" -eq 0 ]; then
        echo -e "${YELLOW}⚠️  No cached data found. Starting data collection...${NC}"
        start_data_collection
    else
        echo -e "${GREEN}✅ Found $TOTAL_BARS cached bar files${NC}"
    fi
}

start_data_collection() {
    echo ""
    echo "Starting data collection..."
    
    # Try to start data collector via API if endpoint exists
    if curl -s -X POST "$API_BASE/data/collector/start" \
        -H "Content-Type: application/json" \
        -d '{"symbols": ["SPY", "QQQ"], "duration_hours": 24}' > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Data collector started via API${NC}"
    else
        echo -e "${YELLOW}⚠️  Data collector API not available${NC}"
        echo "   You may need to start data collection manually"
        echo "   Or ensure data collector service is running"
    fi
}

verify_cached_feed() {
    echo ""
    echo "Verifying cached data feed..."
    
    # Check if CachedDataFeed can be imported
    python3 << EOF
import sys
sys.path.insert(0, '.')
try:
    from core.live.data_feed_cached import CachedDataFeed
    print("✅ CachedDataFeed import successful")
except Exception as e:
    print(f"❌ CachedDataFeed import failed: {e}")
    sys.exit(1)
EOF
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Cached data feed is ready${NC}"
    else
        echo -e "${RED}❌ Cached data feed has issues${NC}"
        return 1
    fi
}

create_offline_config() {
    echo ""
    echo "Creating offline testing configuration..."
    
    cat > "$DATA_DIR/offline_config.json" << EOF
{
    "offline_mode": true,
    "use_cached_data": true,
    "cache_directory": "$CACHE_DIR",
    "symbols": ["SPY", "QQQ"],
    "test_duration_days": 4,
    "bar_interval_seconds": 60
}
EOF
    
    echo -e "${GREEN}✅ Offline config created: $DATA_DIR/offline_config.json${NC}"
}

print_summary() {
    echo ""
    echo "=========================================="
    echo "OFFLINE TESTING PREPARATION SUMMARY"
    echo "=========================================="
    echo ""
    echo "✅ System is ready for offline testing"
    echo ""
    echo "Next steps:"
    echo "1. Ensure data collector is running to gather data"
    echo "2. Use CachedDataFeed for offline trading"
    echo "3. Test with: python3 scripts/test_offline_trading.py"
    echo ""
    echo "To start offline trading:"
    echo "  curl -X POST $API_BASE/live/start \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"symbols\": [\"SPY\"], \"use_cached\": true}'"
    echo ""
    echo "Monitor data collection:"
    echo "  tail -f logs/*.log | grep -i 'collect\|cache'"
    echo ""
    echo "Check cached data:"
    echo "  ls -lh $CACHE_DIR/bars/"
    echo ""
}

# Main execution
main() {
    if ! check_api; then
        echo ""
        echo "⚠️  API server not running. Some checks will be skipped."
        echo ""
    fi
    
    check_directories
    check_data_availability
    verify_cached_feed
    create_offline_config
    print_summary
    
    echo -e "${GREEN}✅ System preparation complete!${NC}"
}

main

