# LocaNext - Deployment & Distribution Guide

## 📦 Windows Distribution Options

You have **TWO options** for distributing LocaNext to Windows users:

---

## ✅ **Option 1: GitHub Releases (Recommended - Easiest)**

**Like webtranslatorApp** - Free, automatic, and easy!

### Pros:
- ✅ FREE hosting on GitHub
- ✅ Automatic update notifications
- ✅ No server bandwidth costs
- ✅ Built-in version management
- ✅ Same as webtranslatorApp (you're familiar!)

### How It Works:
1. Build `.exe` installer locally
2. Upload to GitHub Releases (manual or automated)
3. Users download from GitHub
4. App checks GitHub for updates automatically

### Setup Steps:

**1. Install electron-updater:**
```bash
cd locaNext
npm install electron-updater
```

**2. Update `package.json`:**
```json
{
  "name": "locanext",
  "version": "1.0.0",
  "build": {
    "appId": "com.locanext.app",
    "productName": "LocaNext",
    "publish": {
      "provider": "github",
      "owner": "NeilVibe",
      "repo": "LocalizationTools"
    },
    "win": {
      "target": "nsis",
      "icon": "build/icon.ico"
    }
  }
}
```

**3. Add auto-updater to `electron/main.js`:**
```javascript
const { app, BrowserWindow } = require('electron');
const { autoUpdater } = require('electron-updater');

app.on('ready', () => {
  createWindow();

  // Check for updates on startup
  autoUpdater.checkForUpdatesAndNotify();
});

// Optional: Update events
autoUpdater.on('update-available', () => {
  console.log('Update available!');
});

autoUpdater.on('update-downloaded', () => {
  console.log('Update downloaded! Will install on restart.');
});
```

**4. Build the app:**
```bash
cd locaNext
npm run build
```

This creates:
- `dist-electron/LocaNext Setup 1.0.0.exe` - Windows installer
- `dist-electron/latest.yml` - Update manifest

**5. Create GitHub Release:**

**Manual Method:**
1. Go to https://github.com/NeilVibe/LocalizationTools/releases
2. Click "Create a new release"
3. Tag: `v1.0.0`
4. Upload files:
   - `LocaNext Setup 1.0.0.exe`
   - `latest.yml`
5. Publish release

**Automated Method (GitHub Actions):**

Create `.github/workflows/release.yml`:
```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18

      - name: Install dependencies
        run: |
          cd locaNext
          npm install

      - name: Build
        run: |
          cd locaNext
          npm run build

      - name: Release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          cd locaNext
          npx electron-builder --publish always
```

**6. Push updates:**
```bash
# Update version in package.json to 1.0.1
git add .
git commit -m "Release v1.0.1"
git tag v1.0.1
git push origin v1.0.1
# GitHub Actions will automatically build and publish!
```

---

## 🖥️ **Option 2: Self-Hosted (Your Own Server)**

**More control, but requires server management.**

### Pros:
- ✅ Complete control over distribution
- ✅ No GitHub dependency
- ✅ Can integrate with your own admin dashboard
- ✅ Track downloads in your database
- ✅ Custom update logic

### Cons:
- ❌ You pay for bandwidth
- ❌ Need to maintain server
- ❌ More complex setup

### How It Works:
1. Build `.exe` installer locally
2. Upload to YOUR FastAPI server (`/updates/` folder)
3. Users download from `http://yourserver.com/updates/download/LocaNext-Setup-1.0.0.exe`
4. App checks YOUR server for updates

### Setup Steps:

**1. Install electron-updater:**
```bash
cd locaNext
npm install electron-updater
```

**2. Update `package.json` for self-hosted:**
```json
{
  "build": {
    "publish": {
      "provider": "generic",
      "url": "http://localhost:8888/updates"
    },
    "win": {
      "target": "nsis"
    }
  }
}
```

**3. Backend is ALREADY SET UP!**

The FastAPI server now has these endpoints:
- `GET /updates/latest.yml` - Update manifest
- `GET /updates/download/{filename}` - Download installer
- `GET /updates/version` - Get current version

**4. Build the app:**
```bash
cd locaNext
npm run build
```

**5. Upload to server:**
```bash
# Copy built files to server updates directory
cp dist-electron/LocaNext\ Setup\ 1.0.0.exe ../updates/
cp dist-electron/latest.yml ../updates/
```

**6. Edit `latest.yml` to point to YOUR server:**
```yaml
version: 1.0.0
files:
  - url: http://localhost:8888/updates/download/LocaNext-Setup-1.0.0.exe
    sha512: [checksum here]
    size: 123456789
path: http://localhost:8888/updates/download/LocaNext-Setup-1.0.0.exe
sha512: [checksum here]
releaseDate: '2025-11-08T12:00:00.000Z'
```

**7. Users download from:**
```
http://localhost:8888/updates/download/LocaNext-Setup-1.0.0.exe
```

**8. Auto-updates work automatically!**

The app will check `http://localhost:8888/updates/latest.yml` on startup and notify users of new versions.

---

## 🚀 Production Deployment (Self-Hosted)

**For production with a real domain:**

1. **Get a domain** (e.g., `locanext.com`)

2. **Update `package.json`:**
```json
{
  "build": {
    "publish": {
      "provider": "generic",
      "url": "https://locanext.com/updates"
    }
  }
}
```

3. **Deploy FastAPI with HTTPS:**
```bash
# Install Nginx + Certbot for SSL
sudo apt install nginx certbot python3-certbot-nginx

# Configure Nginx
server {
    listen 80;
    server_name locanext.com;

    location /updates {
        proxy_pass http://localhost:8888/updates;
    }
}

# Get SSL certificate
sudo certbot --nginx -d locanext.com
```

4. **Build and upload:**
```bash
npm run build
scp dist-electron/* user@yourserver:/opt/locanext/updates/
```

---

## 📊 Comparison

| Feature | GitHub Releases | Self-Hosted |
|---------|----------------|-------------|
| **Cost** | FREE | Server costs |
| **Bandwidth** | Unlimited (GitHub) | Your server |
| **Setup** | Easy | Moderate |
| **Control** | Limited | Full |
| **Privacy** | Public repo required | Fully private |
| **Updates** | Automatic | Automatic |
| **Download Tracking** | GitHub stats only | Full analytics |

---

## 💡 Recommendation

**For most cases: Use GitHub Releases (Option 1)**
- It's what you did for webtranslatorApp
- FREE and reliable
- No maintenance needed

**Use Self-Hosted (Option 2) if:**
- You need private distribution
- You want download analytics in your database
- You want to integrate with admin dashboard
- You already have a production server

---

## 🔧 Building for Windows

**On any OS:**
```bash
cd locaNext

# Development
npm run dev

# Production build
npm run build

# Build for Windows specifically
npx electron-builder --win
```

**Output:**
- `dist-electron/LocaNext Setup 1.0.0.exe` - Installer
- `dist-electron/win-unpacked/` - Unpacked files
- `dist-electron/latest.yml` - Update manifest

---

## 📝 Version Management

**Update version:**
1. Edit `locaNext/package.json` → change `"version": "1.0.1"`
2. Build: `npm run build`
3. Publish to GitHub or upload to server
4. Users get notified automatically!

---

## 🎯 Summary

**Quick Start (GitHub):**
```bash
npm install electron-updater
npm run build
# Upload to GitHub Releases
```

**Quick Start (Self-Hosted):**
```bash
npm install electron-updater
# Edit package.json publish.url
npm run build
cp dist-electron/* ../updates/
# Users download from YOUR server
```

Both methods support **automatic updates**! Users just need to restart the app. 🚀
