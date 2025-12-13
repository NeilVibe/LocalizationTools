"""
LocaNext Version Configuration
Single source of truth for version across entire project

Based on VRS-Manager version management pattern
"""

# Version in DateTime format: YYMMDDHHMM
# Example: 2511221939 = November 22, 2025, 19:39
VERSION = "2512131330"

# Version footer for UI display
VERSION_FOOTER = f"ver. {VERSION} | AI-Powered Localization Platform | XLSTransfer + QuickSearch"

# Semantic version for package managers
SEMANTIC_VERSION = "1.4.0"

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
