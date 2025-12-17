# Testing & Debugging Documentation Hub

**Last Updated**: 2025-12-17 | **Build:** 298

---

## 🤖 CLAUDE AI: AUTONOMOUS TESTING MODE

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                    CLAUDE WORKS ALONE ON TESTING                          ║
║                                                                           ║
║  ✅ Claude can: test, monitor, fix, troubleshoot, rebuild, redeploy      ║
║  ❌ Claude does NOT need user for any testing/debugging tasks            ║
║                                                                           ║
║  User Role: Direction & Design ONLY                                       ║
║  Claude Role: Execute ALL testing autonomously                            ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

**When encountering issues, Claude should:**
1. Read logs first
2. Debug with available tools
3. Fix the issue
4. Retest
5. Only ask user if architecture decision needed

**Windows Test Folder:** `D:\LocaNext` (WSL: `/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext`)

---

## 🗺️ START HERE → [DEBUG_AND_TEST_HUB.md](DEBUG_AND_TEST_HUB.md)

The **Debug & Test Hub** contains the complete tree of ALL capabilities for:
- Remote access to Windows EXE (CDP)
- Backend testing (pytest)
- Frontend testing (Playwright)
- Real-time monitoring (WebSocket, logs)
- Telemetry testing
- Visual debugging (X Server)

---

## 📚 Documentation Tree

```
docs/testing/
│
├── 🎯 DEBUG_AND_TEST_HUB.md ──── MASTER GUIDE (Start Here!)
│   └── Complete capabilities tree
│   └── All methods documented
│   └── Quick reference commands
│
├── 📡 CDP_TESTING_GUIDE.md ──── Chrome DevTools Protocol
│   └── ⚠️ Critical: WSL2 can't access Windows localhost:9222
│   └── Must run tests on Windows side via PowerShell
│
├── 🖥️ PLAYGROUND_INSTALL_PROTOCOL.md ── Playground setup
│   └── Fresh install, auto-login, CDP enable
│
├── 🤖 AUTONOMOUS_WINDOWS_TESTING.md ── CDP + TEST MODE
│   └── Skips file dialogs automatically
│   └── window.xlsTransferTest functions
│
├── ⚡ QUICK_COMMANDS.md ────────── Copy-paste commands only
│
├── 🐍 PYTEST_GUIDE.md ─────────── Python backend testing
│   └── Fixtures, patterns, TRUE simulation
│
├── 🌐 PLAYWRIGHT_GUIDE.md ─────── Frontend E2E testing
│   └── Browser automation, selectors
│
├── 🖼️ X_SERVER_SETUP.md ──────── Visual testing from WSL
│   └── VcXsrv setup, DISPLAY export
│
└── 🛠️ TOOLS_REFERENCE.md ──────── xdotool, ffmpeg, scrot
```

**CDP Testing Toolkit** (`testing_toolkit/cdp/`):
```
testing_toolkit/cdp/
├── README.md ──────────────── Hub with selectors, navigation map
├── utils/cdp-client.js ───── Reusable CDP client
└── tests/
    ├── login/ ────────────── Login automation
    ├── navigation/ ───────── Page state checks
    └── tm-viewer/ ────────── TM Viewer & Confirm tests
```

**Related Docs (outside testing/):**
- `WINDOWS_TROUBLESHOOTING.md` - CDP, Electron logs, remote debugging
- `ELECTRON_TROUBLESHOOTING.md` - Black screen, preload issues
- `MONITORING_COMPLETE_GUIDE.md` - Log monitoring system

---

## ⚡ Quick Start (3 Commands)

```bash
# 1. Start server
python3 server/main.py &

# 2. Wait + run tests
sleep 5 && RUN_API_TESTS=1 python3 -m pytest -v

# 3. Frontend tests
cd locaNext && npm test
```

---

## 🧪 Test Counts Summary

| Domain | Tests | Tool |
|--------|-------|------|
| Backend (Unit + E2E + API) | 630+ | pytest |
| Security | 86 | pytest |
| Telemetry (P12.5) | 10 | pytest |
| Frontend (LocaNext + Dashboard) | 164 | Playwright |
| CDP (Windows EXE) | 15 | Node.js |
| **Total** | **~1000+** | |

---

## 🔑 Philosophy: Mathematical Proof Testing

```
INPUT → PROCESS → OUTPUT → ASSERTION = PASS or FAIL
```

**What Claude sees:**
```
✓ should login successfully (245ms)
✓ should show error on invalid password (89ms)
39 passed (12.4s)
```

**This IS the proof!** No screenshots needed because assertions verify expected behavior.

---

*For the complete capabilities tree, see [DEBUG_AND_TEST_HUB.md](DEBUG_AND_TEST_HUB.md)*
