#!/bin/bash
# Ensure data collector is running for offline testing

echo "🔍 Checking data collector status..."

# Check if API server is running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ API server is not running. Please start it first:"
    echo "   python main.py --mode api --port 8000"
    exit 1
fi

# Check collector status
STATUS=$(curl -s http://localhost:8000/data-collector/status 2>/dev/null)

if echo "$STATUS" | grep -q "is_running.*true"; then
    echo "✅ Data collector is already running"
    echo "$STATUS" | python3 -m json.tool
    exit 0
fi

echo "📊 Starting data collector..."

# Start collector with default symbols (QQQ, SPY)
RESPONSE=$(curl -s -X POST http://localhost:8000/data-collector/start \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["QQQ", "SPY"], "bar_size": "1Min"}')

if echo "$RESPONSE" | grep -q "started"; then
    echo "✅ Data collector started successfully!"
    echo "$RESPONSE" | python3 -m json.tool
    echo ""
    echo "📝 The collector will:"
    echo "   - Collect data every 1 minute during trading hours (9:30 AM - 4:00 PM ET)"
    echo "   - Collect data every 5 minutes outside trading hours"
    echo "   - Store data in cache for offline trading"
    echo ""
    echo "💡 To test offline, use:"
    echo "   curl -X POST http://localhost:8000/live/start \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -d '{\"symbols\": [\"QQQ\"], \"broker_type\": \"cached\"}'"
else
    echo "❌ Failed to start data collector:"
    echo "$RESPONSE" | python3 -m json.tool
    exit 1
fi

