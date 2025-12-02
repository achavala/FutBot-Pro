#!/bin/bash
# Execute Gamma-Only Test - Step by Step

set -e

echo "============================================================"
echo "GAMMA-ONLY TEST EXECUTION"
echo "============================================================"
echo ""

# Step 1: Freeze (requires user confirmation)
echo "Step 1: Freeze current state"
echo "  Running: ./FREEZE_AND_TAG.sh"
echo ""
./FREEZE_AND_TAG.sh

echo ""
echo "============================================================"
echo "Step 2: Starting Gamma-only simulation"
echo "============================================================"
echo ""
echo "Starting server with GAMMA_ONLY_TEST_MODE=true..."
echo "  This will start the FastAPI server"
echo "  Monitor logs for:"
echo "    - 🔬 GAMMA_ONLY_TEST_MODE=true"
echo "    - ✅ Created X agents (Gamma Scalper only)"
echo "    - [GAMMA SCALP] entries"
echo ""
echo "Press Ctrl+C to stop the server when done"
echo ""

# Export env var and start server
export GAMMA_ONLY_TEST_MODE=true
./START_VALIDATION.sh

