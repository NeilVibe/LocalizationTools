# Testing Documentation

**Updated:** 2025-12-19 | **Build:** 300

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
| [DEBUG_AND_TEST_HUB.md](DEBUG_AND_TEST_HUB.md) | Multi-environment testing, Playwright, backend |
| [PYTEST_GUIDE.md](PYTEST_GUIDE.md) | Python backend tests |
| [PLAYWRIGHT_GUIDE.md](PLAYWRIGHT_GUIDE.md) | Frontend E2E (dev server) |
| [PLAYGROUND_INSTALL_PROTOCOL.md](PLAYGROUND_INSTALL_PROTOCOL.md) | Playground setup |

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
