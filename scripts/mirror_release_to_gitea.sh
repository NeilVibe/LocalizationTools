#!/bin/bash
# ============================================================================
# Mirror GitHub Release to Gitea
# ============================================================================
# Copies the latest GitHub release (installer + latest.yml) to Gitea
# for internal company distribution.
#
# Usage:
#   GITEA_TOKEN=your_token ./mirror_release_to_gitea.sh
#
# Requirements:
#   - curl
#   - jq
#   - GITEA_TOKEN environment variable
# ============================================================================

set -e

# Configuration
GITHUB_REPO="NeilVibe/LocalizationTools"
GITEA_URL="${GITEA_URL:-http://localhost:3000}"
GITEA_REPO="neilvibe/LocaNext"

# Check for token
if [ -z "$GITEA_TOKEN" ]; then
    echo "ERROR: GITEA_TOKEN environment variable not set"
    echo "Get token from: Gitea → User Settings → Applications → Generate Token"
    exit 1
fi

echo "=============================================="
echo "GitHub → Gitea Release Mirror"
echo "=============================================="
echo "GitHub: $GITHUB_REPO"
echo "Gitea:  $GITEA_URL/$GITEA_REPO"
echo ""

# Get latest GitHub release
echo "Fetching latest GitHub release..."
LATEST=$(curl -s "https://api.github.com/repos/${GITHUB_REPO}/releases/latest")

if [ -z "$LATEST" ] || [ "$LATEST" == "null" ]; then
    echo "ERROR: Could not fetch GitHub release"
    exit 1
fi

TAG=$(echo "$LATEST" | jq -r '.tag_name')
VERSION=$(echo "$LATEST" | jq -r '.name')
BODY=$(echo "$LATEST" | jq -r '.body')

echo "Latest release: $TAG ($VERSION)"

# Check if already exists in Gitea
EXISTING=$(curl -s "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/releases/tags/${TAG}" \
    -H "Authorization: token ${GITEA_TOKEN}" 2>/dev/null | jq -r '.id // empty')

if [ -n "$EXISTING" ]; then
    echo "Release $TAG already exists in Gitea (ID: $EXISTING)"
    echo "Skipping..."
    exit 0
fi

# Create temp directory
TEMP_DIR=$(mktemp -d)
echo "Temp directory: $TEMP_DIR"

# Download assets
echo ""
echo "Downloading assets..."

# Find .exe asset
EXE_URL=$(echo "$LATEST" | jq -r '.assets[] | select(.name | endswith(".exe")) | .browser_download_url' | head -1)
if [ -n "$EXE_URL" ]; then
    echo "  Downloading: $(basename "$EXE_URL")"
    curl -L -o "$TEMP_DIR/LocaNext-Setup.exe" "$EXE_URL"
fi

# Find latest.yml
YML_URL=$(echo "$LATEST" | jq -r '.assets[] | select(.name == "latest.yml") | .browser_download_url')
if [ -n "$YML_URL" ]; then
    echo "  Downloading: latest.yml"
    curl -L -o "$TEMP_DIR/latest.yml" "$YML_URL"
fi

# Create Gitea release
echo ""
echo "Creating Gitea release..."

RELEASE_BODY="Mirrored from GitHub release.

---

$BODY"

CREATE_RESPONSE=$(curl -s -X POST "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/releases" \
    -H "Authorization: token ${GITEA_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
        \"tag_name\": \"${TAG}\",
        \"name\": \"${VERSION}\",
        \"body\": $(echo "$RELEASE_BODY" | jq -Rs .),
        \"draft\": false,
        \"prerelease\": false
    }")

RELEASE_ID=$(echo "$CREATE_RESPONSE" | jq -r '.id')

if [ -z "$RELEASE_ID" ] || [ "$RELEASE_ID" == "null" ]; then
    echo "ERROR: Failed to create release"
    echo "$CREATE_RESPONSE"
    rm -rf "$TEMP_DIR"
    exit 1
fi

echo "Created release ID: $RELEASE_ID"

# Upload assets
echo ""
echo "Uploading assets..."

if [ -f "$TEMP_DIR/LocaNext-Setup.exe" ]; then
    echo "  Uploading: LocaNext-Setup.exe"
    curl -s -X POST "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/releases/${RELEASE_ID}/assets" \
        -H "Authorization: token ${GITEA_TOKEN}" \
        -F "attachment=@$TEMP_DIR/LocaNext-Setup.exe"
fi

if [ -f "$TEMP_DIR/latest.yml" ]; then
    echo "  Uploading: latest.yml"
    curl -s -X POST "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/releases/${RELEASE_ID}/assets" \
        -H "Authorization: token ${GITEA_TOKEN}" \
        -F "attachment=@$TEMP_DIR/latest.yml"
fi

# Cleanup
rm -rf "$TEMP_DIR"

echo ""
echo "=============================================="
echo "Release mirrored successfully!"
echo "View at: ${GITEA_URL}/${GITEA_REPO}/releases/tag/${TAG}"
echo "=============================================="
