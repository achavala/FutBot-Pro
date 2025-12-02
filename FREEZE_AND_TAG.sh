#!/usr/bin/env bash
# Freeze current state and create tag for Phase 1 validation

set -e

# Default tag name (can be overridden via command line)
TAG_NAME="${1:-v1.0.1-ml-gamma-qa}"
TAG_MESSAGE="${2:-Add production-safe gamma-only test infra}"

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

# Show tag info
echo "Tag name: $TAG_NAME"
echo "Tag message: $TAG_MESSAGE"
echo ""

# Show tag info
echo "Tag name: $TAG_NAME"
echo "Tag message: $TAG_MESSAGE"
echo ""

# Prompt for confirmation
read -p "Continue and commit/tag as ${TAG_NAME}? (y/N) " ans
if [[ "$ans" != "y" && "$ans" != "Y" ]]; then
    echo "❌ Aborting."
    exit 1
fi

# Check for uncommitted changes
if [ -z "$(git status --porcelain)" ]; then
    echo "✅ No uncommitted changes - repository is clean"
else
    echo "📝 Staging all changes..."
    git add -A
    
    echo "💾 Committing changes..."
    git commit -m "$TAG_MESSAGE"
    
    echo "✅ Changes committed"
fi

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

