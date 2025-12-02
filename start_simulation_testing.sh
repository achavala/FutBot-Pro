#!/bin/bash
# Start simulation with testing_mode: true

API_BASE="http://localhost:8000"

# Get current date for default start time (today at 9:30 AM EST)
START_DATE=$(date -v-1d +"%Y-%m-%d" 2>/dev/null || date -d "1 day ago" +"%Y-%m-%d")
START_TIME="${START_DATE}T09:30:00"

# End time: same day at 4:00 PM EST
END_TIME="${START_DATE}T16:00:00"

echo "🚀 Starting simulation with testing_mode: true"
echo "📅 Start: $START_TIME"
echo "📅 End: $END_TIME"
echo ""

curl -X POST "${API_BASE}/live/start" \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY", "QQQ"],
    "broker_type": "cached",
    "offline_mode": true,
    "testing_mode": true,
    "replay_speed": 600.0,
    "start_time": "'"$START_TIME"'",
    "end_time": "'"$END_TIME"'",
    "fixed_investment_amount": 10000.0
  }' | python3 -m json.tool

echo ""
echo "✅ Simulation started!"
echo "📋 Check status: curl -s ${API_BASE}/live/status | python3 -m json.tool"
echo "📋 Check logs: tail -f /tmp/futbot_server.log | grep -E 'Controller|TradeExecution|Agent'"
