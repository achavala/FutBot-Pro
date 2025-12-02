#!/bin/bash
# Run focused Gamma Scalper only test

set -e

echo "============================================================"
echo "GAMMA SCALPER FOCUSED TEST"
echo "============================================================"
echo ""

# Enable Gamma-only test mode
export GAMMA_ONLY_TEST_MODE=true

# Configuration
SYMBOL="SPY"
OUTPUT_DIR="phase1_results/gamma_only"
TEST_PERIOD_START="2024-12-01"  # Adjust as needed
TEST_PERIOD_END="2024-12-05"    # 3-5 trading days

echo "Configuration:"
echo "  Symbol: $SYMBOL"
echo "  Period: $TEST_PERIOD_START → $TEST_PERIOD_END"
echo "  Output: $OUTPUT_DIR"
echo "  Mode: GAMMA_ONLY_TEST_MODE=true"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️ Virtual environment not activated"
    echo "   Activating .venv..."
    source .venv/bin/activate 2>/dev/null || echo "   Could not activate .venv"
fi

# Verify delta hedging config
echo "Verifying delta hedging configuration..."
python3 << 'EOF'
from core.live.delta_hedge_manager import DeltaHedgeConfig

config = DeltaHedgeConfig()
print(f"✅ Delta Hedging Config:")
print(f"   delta_threshold: {config.delta_threshold}")
print(f"   min_hedge_shares: {config.min_hedge_shares}")
print(f"   max_hedge_trades_per_day: {config.max_hedge_trades_per_day}")
print(f"   max_hedge_notional_per_day: ${config.max_hedge_notional_per_day:,.0f}")
print(f"   max_orphan_hedge_bars: {config.max_orphan_hedge_bars}")
EOF

echo ""
echo "📋 Next Steps:"
echo "   1. Start server: ./START_VALIDATION.sh"
echo "   2. Configure Gamma Scalper only (disable Theta Harvester)"
echo "   3. Start simulation for period: $TEST_PERIOD_START → $TEST_PERIOD_END"
echo "   4. Wait for 1-2 complete Gamma packages"
echo "   5. Export timelines: python3 scripts/export_hedge_timelines.py --output-dir $OUTPUT_DIR"
echo ""
echo "============================================================"

