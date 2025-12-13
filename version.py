"""
LocaNext Version Configuration
Single source of truth for version across entire project

Based on VRS-Manager version management pattern
FACTORIZED: Single version format for ALL uses (datetime + semver)
"""

# UNIFIED VERSION FORMAT: YY.MMDD.HHMM
# - Valid semver: 25.1213.1540 = X.Y.Z
# - Human readable: Dec 13, 2025, 15:40 KST
# - Auto-increments with time
# - Works everywhere: electron, CI, installer, UI
VERSION = "25.1213.1540"

# Version footer for UI display
VERSION_FOOTER = f"ver. {VERSION} | AI-Powered Localization Platform | XLSTransfer + QuickSearch"

# DEPRECATED: No longer needed - VERSION is now semver-compatible
# Kept for backwards compatibility during transition
SEMANTIC_VERSION = VERSION  # Same as VERSION now!

# Build type
BUILD_TYPE = "LIGHT"  # FULL (with AI model) or LIGHT (without AI)

# Release info
RELEASE_DATE = "2025-12-13"
RELEASE_NAME = "P25 TM/QA Core Backend + Integration Tests"

# Repository info
REPOSITORY_URL = "https://github.com/NeilVibe/LocalizationTools"
ISSUES_URL = f"{REPOSITORY_URL}/issues"

if __name__ == "__main__":
    print("LocaNext Version Information")
    print("=" * 50)
    print(f"Version: {VERSION}")
    print(f"Semantic: {SEMANTIC_VERSION}")
    print(f"Build Type: {BUILD_TYPE}")
    print(f"Release: {RELEASE_NAME} ({RELEASE_DATE})")
    print(f"Footer: {VERSION_FOOTER}")
    print(f"Repository: {REPOSITORY_URL}")
