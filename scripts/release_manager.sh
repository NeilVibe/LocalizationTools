#!/bin/bash
# =============================================================================
# Release Manager - Cleanup old releases and create mock releases for testing
# =============================================================================
#
# USAGE:
#   ./scripts/release_manager.sh <command> [options]
#
# COMMANDS:
#   list                    - List all releases
#   cleanup                 - Delete all releases except latest and current
#   mock-update             - Create a mock v99.999.9999 release for auto-update testing
#   restore                 - Remove mock release, restore normal
#
# SETUP:
#   Export GITEA_TOKEN first:
#   export GITEA_TOKEN="your_token_here"
#
#   Get your token from: http://172.28.150.120:3000/user/settings/applications
#   Create a new token with "write:repository" permission
# =============================================================================

set -e

GITEA_URL="${GITEA_URL:-http://172.28.150.120:3000}"
GITEA_REPO="neilvibe/LocaNext"
API_URL="$GITEA_URL/api/v1/repos/$GITEA_REPO"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${CYAN}[INFO]${NC} $1"; }
ok() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

check_token() {
    if [ -z "$GITEA_TOKEN" ]; then
        error "GITEA_TOKEN not set. Run: export GITEA_TOKEN=\"your_token\""
    fi
}

cmd_list() {
    log "Fetching releases from Gitea..."
    curl -s "$API_URL/releases" | python3 -c "
import sys, json
releases = json.load(sys.stdin)
print('=' * 60)
print('ID     TAG                  NAME')
print('=' * 60)
for r in releases:
    rid = str(r['id']).ljust(6)
    tag = r['tag_name'][:18].ljust(20)
    name = r['name'][:28].ljust(30)
    print(f'{rid} {tag} {name}')
print('=' * 60)
print(f'Total: {len(releases)} releases')
"
}

