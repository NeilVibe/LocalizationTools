# LocaNext - Quick Start Guide

**Status**: ✅ Phase 2.1 Initial Setup Complete!

## What's Built

### ✅ Core Structure
- Electron + SvelteKit project configured
- Carbon Components Svelte (IBM Design System) integrated
- Top menu bar with "Apps" dropdown and "Tasks" button
- One-page, seamless UI/UX design
- All 448 npm packages installed successfully

### ✅ Components Created

**Layout (`src/routes/+layout.svelte`)**:
- Top menu bar with Apps dropdown
- Tasks button
- Professional Carbon Design theme (g100 - dark)

**Main Components**:
1. **Welcome.svelte** - Landing page with instructions
2. **TaskManager.svelte** - Task history, live operations, clean history
3. **XLSTransfer.svelte** - All 7 XLSTransfer functions on one page:
   - Create Dictionary
   - Transfer Translations
   - Check Newlines
   - Check Spaces
   - Find Duplicates
   - Merge Dictionaries
   - Validate Dictionary

### ✅ State Management
- Svelte 5 runes (`$state`, `$derived`, `$effect`) — per-component state
- Authentication via layout component
- WebSocket real-time updates via `src/lib/api/websocket.js`

### ✅ Development Environment
- Hot reload configured (Vite dev server)
- Electron main process ready
- Cross-platform build configuration
- DevTools enabled in development mode

## How to Run LocaNext

### Option 1: Development Mode (Recommended for Testing)

Open **two terminals**:

**Terminal 1 - Start Vite Dev Server:**
```bash
cd /home/<USERNAME>/LocalizationTools/locaNext
npm run dev:svelte
```

Wait until you see:
```
VITE v5.x.x  ready in XXXXms
➜  Local:   http://localhost:5173/
```

**Terminal 2 - Launch Electron:**
```bash
cd /home/<USERNAME>/LocalizationTools/locaNext
npm run dev:electron
```

This will:
1. Wait for Vite server to be ready
2. Launch Electron with the app
3. Open DevTools automatically
4. Enable hot reload (changes update instantly)

### Option 2: Single Command (Launches Both)

```bash
cd /home/<USERNAME>/LocalizationTools/locaNext
npm run dev
```

This runs both servers using `concurrently`.

## What You'll See

When LocaNext launches:

1. **Top Menu Bar**:
   - **LocaNext** logo on the left
   - **Apps** button (dropdown) - Click to select XLSTransfer
   - **Tasks** button - Click to view Task Manager

2. **Welcome Screen** (default):
   - "Welcome to LocaNext" message
   - Instructions on how to use the app
   - Quick stats (1 tool, 7 functions)

3. **Select "Apps" > XLSTransfer**:
   - See all 7 functions in accordion layout
   - Two columns: Main functions (left) + Utilities (right)
   - Expand any function to see its controls
   - All on one page, no navigation needed

4. **Click "Tasks"**:
   - See Task Manager view
   - Sample tasks (for demo purposes)
   - Search, filter, refresh, clear history buttons
   - Progress bars for running tasks

## Testing the UI

Currently, the buttons **will log to console** but won't execute Python code yet. That's the next phase!

To test:
1. Launch LocaNext
2. Open DevTools (Ctrl+Shift+I or Cmd+Option+I)
3. Go to Console tab
4. Click "Create Dictionary" button
5. See console log: `Creating dictionary... {dictSourceFile, dictTargetFile, ...}`

## Next Steps

### Phase 2.2: Backend Integration (Next!)

1. **Python Backend Connection**:
   - Create API client in `src/lib/api/client.js`
   - Connect to FastAPI server (http://localhost:8888)
   - JWT authentication flow

2. **XLSTransfer Execution**:
   - Spawn Python subprocess from Electron
   - Call `/server/tools/xlstransfer/core.py` functions
   - Real-time progress via WebSocket
   - Send logs to server

3. **Task Manager Integration**:
   - Real WebSocket connection to server
   - Live task updates from backend
   - Actual task history from database

## Project Structure

```
locaNext/
├── electron/
│   └── main.js                    # ✅ Electron main process
├── src/
│   ├── routes/
│   │   ├── +layout.svelte         # ✅ Top menu bar
│   │   ├── +layout.js             # ✅ SSR config
│   │   ├── +page.svelte           # ✅ App router
│   │   └── +page.js               # ✅ SSR config
│   ├── lib/
│   │   ├── components/
│   │   │   ├── apps/
│   │   │   │   └── XLSTransfer.svelte  # ✅ All 7 functions
│   │   │   ├── TaskManager.svelte       # ✅ Task management
│   │   │   └── Welcome.svelte           # ✅ Landing page
│   │   └── utils/
│   │       └── logger.js          # ✅ Console logger
│   └── app.html                   # ✅ HTML template
├── package.json                   # ✅ Dependencies
├── svelte.config.js               # ✅ SvelteKit config
├── vite.config.js                 # ✅ Vite config
└── README.md                      # ✅ Documentation
```

## Troubleshooting

**"Port 5174 is already in use"**:
- Kill the process: `pkill -f "vite dev"`
- Or use different port in `vite.config.js`

**"Electron doesn't launch"**:
- Make sure Vite dev server is running first
- Check Terminal 1 shows "VITE ready"

**"Components don't show"**:
- Check browser console (DevTools)
- Look for import errors
- Make sure all files are saved

## Current Status Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Project Setup | ✅ Complete | 448 packages installed |
| Electron Main Process | ✅ Complete | Hot reload enabled |
| Top Menu Bar | ✅ Complete | Apps dropdown + Tasks |
| Welcome Screen | ✅ Complete | Professional landing page |
| Task Manager UI | ✅ Complete | Mock data for now |
| XLSTransfer UI | ✅ Complete | All 7 functions visible |
| State Management | ✅ Complete | Svelte 5 runes ($state, $derived) |
| Backend Integration | ✅ Complete | FastAPI REST API |
| WebSocket Real-Time | ✅ Complete | socket.io-client |

---

**Congratulations! LocaNext is ready for backend integration!** 🎉

Next: Connect to Python backend and make XLSTransfer functions executable.
