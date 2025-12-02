#!/bin/bash
# FutBot Pro - Quick Launch Script for Market Open

echo "🚀 FutBot Pro - Market Open Launch"
echo "===================================="
echo ""

# Check environment variables
if [ -z "$ALPACA_API_KEY" ] || [ -z "$ALPACA_SECRET_KEY" ]; then
    echo "❌ ERROR: Alpaca credentials not set"
    echo "   Run: export ALPACA_API_KEY='your_key'"
    echo "   Run: export ALPACA_SECRET_KEY='your_secret'"
    exit 1
fi

echo "✅ Credentials found"
echo ""

# Validate setup
echo "📋 Running validation..."
python scripts/validate_alpaca_options_paper.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Validation failed - DO NOT PROCEED"
    exit 1
fi

echo ""
echo "✅ Validation passed"
echo ""

# Check server
echo "🔍 Checking server status..."
STATUS=$(curl -s http://localhost:8000/health 2>/dev/null)
if [ "$STATUS" != '{"status":"ok"}' ]; then
    echo "⚠️  Server not running - starting server..."
    echo "   Run: python main.py --mode api --port 8000"
    echo "   Then run this script again"
    exit 1
fi

echo "✅ Server is running"
echo ""

# Launch trading
echo "🚀 Launching live trading..."
echo ""

RESPONSE=$(curl -s -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY", "QQQ"],
    "broker_type": "alpaca",
    "offline_mode": false,
    "testing_mode": false,
    "strict_data_mode": false,
    "replay_speed": 1.0,
    "fixed_investment_amount": 10000
  }')

echo "$RESPONSE" | python -m json.tool

echo ""
echo "✅ Launch command sent"
echo ""
echo "📊 Monitor at:"
echo "   • Logs: tail -f /tmp/futbot_server.log"
echo "   • Status: curl http://localhost:8000/live/status"
echo "   • Alpaca: https://app.alpaca.markets/paper/trade"
echo ""
echo "🛑 To stop: curl -X POST http://localhost:8000/live/stop"
echo ""