cmd_cleanup() {
    check_token
    log "Cleaning up old releases (keeping only 'latest' tag and most recent version)..."

    # Get all releases
    releases=$(curl -s "$API_URL/releases" -H "Authorization: token $GITEA_TOKEN")

    echo "$releases" | python3 -c "
import sys, json
releases = json.load(sys.stdin)

# Keep: 'latest' tag and the most recent version release
to_keep = set()
latest_version = None

for r in releases:
    if r['tag_name'] == 'latest':
        to_keep.add(r['id'])
        print(f\"[KEEP] {r['tag_name']}: {r['name']}\")

# Find most recent versioned release
versioned = [r for r in releases if r['tag_name'].startswith('v')]
if versioned:
    # Sort by tag (version) descending
    versioned.sort(key=lambda x: x['tag_name'], reverse=True)
    latest = versioned[0]
    to_keep.add(latest['id'])
    print(f\"[KEEP] {latest['tag_name']}: {latest['name']}\")

# List releases to delete
to_delete = [r for r in releases if r['id'] not in to_keep]
print(f'')
print(f'Releases to DELETE: {len(to_delete)}')
for r in to_delete:
    print(f\"[DELETE] {r['tag_name']}: {r['name']}\")

# Output IDs to delete
with open('/tmp/releases_to_delete.txt', 'w') as f:
    for r in to_delete:
        f.write(f\"{r['id']} {r['tag_name']}\n\")
"

    # Confirm and delete
    if [ -s /tmp/releases_to_delete.txt ]; then
        echo ""
        read -p "Delete these releases? (y/N) " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            while read -r id tag; do
                log "Deleting release $id ($tag)..."
                curl -s -X DELETE "$API_URL/releases/$id" -H "Authorization: token $GITEA_TOKEN"
                curl -s -X DELETE "$API_URL/tags/$tag" -H "Authorization: token $GITEA_TOKEN" 2>/dev/null || true
                ok "Deleted $tag"
            done < /tmp/releases_to_delete.txt
            ok "Cleanup complete!"
        else
            warn "Cancelled"
        fi
    else
        ok "Nothing to delete"
    fi
}

cmd_mock_update() {
    check_token
    log "Creating mock v99.999.9999 release for auto-update testing..."

    # Get current latest.yml content for file info
    current_yml=$(curl -s "$GITEA_URL/$GITEA_REPO/releases/download/latest/latest.yml")

    # Extract file info
    filename=$(echo "$current_yml" | grep -oP '(?<=url: ).*' | head -1)
    sha512=$(echo "$current_yml" | grep -oP '(?<=sha512: ).*' | head -1)
    size=$(echo "$current_yml" | grep -oP '(?<=size: ).*' | head -1)

    log "Using existing installer: $filename"

    # Create mock latest.yml with version 99.999.9999
    cat > /tmp/mock_latest.yml << EOF
version: 99.999.9999
files:
  - url: $filename
    sha512: $sha512
    size: $size
path: $filename
sha512: $sha512
releaseDate: '$(date -u +%Y-%m-%dT%H:%M:%S.000Z)'
EOF

    log "Mock latest.yml:"
    cat /tmp/mock_latest.yml

    # Get current 'latest' release ID and asset ID
    latest_release=$(curl -s "$API_URL/releases/tags/latest" -H "Authorization: token $GITEA_TOKEN")
    release_id=$(echo "$latest_release" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))")
    asset_id=$(echo "$latest_release" | python3 -c "
import sys, json
r = json.load(sys.stdin)
for a in r.get('assets', []):
    if a['name'] == 'latest.yml':
        print(a['id'])
        break
")

    log "Release ID: $release_id, Asset ID: $asset_id"

    # Delete old latest.yml
    if [ -n "$asset_id" ]; then
        log "Deleting old latest.yml..."
        curl -s -X DELETE "$API_URL/releases/$release_id/assets/$asset_id" \
            -H "Authorization: token $GITEA_TOKEN"
    fi

    # Upload mock latest.yml
    log "Uploading mock latest.yml..."
    curl -s -X POST "$API_URL/releases/$release_id/assets?name=latest.yml" \
        -H "Authorization: token $GITEA_TOKEN" \
        -H "Content-Type: application/octet-stream" \
        --data-binary @/tmp/mock_latest.yml

    ok "Mock release created! Server now reports v99.999.9999"
    echo ""
    log "Now launch LocaNext - it should detect an update available!"
    log "Run: node testing_toolkit/cdp/auto_update_test.js"
}

cmd_restore() {
    check_token
    log "Restoring normal latest.yml (removing mock)..."

    # Get current version from version.py
    version=$(grep -oP 'VERSION = "\K[^"]+' version.py)

    # Get file info from existing release
    latest_release=$(curl -s "$API_URL/releases/tags/latest" -H "Authorization: token $GITEA_TOKEN")

    # Extract installer info
    installer_info=$(echo "$latest_release" | python3 -c "
import sys, json
r = json.load(sys.stdin)
for a in r.get('assets', []):
    if a['name'].endswith('.exe') and 'blockmap' not in a['name']:
        print(f\"{a['name']}|{a['size']}\")
        break
")

    filename=$(echo "$installer_info" | cut -d'|' -f1)
    size=$(echo "$installer_info" | cut -d'|' -f2)

    # We need the sha512 from the blockmap or recalculate
    # For now, get from existing versioned release
    versioned_yml=$(curl -s "$GITEA_URL/$GITEA_REPO/releases/download/v$version/latest.yml" 2>/dev/null || echo "")

    if [ -z "$versioned_yml" ]; then
        error "Cannot find versioned release to get sha512. Please trigger a new build."
    fi

    sha512=$(echo "$versioned_yml" | grep -oP '(?<=sha512: ).*' | head -1)

    # Create proper latest.yml
    cat > /tmp/real_latest.yml << EOF
version: $version
files:
  - url: $filename
    sha512: $sha512
    size: $size
path: $filename
sha512: $sha512
releaseDate: '$(date -u +%Y-%m-%dT%H:%M:%S.000Z)'
EOF

    log "Restored latest.yml:"
    cat /tmp/real_latest.yml

    # Get release and asset IDs
    release_id=$(echo "$latest_release" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))")
    asset_id=$(echo "$latest_release" | python3 -c "
import sys, json
r = json.load(sys.stdin)
for a in r.get('assets', []):
    if a['name'] == 'latest.yml':
        print(a['id'])
        break
")

    # Delete mock and upload real
    if [ -n "$asset_id" ]; then
        curl -s -X DELETE "$API_URL/releases/$release_id/assets/$asset_id" \
            -H "Authorization: token $GITEA_TOKEN"
    fi

    curl -s -X POST "$API_URL/releases/$release_id/assets?name=latest.yml" \
        -H "Authorization: token $GITEA_TOKEN" \
        -H "Content-Type: application/octet-stream" \
        --data-binary @/tmp/real_latest.yml

    ok "Restored to v$version"
}

# Main
case "${1:-}" in
    list)
        cmd_list
        ;;
    cleanup)
        cmd_cleanup
        ;;
    mock-update)
        cmd_mock_update
        ;;
    restore)
        cmd_restore
        ;;
    *)
        echo "Usage: $0 <command>"
        echo ""
        echo "Commands:"
        echo "  list        - List all releases"
        echo "  cleanup     - Delete old releases (keeps latest + current version)"
        echo "  mock-update - Create mock v99.999.9999 for testing auto-update"
        echo "  restore     - Remove mock, restore real version"
        echo ""
        echo "Setup:"
        echo "  export GITEA_TOKEN=\"your_token\""
        echo "  Get token from: http://172.28.150.120:3000/user/settings/applications"
        ;;
esac
