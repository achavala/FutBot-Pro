#!/usr/bin/env bash
# Freeze current state and create tag for Phase 1 validation

set -e

TAG_NAME="v1.0.0-ml-multi-leg"

echo "============================================================"
echo "FREEZING CURRENT STATE FOR PHASE 1 VALIDATION"
echo "============================================================"
echo ""

# Check if we're in a git repo
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

# Show current git status
echo "📊 Current git status:"
git status --short
echo ""

# Check for untracked files that might be junk
UNTRACKED=$(git status --porcelain | grep "^??" | wc -l)
if [ "$UNTRACKED" -gt 0 ]; then
    echo "⚠️  Warning: $UNTRACKED untracked files found"
    echo "   Review them before committing"
    echo ""
fi

# Prompt for confirmation
read -p "Continue and commit/tag as ${TAG_NAME}? (y/N) " ans
if [[ "$ans" != "y" && "$ans" != "Y" ]]; then
    echo "Aborting."
    exit 1
fi

# Check for uncommitted changes
if [ -z "$(git status --porcelain)" ]; then
    echo "✅ No uncommitted changes - repository is clean"
else
    echo "📝 Staging all changes..."
    git add -A
    
    echo "💾 Committing changes..."
    git commit -m "feat: Multi-leg execution system ready for Phase 1 validation

- Multi-leg execution (two orders per leg)
- Fill tracking (independent per leg)
- Combined P&L calculation
- Credit/debit verification
- Package-level closing
- Auto-exit logic (TP/SL/IV/GEX/Regime)
- UI integration (positions + history tables)
- API endpoints (/options/positions, /trades/options/multi-leg)
- Unit tests (all passing)
- API tests (all working)
- Documentation (validation checklist, exit criteria, roadmap)

Ready for Phase 1: Simulation Validation"
    
    echo "✅ Changes committed"
fi

# Create tag
TAG_MESSAGE="Multi-leg engine ready for Phase 1 validation

This tag marks the completion of the multi-leg options execution system:
- Theta Harvester (straddle seller) ready
- Gamma Scalper (strangle buyer) ready
- All core functionality implemented and tested
- Ready for Phase 1 simulation validation

Next: Run Phase 1 validation checklist"

echo ""
echo "🏷️  Creating tag: $TAG_NAME"
git tag -a "$TAG_NAME" -m "$TAG_MESSAGE"

echo ""
echo "✅ Tag created successfully"
echo ""
echo "📋 Next steps:"
echo "   1. Review the tag: git show $TAG_NAME"
echo "   2. Push commits: git push"
echo "   3. Push tags: git push --tags"
echo "   4. Start Phase 1: ./START_VALIDATION.sh"
echo ""
echo "============================================================"

