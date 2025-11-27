#!/bin/bash
# Check if OptionsAgent is being called in the trading loop

echo "Checking if OptionsAgent is being called..."
echo ""

# Check if API is running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ API server is not running!"
    exit 1
fi

# Check if options trading is active
echo "1. Checking if options trading is active..."
STATUS=$(curl -s http://localhost:8000/live/status)
if echo "$STATUS" | grep -q "SPY\|QQQ"; then
    echo "   ✅ Live trading is active"
else
    echo "   ⚠️  Live trading may not be active"
fi

echo ""
echo "2. Checking agents..."
AGENTS=$(curl -s http://localhost:8000/agents)
if echo "$AGENTS" | grep -qi "options"; then
    echo "   ✅ OptionsAgent found in agents list"
else
    echo "   ⚠️  OptionsAgent not found in agents list"
fi

echo ""
echo "3. To see if OptionsAgent is being called, check logs:"
echo "   tail -f logs/*.log | grep -i 'optionsagent'"
echo ""
echo "   Look for:"
echo "   - 'OptionsAgent.evaluate() called for SPY'"
echo "   - 'OptionsAgent: Fetching options chain'"
echo "   - 'OptionsAgent: Evaluating contract'"
echo ""
echo "4. If you don't see these logs, the agent may not be wired into the loop."

