# LanguageTool Lazy Load

**Priority:** P2 | **Status:** IMPLEMENTED | **Created:** 2025-12-28

---

## Problem

LanguageTool Java server runs 24/7, consuming **~900MB RAM** even when not in use.

```
Current: Always running on port 8081
RAM: 909 MB (biggest single process!)
CPU: Idle when not checking grammar
```

---

## Proposed Solution: Lazy Load

Start LanguageTool **on-demand** when user needs grammar check, stop after idle timeout.

### Option A: Start/Stop on Request

```
User clicks "Check Grammar"
  → Frontend calls /api/ldm/grammar/check
  → Backend checks if LanguageTool running
  → If not: start it, wait for ready (~5-10 sec)
  → Perform check
  → Start idle timer (5 min)
  → After 5 min idle: stop LanguageTool
```

**Pros:**
- Saves 900MB when not using grammar check
- Automatic lifecycle management

**Cons:**
- 5-10 second delay on first grammar check
- Need to handle startup/shutdown logic

### Option B: User-Controlled Toggle

```
Settings → "Grammar Checker"
  [ ] Enable (loads LanguageTool, uses 900MB)
  [x] Disable (saves RAM)
```

**Pros:**
- Simple implementation
- User has full control

**Cons:**
- Manual management required

### Option C: Local Installation (User PC)

Move LanguageTool from central server to user's PC:

```
Current:
  LocaNext → Central LanguageTool Server (172.28.150.120:8081)

Proposed:
  LocaNext → Local LanguageTool (bundled, starts on demand)
```

**Pros:**
- No central server dependency
- Works offline
- Each user pays own RAM cost

**Cons:**
- Adds ~200MB to installer (LanguageTool JAR)
- Requires Java on user PC (or bundle JRE)
- More complex packaging

---

## Implementation Notes

### Starting LanguageTool

```bash
# Current systemd service
sudo systemctl start languagetool

# Or direct command
java -Xmx512m -cp languagetool-server.jar \
  org.languagetool.server.HTTPServer \
  --port 8081 --public --allow-origin *
```

### Health Check

```bash
curl http://localhost:8081/v2/check?text=test&language=en-US
```

### Stopping

```bash
sudo systemctl stop languagetool
# Or
pkill -f languagetool
```

---

## Recommendation

**Start with Option B** (user toggle) - simplest to implement:

1. Add toggle in Settings: "Enable Grammar Checker"
2. When OFF: Don't start LanguageTool, grey out grammar menu
3. When ON: Start LanguageTool on app launch
4. Save preference in user settings

**Later:** Upgrade to Option A (auto start/stop) for better UX.

---

## Files to Modify

| File | Changes |
|------|---------|
| `PreferencesModal.svelte` | Add grammar toggle |
| `preferences.js` | Add `grammarEnabled` setting |
| Backend startup | Conditional LanguageTool start |
| Grammar endpoints | Check if service available |

---

## RAM Impact

| State | RAM Saved |
|-------|-----------|
| Grammar OFF | ~900 MB |
| Grammar ON (current) | 0 MB |

---

## Implementation (2025-12-28)

**Implemented Option A** - Auto start/stop on demand:

### How It Works

```
User clicks "Check Grammar"
  → Backend calls languagetool.check()
  → languagetool.ensure_running() checks if server is up
  → If not running: starts via systemctl (waits up to 30s)
  → Performs grammar check
  → Starts 5-minute idle timer
  → After 5 min idle: automatically stops server
```

### Files Modified

| File | Changes |
|------|---------|
| `server/utils/languagetool.py` | Added lazy load logic |

### Key Features

- **Auto-start**: Server starts when grammar check requested
- **Auto-stop**: Server stops after 5 minutes idle
- **Startup wait**: Up to 30 seconds for server to become ready
- **RAM savings**: ~900MB when grammar not in use

### Manual Control

```bash
# Stop LanguageTool (it will auto-start when needed)
sudo systemctl stop languagetool

# Check if running
systemctl status languagetool

# Force start (if needed)
sudo systemctl start languagetool
```

---

*Optimization complete - saves ~900MB RAM when grammar check not in use*
