# Debug & Test Hub

**Updated:** 2025-12-19 | **Build:** 300

---

## Autonomous Testing Protocol

Claude works **alone** on testing. User provides direction only.

```
User Role:  Direction, priorities, approval
Claude:     Build → Test → Fix → Rebuild → Report
```

**Claude has full authority to:**
- Build/deploy/test independently
- Run CDP tests via remote debugging
- Read logs, fix issues, iterate

---

## Test Locations

### Windows Playground

```
C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\Playground\LocaNext\
├── LocaNext.exe
└── logs/

WSL: /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/Playground/LocaNext
```

### Test Data Files

```
D:\TestFilesForLocaNext\
├── sampleofLanguageData.txt     ← QuickSearch (16MB, KR+FR)
├── GlossaryUploadTestFile.xlsx  ← Dictionary (100 rows)
├── 150linetranslationtest.xlsx  ← XLSTransfer
└── closetotest.txt              ← Transfer to Close

WSL: /mnt/d/TestFilesForLocaNext
```

---

## Test Methods

| Method | When | Doc |
|--------|------|-----|
| **CDP (Node.js)** | Windows app testing | [testing_toolkit/cdp/README.md](../../testing_toolkit/cdp/README.md) |
| **pytest** | Backend API/unit tests | [PYTEST_GUIDE.md](PYTEST_GUIDE.md) |
| **Playwright** | Frontend E2E (dev) | [PLAYWRIGHT_GUIDE.md](PLAYWRIGHT_GUIDE.md) |

---

## Quick Commands

### CDP Test (Windows App)
```bash
cd testing_toolkit/cdp
node test_bug029.js
```

### Backend Test
```bash
python3 -m pytest tests/ -v
```

### With Server Running
```bash
RUN_API_TESTS=1 python3 -m pytest -v
```

---

## DEV_MODE (Skip Auth)

```bash
DEV_MODE=true python3 server/main.py
```

Auto-authenticates localhost API calls. No JWT needed.

---

## Multi-Environment Testing

**Always test in multiple environments:**

| Environment | Command |
|-------------|---------|
| WSL curl | `curl http://localhost:8888/health` |
| Windows browser | Open `http://localhost:5175` |
| LocaNext.exe | CDP via port 9222 |

**Server binding matters:**
```bash
# WSL only
python3 server/main.py

# Windows + WSL
SERVER_HOST=0.0.0.0 python3 server/main.py
```

---

## Process Management

### Kill & Launch (WSL → Windows)
```bash
# Kill existing
/mnt/c/Windows/System32/taskkill.exe /F /IM "LocaNext.exe" /T

# Launch with CDP
cd /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/Playground/LocaNext
./LocaNext.exe --remote-debugging-port=9222 &

# Wait & verify
sleep 30
curl -s http://127.0.0.1:9222/json | head -5
```

### Kill Backend
```bash
fuser -k 8888/tcp
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Port in use | `fuser -k PORT/tcp` |
| CDP no connection | Check app running with `--remote-debugging-port=9222` |
| Windows browser fails, WSL works | Server bound to 127.0.0.1, use `SERVER_HOST=0.0.0.0` |
| Multiple LocaNext windows | Kill all, launch ONE instance |

---

*See [testing_toolkit/cdp/README.md](../../testing_toolkit/cdp/README.md) for CDP details*
