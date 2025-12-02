#!/bin/bash
# Verify freeze completed successfully

echo "============================================================"
echo "VERIFYING FREEZE & TAG"
echo "============================================================"
echo ""

# Check git status
echo "📊 Git status:"
git status --short
echo ""

# Check if tag exists
TAG_NAME="v1.0.1-ml-gamma-qa"
if git rev-parse "$TAG_NAME" >/dev/null 2>&1; then
    echo "✅ Tag '$TAG_NAME' exists"
    echo ""
    echo "Tag details:"
    git show "$TAG_NAME" --stat --oneline | head -30
    echo ""
    echo "Tag commit:"
    git log -1 "$TAG_NAME" --oneline
else
    echo "❌ Tag '$TAG_NAME' not found"
    echo "   Freeze may not have completed"
fi

echo ""
echo "============================================================"

