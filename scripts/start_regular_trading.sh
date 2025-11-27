#!/bin/bash
# Start regular trading mode (not challenge mode)

echo "Starting regular trading mode..."
echo ""

# Check if API is running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ API server is not running!"
    echo "   Start it with: python3 -m uvicorn ui.fastapi_app:app --host 0.0.0.0 --port 8000"
    exit 1
fi

# Start regular trading with SPY
echo "Starting live trading for SPY..."
curl -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY"],
    "broker_type": "alpaca",
    "fixed_investment_amount": 1000.0
  }'

echo ""
echo ""
echo "✅ Trading started!"
echo ""
echo "Check status: curl http://localhost:8000/live/status"
echo "Check regime: curl http://localhost:8000/regime"
echo "Check health: curl http://localhost:8000/health"

