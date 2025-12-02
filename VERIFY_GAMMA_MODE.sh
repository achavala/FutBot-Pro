#!/bin/bash
# Verify Gamma-only mode is active

echo "============================================================"
echo "VERIFYING GAMMA-ONLY MODE"
echo "============================================================"
echo ""

# Check if server is running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ Server not running"
    echo "   Start it first: ./CLEAN_START_GAMMA_ONLY.sh"
    exit 1
fi

echo "✅ Server is running"
echo ""

# Check logs for Gamma-only mode indicators
echo "🔍 Checking logs for Gamma-only mode indicators..."
echo ""

# Look for startup logs
if [ -d "logs" ]; then
    LATEST_LOG=$(ls -t logs/*.log 2>/dev/null | head -1)
    if [ -n "$LATEST_LOG" ]; then
        echo "📄 Checking log: $LATEST_LOG"
        echo ""
        
        # Check for Gamma-only mode
        if grep -q "GAMMA_ONLY_TEST_MODE=true" "$LATEST_LOG" 2>/dev/null; then
            echo "✅ Found: GAMMA_ONLY_TEST_MODE=true"
        else
            echo "❌ NOT FOUND: GAMMA_ONLY_TEST_MODE=true"
            echo "   Server was not started with Gamma-only mode!"
        fi
        
        # Check for Gamma Scalper only agents
        if grep -q "Gamma Scalper only" "$LATEST_LOG" 2>/dev/null; then
            echo "✅ Found: Gamma Scalper only agents created"
        else
            echo "⚠️  NOT FOUND: Gamma Scalper only agents"
        fi
        
        # Check for agent count
        AGENT_COUNT=$(grep -o "Created [0-9]* agents" "$LATEST_LOG" 2>/dev/null | tail -1)
        if [ -n "$AGENT_COUNT" ]; then
            echo "✅ Found: $AGENT_COUNT"
        fi
        
        echo ""
        echo "Recent Gamma-related log entries:"
        tail -50 "$LATEST_LOG" | grep -i "gamma\|GAMMA_ONLY" | tail -5 || echo "  None found"
    else
        echo "⚠️  No log files found"
    fi
else
    echo "⚠️  Logs directory not found"
fi

echo ""
echo "💡 To see live logs:"
echo "   tail -f logs/*.log | grep -i 'gamma\|GAMMA_ONLY'"
echo ""

