# Testing Documentation Hub

**Last Updated**: 2025-12-03

Quick navigation for all testing docs.

---

## Quick Start

```bash
# Backend tests (no server needed)
python3 -m pytest tests/ -v

# Backend tests WITH server (TRUE simulation)
python3 server/main.py &
sleep 3
RUN_API_TESTS=1 python3 -m pytest -v

# Frontend tests (headless, fast)
cd locaNext && npm test        # 134 tests
cd adminDashboard && npm test  # 30 tests
```

---

## Documentation Tree

| Doc | Lines | Purpose |
|-----|-------|---------|
| [QUICK_COMMANDS.md](QUICK_COMMANDS.md) | ~50 | Copy-paste commands only |
| [PYTEST_GUIDE.md](PYTEST_GUIDE.md) | ~120 | Python backend testing |
| [PLAYWRIGHT_GUIDE.md](PLAYWRIGHT_GUIDE.md) | ~120 | Frontend E2E testing |
| [X_SERVER_SETUP.md](X_SERVER_SETUP.md) | ~60 | VcXsrv for visual testing |
| [TOOLS_REFERENCE.md](TOOLS_REFERENCE.md) | ~80 | xdotool, ffmpeg, etc. |

---

## Philosophy: Mathematical Proof Testing

Testing = Code verification, NOT visual inspection.

```
INPUT → PROCESS → OUTPUT → ASSERTION = PASS or FAIL
```

**What Claude sees:**
```
✓ should login successfully (245ms)
✓ should show error on invalid password (89ms)
39 passed (12.4s)
```

**This IS the proof!** No screenshots needed because:
- Assertions verify expected behavior
- Error messages explain failures
- Terminal output shows exact state

---

## Test Counts

| Domain | Tests | Tool |
|--------|-------|------|
| Backend Unit | 350+ | pytest |
| Backend E2E | 115 | pytest |
| API Simulation | 168 | pytest |
| Security | 86 | pytest |
| Frontend (LocaNext) | 134 | Playwright |
| Frontend (Dashboard) | 30 | Playwright |
| **Total** | **~1000+** | |

---

## When to Use What

| Task | Tool | Doc |
|------|------|-----|
| Test Python code | pytest | [PYTEST_GUIDE.md](PYTEST_GUIDE.md) |
| Test frontend UI | Playwright | [PLAYWRIGHT_GUIDE.md](PLAYWRIGHT_GUIDE.md) |
| Visual debugging | X Server + headed | [X_SERVER_SETUP.md](X_SERVER_SETUP.md) |
| Record demo video | ffmpeg | [TOOLS_REFERENCE.md](TOOLS_REFERENCE.md) |

---

**Screenshots are OPTIONAL** - only for:
- Showing humans what UI looks like
- Debugging visual bugs
- Creating demo videos
