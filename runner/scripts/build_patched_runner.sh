#!/bin/bash
# Build Patched act_runner with NUL Byte Fix (v15)
#
# This script:
# 1. Clones the official act and act_runner repositories
# 2. Applies our NUL byte fix patch
# 3. Builds the patched runner for Windows
#
# Requirements:
# - Go 1.21+ installed
# - git installed
# - Internet access (to clone repos)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_DIR="$(dirname "$SCRIPT_DIR")"
PATCH_FILE="$RUNNER_DIR/patches/v15_nul_byte_fix.patch"
BUILD_DIR="${BUILD_DIR:-$HOME/act_runner_build}"

echo "=============================================="
echo "  Building Patched act_runner (v15 NUL Fix)"
echo "=============================================="

# Check requirements
command -v go >/dev/null 2>&1 || { echo "ERROR: Go is not installed"; exit 1; }
command -v git >/dev/null 2>&1 || { echo "ERROR: git is not installed"; exit 1; }

echo ""
echo "Go version: $(go version)"
echo "Build directory: $BUILD_DIR"
echo ""

# Create build directory
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Clone repositories (if not already cloned)
if [ ! -d "act" ]; then
    echo "[1/5] Cloning nektos/act..."
    git clone --depth 1 https://github.com/nektos/act.git
else
    echo "[1/5] act repo already exists, pulling latest..."
    cd act && git pull && cd ..
fi

if [ ! -d "act_runner" ]; then
    echo "[2/5] Cloning gitea/act_runner..."
    git clone --depth 1 https://gitea.com/gitea/act_runner.git
else
    echo "[2/5] act_runner repo already exists, pulling latest..."
    cd act_runner && git pull && cd ..
fi

# Apply patch
echo "[3/5] Applying NUL byte fix patch..."
cd act
if ! grep -q "V15-PATCH" pkg/container/parse_env_file.go 2>/dev/null; then
    patch -p1 < "$PATCH_FILE"
    echo "      Patch applied successfully"
else
    echo "      Patch already applied, skipping"
fi
cd ..

# Configure act_runner to use local act
echo "[4/5] Configuring act_runner to use patched act..."
cd act_runner
if ! grep -q "replace github.com/nektos/act" go.mod; then
    echo 'replace github.com/nektos/act => ../act' >> go.mod
fi
go mod tidy

# Build for Windows
echo "[5/5] Building for Windows (amd64)..."
GOOS=windows GOARCH=amd64 go build -o act_runner_patched_v15.exe

echo ""
echo "=============================================="
echo "  BUILD COMPLETE!"
echo "=============================================="
echo ""
echo "Output: $BUILD_DIR/act_runner/act_runner_patched_v15.exe"
echo ""
echo "To deploy to Windows:"
echo "  cp act_runner_patched_v15.exe /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/GiteaRunner/"
echo ""
echo "Then on Windows, restart the service:"
echo "  Restart-Service GiteaActRunner"
echo ""
