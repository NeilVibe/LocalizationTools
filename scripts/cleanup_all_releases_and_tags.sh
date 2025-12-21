#!/bin/bash
# ============================================================================
# Nuclear Cleanup: Delete ALL Tags and Releases
# ============================================================================
# Cleans both GitHub and Gitea to start fresh.
# Next build will create new release with matching tag.
#
# Usage:
#   ./scripts/cleanup_all_releases_and_tags.sh          # Dry run (show what would be deleted)
#   ./scripts/cleanup_all_releases_and_tags.sh --force  # Actually delete
#
# Requirements:
#   - gh CLI installed and authenticated
#   - GITEA_TOKEN environment variable set
# ============================================================================

set -e

FORCE=false
if [ "$1" == "--force" ]; then
    FORCE=true
fi

echo "=============================================="
echo "  NUCLEAR CLEANUP: ALL TAGS & RELEASES"
echo "=============================================="
if [ "$FORCE" == "false" ]; then
    echo "  MODE: DRY RUN (use --force to delete)"
else
    echo "  MODE: FORCE DELETE"
fi
echo "=============================================="
echo ""

# ============================================================================
# GITHUB CLEANUP
# ============================================================================
echo "=== GITHUB ==="

if ! command -v gh &> /dev/null; then
    echo "[SKIP] gh CLI not installed"
else
    # Delete all GitHub releases
    echo "Fetching GitHub releases..."
    GH_RELEASES=$(gh release list --limit 100 --json tagName -q '.[].tagName' 2>/dev/null || echo "")

    if [ -z "$GH_RELEASES" ]; then
        echo "No GitHub releases found"
    else
        RELEASE_COUNT=$(echo "$GH_RELEASES" | wc -l)
        echo "Found $RELEASE_COUNT releases to delete"

        for TAG in $GH_RELEASES; do
            if [ "$FORCE" == "true" ]; then
                echo "  Deleting release: $TAG"
                gh release delete "$TAG" --yes 2>/dev/null || true
            else
                echo "  [DRY RUN] Would delete release: $TAG"
            fi
        done
    fi

    # Delete all GitHub tags
    echo ""
    echo "Fetching GitHub tags..."
    GH_TAGS=$(gh api repos/:owner/:repo/tags --jq '.[].name' 2>/dev/null || echo "")

    if [ -z "$GH_TAGS" ]; then
        echo "No GitHub tags found"
    else
        TAG_COUNT=$(echo "$GH_TAGS" | wc -l)
        echo "Found $TAG_COUNT tags to delete"

        for TAG in $GH_TAGS; do
            if [ "$FORCE" == "true" ]; then
                echo "  Deleting tag: $TAG"
                gh api -X DELETE "repos/:owner/:repo/git/refs/tags/$TAG" 2>/dev/null || true
            else
                echo "  [DRY RUN] Would delete tag: $TAG"
            fi
        done
    fi
fi

echo ""

# ============================================================================
# GITEA CLEANUP
# ============================================================================
echo "=== GITEA ==="

GITEA_URL="${GITEA_URL:-http://172.28.150.120:3000}"
GITEA_REPO="neilvibe/LocaNext"

if [ -z "$GITEA_TOKEN" ]; then
    echo "[SKIP] GITEA_TOKEN not set"
else
    # Delete all Gitea releases
    echo "Fetching Gitea releases..."
    GITEA_RELEASES=$(curl -s "$GITEA_URL/api/v1/repos/$GITEA_REPO/releases" \
        -H "Authorization: token $GITEA_TOKEN" | jq -r '.[].id' 2>/dev/null || echo "")

    if [ -z "$GITEA_RELEASES" ]; then
        echo "No Gitea releases found"
    else
        RELEASE_COUNT=$(echo "$GITEA_RELEASES" | wc -w)
        echo "Found $RELEASE_COUNT releases to delete"

        for ID in $GITEA_RELEASES; do
            # Get tag name for logging
            TAG=$(curl -s "$GITEA_URL/api/v1/repos/$GITEA_REPO/releases/$ID" \
                -H "Authorization: token $GITEA_TOKEN" | jq -r '.tag_name' 2>/dev/null || echo "unknown")

            if [ "$FORCE" == "true" ]; then
                echo "  Deleting release: $TAG (ID: $ID)"
                curl -s -X DELETE "$GITEA_URL/api/v1/repos/$GITEA_REPO/releases/$ID" \
                    -H "Authorization: token $GITEA_TOKEN" > /dev/null
            else
                echo "  [DRY RUN] Would delete release: $TAG (ID: $ID)"
            fi
        done
    fi

    # Delete all Gitea tags
    echo ""
    echo "Fetching Gitea tags..."
    GITEA_TAGS=$(curl -s "$GITEA_URL/api/v1/repos/$GITEA_REPO/tags" \
        -H "Authorization: token $GITEA_TOKEN" | jq -r '.[].name' 2>/dev/null || echo "")

    if [ -z "$GITEA_TAGS" ]; then
        echo "No Gitea tags found"
    else
        TAG_COUNT=$(echo "$GITEA_TAGS" | wc -w)
        echo "Found $TAG_COUNT tags to delete"

        for TAG in $GITEA_TAGS; do
            if [ "$FORCE" == "true" ]; then
                echo "  Deleting tag: $TAG"
                curl -s -X DELETE "$GITEA_URL/api/v1/repos/$GITEA_REPO/tags/$TAG" \
                    -H "Authorization: token $GITEA_TOKEN" > /dev/null
            else
                echo "  [DRY RUN] Would delete tag: $TAG"
            fi
        done
    fi
fi

echo ""

# ============================================================================
# LOCAL TAGS CLEANUP
# ============================================================================
echo "=== LOCAL GIT TAGS ==="

LOCAL_TAGS=$(git tag -l)

if [ -z "$LOCAL_TAGS" ]; then
    echo "No local tags found"
else
    TAG_COUNT=$(echo "$LOCAL_TAGS" | wc -l)
    echo "Found $TAG_COUNT local tags to delete"

    for TAG in $LOCAL_TAGS; do
        if [ "$FORCE" == "true" ]; then
            echo "  Deleting local tag: $TAG"
            git tag -d "$TAG" 2>/dev/null || true
        else
            echo "  [DRY RUN] Would delete local tag: $TAG"
        fi
    done
fi

echo ""
echo "=============================================="
if [ "$FORCE" == "true" ]; then
    echo "  CLEANUP COMPLETE"
    echo "  Next build will create fresh release + tag"
else
    echo "  DRY RUN COMPLETE"
    echo "  Run with --force to actually delete"
fi
echo "=============================================="
