#!/bin/bash
# Monitor bot status and bar collection

echo "=== FutBot Live Trading Monitor ==="
echo ""

while true; do
    clear
    echo "=== FutBot Status - $(date) ==="
    echo ""
    
    # Check if API server is running
    if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "❌ API server is not running!"
        echo "   Start it with: python main.py --mode api --port 8000"
        echo ""
        sleep 5
        continue
    fi
    
    # Live status
    echo "📊 Live Trading Status:"
    LIVE_STATUS=$(curl -s http://localhost:8000/live/status 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "$LIVE_STATUS" | python3 -m json.tool 2>/dev/null | grep -E "(mode|is_running|bar_count|last_bar_time|error)" || echo "$LIVE_STATUS"
        
        # Check if bot is actually running
        IS_RUNNING=$(echo "$LIVE_STATUS" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('is_running', False))" 2>/dev/null)
        MODE=$(echo "$LIVE_STATUS" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('mode', 'unknown'))" 2>/dev/null)
        
        if [ "$IS_RUNNING" != "True" ] || [ "$MODE" != "live" ]; then
            echo ""
            echo "⚠️  Bot is NOT running in live mode!"
            echo "   Start it with:"
            echo "   curl -X POST http://localhost:8000/live/start \\"
            echo "     -H 'Content-Type: application/json' \\"
            echo "     -d '{\"symbols\": [\"QQQ\"], \"broker_type\": \"ibkr\", \"ibkr_host\": \"127.0.0.1\", \"ibkr_port\": 4002}'"
        fi
    else
        echo "Error getting status"
    fi
    echo ""
    
    # Portfolio stats
    echo "💰 Portfolio Stats:"
    curl -s http://localhost:8000/stats | python3 -m json.tool 2>/dev/null | grep -E "(total_trades|total_return|open_positions)" || echo "Error getting stats"
    echo ""
    
    # Risk status
    echo "🛡️ Risk Status:"
    curl -s http://localhost:8000/risk-status | python3 -m json.tool 2>/dev/null | grep -E "(can_trade|kill_switch|circuit_breaker)" || echo "Error getting risk status"
    echo ""
    
    # Recent logs
    echo "📝 Recent Events (last 3):"
    if [ -f logs/trading_events.jsonl ]; then
    tail -3 logs/trading_events.jsonl 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "No logs yet"
    else
        echo "No log file found"
    fi
    echo ""
    
    echo "Press Ctrl+C to stop monitoring"
    sleep 5
done

