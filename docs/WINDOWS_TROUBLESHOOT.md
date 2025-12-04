# Windows Build Troubleshooting Guide

**Version:** 2512041930 | **Updated:** 2025-12-04

---

## 🎯 Purpose

This guide documents how to debug and troubleshoot LocaNext Windows builds from WSL.

---

## 🔧 Testing Windows Builds from WSL

### Access Windows Files
```bash
# Windows path: C:\Users\MYCOM\Desktop\LocaNext
# WSL path:     /mnt/c/Users/MYCOM/Desktop/LocaNext
```

### Quick Diagnostic Commands

```bash
# 1. Check installed files
ls -la "/mnt/c/Users/MYCOM/Desktop/LocaNext/"

# 2. Check if first-run completed
cat "/mnt/c/Users/MYCOM/Desktop/LocaNext/first_run_complete.flag"

# 3. Check Python works
"/mnt/c/Users/MYCOM/Desktop/LocaNext/tools/python/python.exe" --version

# 4. Check Python imports
"/mnt/c/Users/MYCOM/Desktop/LocaNext/tools/python/python.exe" -c "import fastapi; import torch; print('OK')"

# 5. Check model files
ls -la "/mnt/c/Users/MYCOM/Desktop/LocaNext/models/kr-sbert/"

# 6. Check logs
cat "/mnt/c/Users/MYCOM/Desktop/LocaNext/logs/locanext_app.log"

# 7. Run install_deps manually
cd "/mnt/c/Users/MYCOM/Desktop/LocaNext/tools"
"./python/python.exe" install_deps.py
```

### Launch App from WSL
```bash
# Kill existing instances
/mnt/c/Windows/System32/taskkill.exe /F /IM LocaNext.exe 2>/dev/null

# Launch app
/mnt/c/Windows/System32/cmd.exe /c "start C:\Users\MYCOM\Desktop\LocaNext\LocaNext.exe"

# Wait and check logs
sleep 10
cat "/mnt/c/Users/MYCOM/Desktop/LocaNext/logs/locanext_app.log"
```

---

## 🐛 Known Issues & Fixes

### Issue 1: Logger ASAR Path (FIXED in v2512041930)

**Symptom:** No logs created, silent failures

**Root Cause:** `logger.js` used `__dirname` which inside ASAR points to `app.asar/electron/` - can't write files inside ASAR archive.

**Fix:** Use `process.resourcesPath` to get path outside ASAR:
```javascript
// OLD (broken)
const projectRoot = path.join(__dirname, '../..');

// NEW (fixed)
const isPackaged = __dirname.includes('app.asar');
if (isPackaged) {
  const appRoot = path.join(process.resourcesPath, '..');
  return path.join(appRoot, 'logs');
}
```

**Files Changed:** `electron/logger.js`

---

### Issue 2: First-Run Setup Not Triggering (FIXED in v2512041930)

**Symptom:** App launches but setup never runs, no deps installed

**Root Cause:** Logger crash early in startup prevented first-run check

**Fix:**
1. Fixed logger (Issue 1)
2. Added try-catch around first-run setup
3. Added health check that runs on EVERY launch

**Files Changed:** `electron/main.js`

---

### Issue 3: Missing Python Packages

**Symptom:** `ModuleNotFoundError: No module named 'torch'`

**Diagnosis:**
```bash
"/mnt/c/Users/MYCOM/Desktop/LocaNext/tools/python/python.exe" -c "import torch"
```

**Manual Fix:**
```bash
cd "/mnt/c/Users/MYCOM/Desktop/LocaNext/tools"
"./python/python.exe" install_deps.py
```

**Auto-Fix:** Health check now detects and auto-repairs on launch.

---

### Issue 4: AI Model Not Downloaded

**Symptom:** `models/kr-sbert/` only contains `model_placeholder.txt`

**Diagnosis:**
```bash
ls -la "/mnt/c/Users/MYCOM/Desktop/LocaNext/models/kr-sbert/"
# Should have: config.json, model.safetensors, tokenizer files
```

**Manual Fix:**
```bash
cd "/mnt/c/Users/MYCOM/Desktop/LocaNext/tools"
"./python/python.exe" download_model.py
```

**Auto-Fix:** Health check now detects and auto-repairs on launch.

---

## 📋 Diagnostic Checklist

Run this checklist when debugging a Windows build:

```
□ 1. Python executable exists?
     /mnt/c/.../LocaNext/tools/python/python.exe

□ 2. Python version correct?
     python.exe --version → Python 3.11.x

□ 3. Core packages installed?
     python.exe -c "import fastapi; import uvicorn"

□ 4. AI packages installed?
     python.exe -c "import torch; import transformers"

□ 5. Server files exist?
     /mnt/c/.../LocaNext/server/main.py

□ 6. Model files exist?
     /mnt/c/.../LocaNext/models/kr-sbert/config.json

□ 7. First-run flag exists?
     /mnt/c/.../LocaNext/first_run_complete.flag

□ 8. Logs being written?
     /mnt/c/.../LocaNext/logs/locanext_app.log

□ 9. App launches?
     cmd.exe /c "start LocaNext.exe"

□ 10. Backend responds?
      curl http://localhost:8888/health
```

---

## 🏗️ File Structure (Production Build)

```
C:\Users\MYCOM\Desktop\LocaNext\
├── LocaNext.exe              # Main executable
├── resources/
│   ├── app.asar              # Packaged Electron app (read-only!)
│   └── app-update.yml        # Auto-update config
├── tools/
│   ├── python/               # Embedded Python 3.11
│   │   ├── python.exe
│   │   └── Lib/site-packages/
│   ├── install_deps.py       # Dependency installer
│   └── download_model.py     # Model downloader
├── server/
│   └── main.py               # FastAPI backend
├── models/
│   └── kr-sbert/             # Korean BERT model (447MB)
├── logs/                     # App logs (created on first run)
│   ├── locanext_app.log
│   └── locanext_error.log
├── first_run_complete.flag   # Indicates setup completed
└── last_repair.json          # Tracks repair attempts
```

---

## 🔄 Health Check System (v2512041930+)

The app now performs health checks on EVERY launch:

```
App Launch
    ↓
Health Check
├── Python exists? ──────────► CRITICAL if missing
├── Server files exist? ─────► CRITICAL if missing
├── Core packages work? ─────► REPAIR if missing
├── AI packages work? ───────► REPAIR if missing
└── Model files exist? ──────► REPAIR if missing
    ↓
Auto-Repair (if needed)
├── Shows "Repairing..." window
├── Runs install_deps.py
├── Runs download_model.py
└── Verifies repair success
    ↓
Start Backend & UI
```

---

## ⚠️ IMPORTANT: Cleanup After Debugging

**ALWAYS kill background shells and processes after debugging!**

If shells are left running, they can:
- Lock files, preventing folder deletion
- Keep LocaNext.exe processes running
- Cause stale reminders in Claude sessions

```bash
# Kill all LocaNext processes on Windows
/mnt/c/Windows/System32/taskkill.exe /F /IM LocaNext.exe

# If using Claude Code, kill any background shells:
# Use the KillShell tool with the shell_id shown in system reminders
```

**Checklist before ending debug session:**
- [ ] Kill all LocaNext.exe processes
- [ ] Kill all background bash shells
- [ ] Verify user can delete the test folder

---

## 📞 Support Escalation

If auto-repair fails repeatedly:

1. Check internet connection
2. Check disk space (need ~3GB for deps + model)
3. Check antivirus isn't blocking Python
4. Try manual repair via Settings
5. Reinstall from fresh installer

---

*Last updated: 2025-12-04*
