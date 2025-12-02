#!/bin/bash
# Check for Gamma Scalper activity

echo "============================================================"
echo "GAMMA SCALPER ACTIVITY CHECK"
echo "============================================================"
echo ""

# Check server status
echo "📊 Server Status:"
STATUS=$(curl -s http://localhost:8000/health | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"Status: {d.get('status')}\"); print(f\"Running: {d.get('is_running')}\"); print(f\"Bars: {d.get('bar_count')}\")" 2>/dev/null)
echo "$STATUS"
echo ""

# Check for multi-leg positions
echo "📈 Open Multi-Leg Positions:"
POSITIONS=$(curl -s http://localhost:8000/options/multi-leg-positions 2>/dev/null)
if echo "$POSITIONS" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"Count: {len(d.get('positions', []))}\"); [print(f\"  - {p.get('strategy')} {p.get('symbol')} {p.get('multi_leg_id')}\") for p in d.get('positions', [])]" 2>/dev/null; then
    echo ""
else
    echo "  None yet"
    echo ""
fi

# Check for completed multi-leg trades
echo "📊 Completed Multi-Leg Trades:"
TRADES=$(curl -s http://localhost:8000/options/multi-leg-trades 2>/dev/null)
if echo "$TRADES" | python3 -c "import sys, json; d=json.load(sys.stdin); trades=d.get('trades', []); print(f\"Count: {len(trades)}\"); [print(f\"  - {t.get('strategy')} {t.get('symbol')} P&L: \${t.get('total_pnl', 0):.2f}\") for t in trades[:5]]" 2>/dev/null; then
    echo ""
else
    echo "  None yet"
    echo ""
fi

# Check for Gamma Scalper specifically
echo "🔍 Gamma Scalper Activity:"
GAMMA_POSITIONS=$(echo "$POSITIONS" | python3 -c "import sys, json; d=json.load(sys.stdin); g=[p for p in d.get('positions', []) if p.get('strategy')=='gamma_scalper']; print(f\"Open Gamma positions: {len(g)}\"); [print(f\"  - {p.get('multi_leg_id')} {p.get('symbol')} P&L: \${p.get('unrealized_pnl', 0):.2f}\") for p in g]" 2>/dev/null)
if [ -n "$GAMMA_POSITIONS" ]; then
    echo "$GAMMA_POSITIONS"
else
    echo "  No Gamma Scalper positions yet"
fi

GAMMA_TRADES=$(echo "$TRADES" | python3 -c "import sys, json; d=json.load(sys.stdin); g=[t for t in d.get('trades', []) if t.get('strategy')=='gamma_scalper']; print(f\"Completed Gamma trades: {len(g)}\"); [print(f\"  - {t.get('multi_leg_id')} {t.get('symbol')} P&L: \${t.get('total_pnl', 0):.2f}\") for t in g[:3]]" 2>/dev/null)
if [ -n "$GAMMA_TRADES" ]; then
    echo "$GAMMA_TRADES"
else
    echo "  No completed Gamma Scalper trades yet"
fi

echo ""
echo "💡 Tips:"
echo "  - Monitor logs: tail -f logs/*.log | grep -i 'gamma\|deltahedge'"
echo "  - Check dashboard: http://localhost:8000/dashboard"
echo "  - After 1-2 complete packages: ./EXPORT_TIMELINES.sh"
echo ""

