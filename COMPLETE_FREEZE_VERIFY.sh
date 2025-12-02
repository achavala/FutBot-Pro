#!/bin/bash
# Complete freeze verification and next steps

echo "============================================================"
echo "FREEZE VERIFICATION"
echo "============================================================"
echo ""

# Check git status
echo "📊 Git status:"
git status
echo ""

# Check if tag exists
TAG_NAME="v1.0.1-ml-gamma-qa"
echo "🏷️  Checking for tag: $TAG_NAME"
if git rev-parse "$TAG_NAME" >/dev/null 2>&1; then
    echo "✅ Tag '$TAG_NAME' exists"
    echo ""
    echo "Tag details:"
    git show "$TAG_NAME" --stat --oneline | head -40
    echo ""
    echo "Tag commit:"
    git log -1 "$TAG_NAME" --oneline
    echo ""
    
    # Check if working tree is clean
    if [ -z "$(git status --porcelain)" ]; then
        echo "✅ Working tree is clean"
        echo ""
        echo "============================================================"
        echo "✅ FREEZE COMPLETE - READY FOR STEP 2"
        echo "============================================================"
        echo ""
        echo "Next: Start Gamma-only test"
        echo ""
        echo "Option 1 (manual):"
        echo "  GAMMA_ONLY_TEST_MODE=true ./START_VALIDATION.sh"
        echo ""
        echo "Option 2 (helper script):"
        echo "  ./STEP_2_START_GAMMA_TEST.sh"
        echo ""
        echo "Watch logs for:"
        echo "  - 🔬 GAMMA_ONLY_TEST_MODE=true (env var: true)"
        echo "  - ✅ Created X agents (Gamma Scalper only)"
        echo "  - [GAMMA SCALP] entries"
        echo "  - [DeltaHedge] hedge trades"
        echo ""
        echo "After at least 1-2 complete Gamma packages, export timelines:"
        echo "  ./EXPORT_TIMELINES.sh"
        echo ""
    else
        echo "⚠️  Warning: Working tree has uncommitted changes"
        echo "   Freeze may not have completed fully"
        echo "   Run: git status"
    fi
else
    echo "❌ Tag '$TAG_NAME' not found"
    echo "   Freeze did not complete - please run ./FREEZE_AND_TAG.sh again"
    exit 1
fi

