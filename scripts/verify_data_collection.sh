#!/bin/bash
# Quick verification script for data collection

echo "🔍 Verifying Data Collection Setup..."
echo ""

# Check if script exists
if [ ! -f "scripts/collect_historical_data.py" ]; then
    echo "❌ Script not found: scripts/collect_historical_data.py"
    exit 1
fi

# Check if .env has Alpaca credentials
if [ -f ".env" ]; then
    if grep -q "ALPACA_API_KEY" .env && grep -q "ALPACA_SECRET_KEY" .env; then
        echo "✅ Alpaca credentials found in .env"
    else
        echo "⚠️  Alpaca credentials not found in .env"
    fi
else
    echo "⚠️  .env file not found"
fi

# Check cache directory
if [ -d "data" ]; then
    echo "✅ Data directory exists"
    if [ -f "data/cache.db" ]; then
        SIZE=$(du -h data/cache.db | cut -f1)
        echo "✅ Cache database exists: $SIZE"
    else
        echo "ℹ️  Cache database will be created on first run"
    fi
else
    echo "ℹ️  Data directory will be created on first run"
fi

echo ""
echo "📋 Ready to run:"
echo "   python3 scripts/collect_historical_data.py --stocks SPY QQQ --months 3"
echo ""
echo "This will collect delayed data (2+ days old) to avoid SIP subscription errors."
