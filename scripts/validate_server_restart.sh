#!/bin/bash
# Validation script to confirm server restart and new code is loaded

echo "🔍 Validating Server Restart and New Code..."
echo ""

# Step 1: Check if server is running
echo "1️⃣ Checking if server is running..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✅ Server is running"
else
    echo "   ❌ Server is NOT running - start it first!"
    exit 1
fi

# Step 2: Check version endpoint
echo ""
echo "2️⃣ Checking version endpoint..."
VERSION=$(curl -s http://localhost:8000/version 2>/dev/null)
if [ -n "$VERSION" ]; then
    echo "   ✅ Version endpoint exists"
    echo "   Response: $VERSION"
    if echo "$VERSION" | grep -q "synthetic_bar_fallback"; then
        echo "   ✅ New code features detected!"
    else
        echo "   ⚠️  May be running old code"
    fi
else
    echo "   ⚠️  Version endpoint not available (may be old server)"
fi

# Step 3: Check logs for synthetic fallback
echo ""
echo "3️⃣ Checking logs for synthetic fallback messages..."
if tail -n 50 /tmp/futbot_server.log 2>/dev/null | grep -q "synthetic_enabled\|synthetic fallback"; then
    echo "   ✅ Synthetic fallback messages found in logs"
else
    echo "   ⚠️  No synthetic fallback messages (may be old code)"
fi

# Step 4: Start trading and check bars_per_symbol
echo ""
echo "4️⃣ Starting trading with testing_mode..."
RESPONSE=$(curl -s -X POST http://localhost:8000/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["SPY"],
    "broker_type": "cached",
    "offline_mode": true,
    "testing_mode": true,
    "replay_speed": 600.0
  }')

if echo "$RESPONSE" | grep -q "started"; then
    echo "   ✅ Trading started successfully"
else
    echo "   ❌ Failed to start trading: $RESPONSE"
    exit 1
fi

# Step 5: Wait and check bars_per_symbol
echo ""
echo "5️⃣ Waiting 5 seconds and checking bars_per_symbol..."
sleep 5

STATUS=$(curl -s http://localhost:8000/live/status)
BARS_PER_SYMBOL=$(echo "$STATUS" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('bars_per_symbol', {}).get('SPY', 0))" 2>/dev/null)

if [ -n "$BARS_PER_SYMBOL" ] && [ "$BARS_PER_SYMBOL" -gt 0 ]; then
    echo "   ✅ SUCCESS! bars_per_symbol['SPY'] = $BARS_PER_SYMBOL"
    echo "   ✅ New code is working correctly!"
else
    echo "   ❌ bars_per_symbol['SPY'] = $BARS_PER_SYMBOL (expected > 0)"
    echo "   ⚠️  May need to check logs or restart server"
    echo ""
    echo "   Full status:"
    echo "$STATUS" | python3 -m json.tool 2>/dev/null || echo "$STATUS"
fi

# Step 6: Check logs for bars_per_symbol updates
echo ""
echo "6️⃣ Checking logs for bars_per_symbol updates..."
if tail -n 100 /tmp/futbot_server.log 2>/dev/null | grep -q "bars_per_symbol.*SPY\|Updated bars_per_symbol"; then
    echo "   ✅ bars_per_symbol update messages found"
else
    echo "   ⚠️  No bars_per_symbol update messages in recent logs"
fi

echo ""
echo "✅ Validation complete!"


