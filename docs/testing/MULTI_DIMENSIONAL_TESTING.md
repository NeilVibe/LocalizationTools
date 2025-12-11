# Multi-Dimensional Testing Guide

**Test LocaNext in 3 different environments to catch all bugs.**

---

## The 3 Dimensions

| Dimension | Environment | What You Test |
|-----------|-------------|---------------|
| **DEV** | API only (no UI) | Backend logic, API endpoints, data parsing |
| **APP** | electron:dev | UI rendering, component behavior, navigation |
| **EXE** | LocaNext.exe | Full integration, file paths, Windows compat |

---

## Quick Commands

### 1. DEV Mode (Backend API)

```bash
# Start backend
python3 server/main.py

# Run test (in another terminal)
cd testing_toolkit/cdp
node apps/ldm/test_file_upload.js dev
```

**What it tests:**
- API endpoints work correctly
- Database operations succeed
- Auth flow works
- File parsing logic correct

### 2. APP Mode (electron:dev)

```bash
# Start Electron with CDP
cd locaNext
npm run electron:dev -- --remote-debugging-port=9222

# Run test (in another terminal)
cd testing_toolkit/cdp
node apps/ldm/test_file_upload.js app
```

**What it tests:**
- UI renders correctly
- Components mount properly
- Navigation works
- Store updates propagate

### 3. EXE Mode (LocaNext.exe on Windows)

```bash
# Launch LocaNext.exe with CDP (from WSL)
cd /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/LocaNext
./LocaNext.exe --remote-debugging-port=9222 &

# Run test
cd ~/LocalizationTools/testing_toolkit/cdp
node apps/ldm/test_file_upload.js exe
```

**What it tests:**
- Windows file paths work
- Embedded server starts
- Full app integration
- Production-like conditions

---

## When to Use Which

| Scenario | Use |
|----------|-----|
| Developing backend logic | DEV |
| Fixing a UI component | APP |
| Testing before release | EXE |
| Bug reproduction | Start with EXE, narrow down to DEV |
| CI/CD pipeline | DEV (fast) + EXE (thorough) |

---

## Troubleshooting

### CDP Connection Failed

```bash
# Check if app is running with CDP
curl http://localhost:9222/json
```

### Backend Not Responding

```bash
curl http://localhost:8888/health
```

### Need to Kill Stuck Processes

```bash
# WSL
pkill -f "python.*main.py"
pkill -f LocaNext

# Windows
/mnt/c/Windows/System32/taskkill.exe /F /IM LocaNext.exe
```

---

*See also: [testing_toolkit/README.md](../../../testing_toolkit/README.md)*
