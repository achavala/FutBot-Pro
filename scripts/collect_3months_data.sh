#!/usr/bin/env bash
# Quick script to collect 3 months of historical data for offline testing

set -euo pipefail

echo "=========================================="
echo "COLLECTING 3 MONTHS OF HISTORICAL DATA"
echo "=========================================="
echo ""

# Check API keys
if [ -z "${ALPACA_API_KEY:-}" ] && [ -z "${POLYGON_API_KEY:-}" ]; then
    echo "⚠️  Warning: No API keys found in environment"
    echo "   Set ALPACA_API_KEY or POLYGON_API_KEY"
    echo ""
fi

# Default symbols
STOCKS="${STOCKS:-SPY QQQ}"
CRYPTO="${CRYPTO:-BTC/USD}"
OPTIONS="${OPTIONS:-SPY}"

echo "Stocks: $STOCKS"
echo "Crypto: $CRYPTO"
echo "Options: $OPTIONS"
echo ""

# Check if Polygon API key is available (better for historical data)
if [ -n "${POLYGON_API_KEY:-}" ]; then
    echo "✅ Polygon API key found - using Polygon for historical data"
    echo ""
    python3 scripts/collect_historical_data.py \
        --months 3 \
        --stocks $STOCKS \
        --crypto $CRYPTO \
        --options $OPTIONS \
        --use-polygon
else
    echo "⚠️  No Polygon API key - using Alpaca (may be slower)"
    echo ""
    python3 scripts/collect_historical_data.py \
        --months 3 \
        --stocks $STOCKS \
        --crypto $CRYPTO \
        --options $OPTIONS
fi

echo ""
echo "=========================================="
echo "DATA COLLECTION COMPLETE"
echo "=========================================="
echo ""
echo "To verify data:"
echo "  python3 scripts/test_offline_trading.py"
echo ""
echo "To check cache:"
echo "  ls -lh cache/bars/"
echo ""

