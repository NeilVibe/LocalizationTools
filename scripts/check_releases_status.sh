#!/bin/bash
# ============================================================================
# Check Tags & Releases Status - GitHub and Gitea
# ============================================================================
# Shows current state of tags and releases on both platforms
# Usage: ./scripts/check_releases_status.sh
# ============================================================================

set -e

echo "=============================================="
echo "  TAGS & RELEASES STATUS CHECK"
echo "=============================================="
echo ""

# ---- LOCAL GIT ----
echo "=== LOCAL GIT ==="
LOCAL_TAGS=$(git tag -l | wc -l)
echo "Tags: $LOCAL_TAGS"
git tag -l | head -10
echo ""

# ---- GITHUB ----
echo "=== GITHUB ==="
if command -v gh &> /dev/null; then
    GH_RELEASES=$(gh release list --limit 100 2>/dev/null | wc -l || echo "0")
    GH_TAGS=$(gh api repos/:owner/:repo/tags --jq 'length' 2>/dev/null || echo "?")
    echo "Releases: $GH_RELEASES"
    echo "Tags: $GH_TAGS"
    echo ""
    echo "Latest releases:"
    gh release list --limit 5 2>/dev/null || echo "(no releases)"
else
    echo "gh CLI not installed - skipping GitHub check"
fi
echo ""

# ---- GITEA ----
echo "=== GITEA ==="
GITEA_URL="${GITEA_URL:-http://172.28.150.120:3000}"
GITEA_REPO="neilvibe/LocaNext"

if [ -n "$GITEA_TOKEN" ]; then
    GITEA_RELEASES=$(curl -s "$GITEA_URL/api/v1/repos/$GITEA_REPO/releases" \
        -H "Authorization: token $GITEA_TOKEN" | jq 'length' 2>/dev/null || echo "?")
    GITEA_TAGS=$(curl -s "$GITEA_URL/api/v1/repos/$GITEA_REPO/tags" \
        -H "Authorization: token $GITEA_TOKEN" | jq 'length' 2>/dev/null || echo "?")
    echo "Releases: $GITEA_RELEASES"
    echo "Tags: $GITEA_TAGS"
    echo ""
    echo "Latest releases:"
    curl -s "$GITEA_URL/api/v1/repos/$GITEA_REPO/releases?limit=5" \
        -H "Authorization: token $GITEA_TOKEN" | jq -r '.[] | "\(.tag_name)\t\(.name)"' 2>/dev/null || echo "(no releases)"
else
    echo "GITEA_TOKEN not set - skipping Gitea check"
    echo "Run: export GITEA_TOKEN=your_token"
fi
echo ""

echo "=============================================="
echo "  SYNC STATUS"
echo "=============================================="
echo "Tags should equal Releases on each platform"
echo ""
