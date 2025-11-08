# LocaNext

**Professional Desktop Platform for Localization Tools**

LocaNext is an Electron-based desktop application that consolidates all your localization and translation tools into one professional, easy-to-use interface.

## Features

- **Ultra-Clean UI**: Simple top menu bar with Apps dropdown and Tasks button
- **One-Page Design**: All tool functions accessible on a single, seamless page
- **Modular Sub-GUIs**: Complex operations displayed as modular components
- **Real-Time Updates**: WebSocket integration for live progress tracking
- **Local Processing**: All operations run on your local machine
- **Professional**: Built with Carbon Design System (IBM)

## Current Tools

### XLSTransfer ✅
Excel translation and localization toolkit with 7 functions:
1. Create Dictionary - AI-powered semantic matching
2. Transfer Translations - Apply dictionary to Excel files
3. Check Newlines - Verify newline consistency
4. Check Spaces - Verify space consistency
5. Find Duplicates - Locate duplicate entries
6. Merge Dictionaries - Combine multiple dictionaries
7. Validate Dictionary - Check format and consistency

## Tech Stack

- **Frontend**: Svelte + SvelteKit
- **Desktop Framework**: Electron
- **UI Library**: Carbon Components Svelte (IBM Design System)
- **Backend**: FastAPI (Python) - See `/server` folder
- **Real-Time**: Socket.IO for WebSocket communication

## Development

### Prerequisites

- Node.js 18+ and npm
- Python 3.8+ (for backend server)

### Install Dependencies

```bash
npm install
```

### Run Development Server

```bash
# Terminal 1: Start backend server (from project root)
cd ..
python3 server/main.py

# Terminal 2: Start LocaNext (from locaNext folder)
npm run dev
```

This will:
1. Start Vite dev server on http://localhost:5173
2. Launch Electron app with hot reload enabled
3. Open DevTools automatically

### Build for Production

```bash
# Build Svelte app
npm run build

# Package Electron app (Windows/Mac/Linux)
npm run package
```

Output will be in `dist-electron/` folder.

## Project Structure

```
locaNext/
├── electron/
│   └── main.js              # Electron main process
├── src/
│   ├── routes/
│   │   ├── +layout.svelte   # Root layout (top menu bar)
│   │   └── +page.svelte     # Main page (app router)
│   ├── lib/
│   │   ├── components/
│   │   │   ├── apps/
│   │   │   │   └── XLSTransfer.svelte  # XLSTransfer UI
│   │   │   ├── TaskManager.svelte       # Task manager view
│   │   │   └── Welcome.svelte           # Welcome screen
│   │   └── stores/
│   │       └── app.js       # Svelte stores (state management)
│   └── app.html             # HTML template
├── static/                  # Static assets
├── package.json
├── svelte.config.js         # SvelteKit config
└── vite.config.js           # Vite config
```

## Adding New Tools

To add a new tool to LocaNext:

1. **Create the Svelte component**:
   ```bash
   src/lib/components/apps/YourTool.svelte
   ```

2. **Add to apps list** in `src/routes/+layout.svelte`:
   ```javascript
   const apps = [
     { id: 'xlstransfer', name: 'XLSTransfer', description: '...' },
     { id: 'yourtool', name: 'YourTool', description: '...' }  // Add this
   ];
   ```

3. **Add route** in `src/routes/+page.svelte`:
   ```svelte
   {:else if app === 'yourtool'}
     <YourTool />
   ```

4. **Implement Python backend** in `/client/tools/yourtool/`
   - Follow XLSTransfer pattern (see `/client/tools/xls_transfer/`)

## Backend Integration

LocaNext connects to the FastAPI backend server:

- **Server URL**: http://localhost:8888
- **WebSocket**: ws://localhost:8888/ws/socket.io
- **Authentication**: JWT tokens
- **Logging**: All operations logged to server

See `/server` folder in project root for backend code.

## License

MIT

---

**Status**: Phase 2.1 - Initial Development
**First Milestone**: XLSTransfer fully functional
