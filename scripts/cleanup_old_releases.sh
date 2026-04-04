#!/bin/bash
# ============================================================================
# Cleanup Old Gitea Releases
# ============================================================================
# Keeps only the latest N releases, deletes older ones.
# Saves disk space while maintaining update history.
#
# Usage:
#   GITEA_TOKEN=your_token ./cleanup_old_releases.sh
#   GITEA_TOKEN=your_token KEEP_COUNT=3 ./cleanup_old_releases.sh
#
# ============================================================================

set -e

# Configuration
GITEA_URL="${GITEA_URL:-http://localhost:3000}"
GITEA_REPO="neilvibe/LocaNext"
KEEP_COUNT="${KEEP_COUNT:-2}"

# Check for token
if [ -z "$GITEA_TOKEN" ]; then
    echo "ERROR: GITEA_TOKEN environment variable not set"
    exit 1
fi

echo "=============================================="
echo "Gitea Release Cleanup"
echo "=============================================="
echo "Repo: $GITEA_URL/$GITEA_REPO"
echo "Keep: $KEEP_COUNT latest releases"
echo ""

# Get all releases
echo "Fetching releases..."
RELEASES=$(curl -s "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/releases" \
    -H "Authorization: token ${GITEA_TOKEN}")

# Count releases
TOTAL=$(echo "$RELEASES" | jq 'length')
echo "Total releases: $TOTAL"

if [ "$TOTAL" -le "$KEEP_COUNT" ]; then
    echo "No cleanup needed (have $TOTAL, keeping $KEEP_COUNT)"
    exit 0
fi

# Get release IDs and names, sorted by created_at descending
echo ""
echo "Releases:"
echo "$RELEASES" | jq -r '.[] | "\(.id)\t\(.tag_name)\t\(.created_at)"' | head -20

# Get IDs to delete (skip first KEEP_COUNT)
TO_DELETE=$(echo "$RELEASES" | jq -r ".[${KEEP_COUNT}:] | .[].id")

if [ -z "$TO_DELETE" ]; then
    echo "No releases to delete"
    exit 0
fi

echo ""
echo "Deleting old releases..."

for RELEASE_ID in $TO_DELETE; do
    # Get release name for logging
    NAME=$(echo "$RELEASES" | jq -r ".[] | select(.id == $RELEASE_ID) | .tag_name")
    echo "  Deleting: $NAME (ID: $RELEASE_ID)"

    curl -s -X DELETE "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/releases/${RELEASE_ID}" \
        -H "Authorization: token ${GITEA_TOKEN}"
done

# Count remaining
REMAINING=$(curl -s "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/releases" \
    -H "Authorization: token ${GITEA_TOKEN}" | jq 'length')

echo ""
echo "=============================================="
echo "Cleanup complete!"
echo "Deleted: $((TOTAL - REMAINING)) releases"
echo "Remaining: $REMAINING releases"
echo "=============================================="
