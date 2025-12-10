# Testing & Documentation Improvements WIP

**Purpose:** Track improvements needed for testing suite organization and documentation structure
**Priority:** Low (background work)
**Created:** 2025-12-11

---

## Overview

User feedback from 2025-12-11 session identified several areas for improvement in testing and documentation organization.

---

## Tasks

### 1. Testing Suite Organization
- [ ] Add category folders to testing_toolkit (e.g., cdp/, api/, integration/)
- [ ] Group LDM tests in separate folder
- [ ] Clean up ad-hoc test scripts from Windows project folder
- [ ] Ensure all test scripts saved in project repo

### 2. TEST HUB Documentation
- [ ] Create `testing_toolkit/TEST_HUB.md` as central index
- [ ] Document each test category with examples
- [ ] Add CDP test injection examples
- [ ] Document autonomous testing workflow

### 3. WIP Archive System
- [ ] Create `docs/wip/archive/` folder for completed WIP docs
- [ ] Move completed WIP docs (P21, P20, P13) to archive
- [ ] Update WIP README.md with archive section

### 4. /tmp Cleanup Protocol
- [ ] Document temp file usage in testing
- [ ] Add cleanup step to test scripts
- [ ] Check Windows build temp artifacts

---

## Current Testing Structure

```
testing_toolkit/
├── README.md               # Main readme
├── ADD_TEST_MODE_GUIDE.md  # How to add test mode to apps
├── TEST_FILES_MANIFEST.md  # Test files listing
├── scripts/
│   ├── run_test.js         # Single test runner
│   ├── run_all_tests.js    # Full suite runner
│   ├── test_ldm_full.js    # LDM comprehensive test
│   └── *.js                # Utility scripts
└── setup/
    ├── launch_and_test.sh  # Autonomous test launcher
    └── check_prerequisites.sh
```

## Proposed Structure

```
testing_toolkit/
├── README.md               # TEST HUB (main index)
├── ADD_TEST_MODE_GUIDE.md
├── TEST_FILES_MANIFEST.md
├── scripts/
│   ├── core/               # Core test infrastructure
│   │   ├── run_test.js
│   │   └── run_all_tests.js
│   ├── ldm/                # LDM-specific tests
│   │   └── test_ldm_full.js
│   ├── api/                # Backend API tests
│   └── cdp/                # CDP/Electron tests
└── setup/
    └── *.sh
```

---

## Notes

- Testing infrastructure is functional but could be better organized
- Priority is low - current setup works fine
- Address when doing major testing work

---

*Created: 2025-12-11 | Status: BACKLOG*
