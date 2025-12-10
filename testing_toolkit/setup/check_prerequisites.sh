#!/bin/bash
# ============================================================================
# LocaNext Testing Toolkit - Prerequisites Check
# ============================================================================
# Checks all requirements for autonomous testing

echo "=============================================="
echo "LocaNext Testing Toolkit - Prerequisites Check"
echo "=============================================="
echo ""

ERRORS=0

# Check Node.js
echo -n "[CHECK] Node.js: "
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo "OK ($NODE_VERSION)"
else
    echo "MISSING"
    echo "  -> Install Node.js from https://nodejs.org"
    ((ERRORS++))
fi

# Check npm
echo -n "[CHECK] npm: "
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo "OK (v$NPM_VERSION)"
else
    echo "MISSING"
    ((ERRORS++))
fi

# Check ws module
echo -n "[CHECK] ws module: "
if node -e "require('ws')" 2>/dev/null; then
    echo "OK"
else
    echo "MISSING"
    echo "  -> Run: npm install ws"
    ((ERRORS++))
fi

# Check test files directory (Windows path)
echo -n "[CHECK] Test files (C:\\NEIL_PROJECTS_WINDOWSBUILD\\LocaNextProject\\TestFilesForLocaNext\\): "
if [ -d "/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/TestFilesForLocaNext" ]; then
    FILE_COUNT=$(ls -1 /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/TestFilesForLocaNext/ 2>/dev/null | wc -l)
    echo "OK ($FILE_COUNT files)"
else
    echo "MISSING"
    echo "  -> Create C:\\NEIL_PROJECTS_WINDOWSBUILD\\LocaNextProject\\TestFilesForLocaNext\\ with test files"
    ((ERRORS++))
fi

# Check specific test files
echo ""
echo "Test Files:"
TEST_FILES_DIR="/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/TestFilesForLocaNext"
for FILE in "GlossaryUploadTestFile.xlsx" "translationTEST.xlsx"; do
    echo -n "  [CHECK] $FILE: "
    if [ -f "$TEST_FILES_DIR/$FILE" ]; then
        SIZE=$(du -h "$TEST_FILES_DIR/$FILE" 2>/dev/null | cut -f1)
        echo "OK ($SIZE)"
    else
        echo "MISSING"
        ((ERRORS++))
    fi
done

# Check LocaNext installation
echo ""
LOCANEXT_DIR="/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext"
echo -n "[CHECK] LocaNext ($LOCANEXT_DIR): "
if [ -d "$LOCANEXT_DIR" ]; then
    if [ -f "$LOCANEXT_DIR/LocaNext.exe" ]; then
        echo "OK"
    else
        echo "MISSING (no LocaNext.exe)"
        ((ERRORS++))
    fi
else
    echo "MISSING"
    echo "  -> Install LocaNext to C:\\NEIL_PROJECTS_WINDOWSBUILD\\LocaNextProject\\LocaNext\\"
    ((ERRORS++))
fi

# Check PowerShell access
echo -n "[CHECK] PowerShell (from WSL): "
if [ -x "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe" ]; then
    echo "OK"
else
    echo "MISSING or not accessible"
    ((ERRORS++))
fi

# Summary
echo ""
echo "=============================================="
if [ $ERRORS -eq 0 ]; then
    echo "All prerequisites OK!"
    echo "Ready for autonomous testing."
    exit 0
else
    echo "ERRORS: $ERRORS"
    echo "Fix the issues above before testing."
    exit 1
fi
