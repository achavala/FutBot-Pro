#!/bin/bash
# Step 2: Start Gamma-only test

echo "============================================================"
echo "STEP 2: START GAMMA-ONLY TEST"
echo "============================================================"
echo ""

# Check if freeze was completed
TAG_NAME="v1.0.1-ml-gamma-qa"
if ! git rev-parse "$TAG_NAME" >/dev/null 2>&1; then
    echo "⚠️  Warning: Tag '$TAG_NAME' not found"
    echo "   Make sure Step 1 (freeze & tag) completed successfully"
    echo ""
    read -p "Continue anyway? (y/N) " ans
    if [[ "$ans" != "y" && "$ans" != "Y" ]]; then
        echo "Aborting."
        exit 1
    fi
fi

echo "✅ Starting Gamma-only test..."
echo ""
echo "Configuration:"
echo "  Mode: GAMMA_ONLY_TEST_MODE=true"
echo "  Tag: $TAG_NAME"
echo ""
echo "Watch logs for:"
echo "  - 🔬 GAMMA_ONLY_TEST_MODE=true (env var: true)"
echo "  - ✅ Created X agents (Gamma Scalper only)"
echo "  - [GAMMA SCALP] entries"
echo "  - [DeltaHedge] hedge trades"
echo ""
echo "Press Ctrl+C to stop the server when done"
echo ""

# Export env var and start server
export GAMMA_ONLY_TEST_MODE=true
./START_VALIDATION.sh

