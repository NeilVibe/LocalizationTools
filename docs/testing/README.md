# Testing Documentation

**Updated:** 2025-12-21 | **Build:** 312 (VERIFIED)

---

## AI Visual Verification Protocol (NEW)

**CRITICAL:** All UI/UX fixes MUST be verified with screenshot proof.

**Full Protocol:** [testing_toolkit/MASTER_TEST_PROTOCOL.md - Phase 6](../../testing_toolkit/MASTER_TEST_PROTOCOL.md#phase-6-ai-visual-verification-protocol)

### Quick Summary

```
1. Take screenshot via CDP
2. Read image (Claude can analyze PNGs)
3. Verify fix is visible
4. Don't mark VERIFIED until screenshot proves it
```

### AI State of Mind

| Principle | Meaning |
|-----------|---------|
| **Be skeptical** | Code changes ≠ working UI |
| **Be visual** | Screenshots reveal user experience |
| **Be thorough** | Test edge cases |
| **Be precise** | Document exactly what changed |
| **Be demanding** | Require proof before marking VERIFIED |

### Svelte 5 UIUX Testing

- **Auto-adaptive UI** - percentage widths, not hardcoded pixels
- **`$state()` reactivity** - verify UI updates when state changes
- **Clear separators** - visible borders between columns
- **No clutter** - remove pagination, footers, useless elements

---

## Primary Testing Method: Node.js CDP

For testing the Windows LocaNext.exe app, use **pure Node.js CDP scripts**.

**Main Guide:** [testing_toolkit/cdp/README.md](../../testing_toolkit/cdp/README.md)

```bash
# Quick start
cd testing_toolkit/cdp
node test_bug029.js
```

---

## Documentation

| Doc | Purpose |
|-----|---------|
| **[testing_toolkit/cdp/README.md](../../testing_toolkit/cdp/README.md)** | CDP testing (Windows app) - **START HERE** |
| [testing_toolkit/BUILD_TEST_PROTOCOL.md](../../testing_toolkit/BUILD_TEST_PROTOCOL.md) | Build → Test workflow |
| [PLAYGROUND_INSTALL_PROTOCOL.md](PLAYGROUND_INSTALL_PROTOCOL.md) | Detailed Playground install |
| [DEBUG_AND_TEST_HUB.md](DEBUG_AND_TEST_HUB.md) | Multi-environment quick reference |
| [PYTEST_GUIDE.md](PYTEST_GUIDE.md) | Python backend tests |
| [PLAYWRIGHT_GUIDE.md](PLAYWRIGHT_GUIDE.md) | Frontend E2E (dev server) |

---

## Test Toolkit

```
testing_toolkit/cdp/
├── README.md ──────────── Main CDP guide (Node.js)
├── quick_check.js ─────── Page state check
├── test_bug023.js ─────── TM status test
├── test_bug029.js ─────── Upload as TM test
├── test_clean_slate.js ── Clear TMs test
└── test_server_status.js ─ Server status test
```

---

## Quick Commands

### CDP Test (Windows App)
```bash
# From WSL or Windows
cd testing_toolkit/cdp
node test_bug029.js
```

### Backend Tests
```bash
python3 -m pytest tests/unit/ tests/integration/ -v
```

### Frontend Tests (Dev Server)
```bash
cd locaNext && npm test
```

---

## Test Counts

| Category | Tests | Tool |
|----------|-------|------|
| Backend | 630+ | pytest |
| Frontend | 164 | Playwright |
| CDP (Windows) | 15 | Node.js |
| **Total** | **~800+** | |

---

*Last updated: 2025-12-19*
