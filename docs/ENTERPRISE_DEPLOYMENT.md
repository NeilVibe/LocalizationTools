# LocaNext - Enterprise Self-Hosted Deployment

## 🏢 **For Companies with Strict Network Security**

This guide is for deploying LocaNext **entirely within your company network** with NO external dependencies. Perfect for organizations that require:
- ✅ No internet access required
- ✅ No GitHub or external services
- ✅ All updates distributed internally
- ✅ Maximum security and control

---

## 📊 **Architecture Overview**

```
YOUR COMPANY NETWORK (Closed/Isolated)
│
├── YOUR COMPUTER (192.168.1.100)
│   ├── FastAPI Server (port 8888)
│   │   ├── Backend API
│   │   ├── Admin Dashboard (port 5175)
│   │   └── /updates endpoint (serves .exe files)
│   │
│   └── Build LocaNext.exe here
│
└── EMPLOYEE COMPUTERS (192.168.1.x)
    └── Install LocaNext.exe
        └── Auto-checks for updates from YOUR computer
```

**Key Points:**
- Your computer runs the FastAPI server (backend + update server)
- Employees' LocaNext apps connect to YOUR computer's IP
- No external services needed - everything stays inside your network
- You control ALL updates - build and push from your machine

---

## 🚀 **Complete Setup Workflow**

### **Step 1: Configure Your Server IP**

First, find your computer's local IP:
```bash
# On Windows:
ipconfig
# Look for "IPv4 Address" (e.g., 192.168.1.100)

# On Linux/Mac:
ifconfig
# Look for inet address
```

Let's say your IP is: `192.168.1.100`

### **Step 2: Configure LocaNext to Use Your Server**

Edit `/locaNext/electron/main.js`:

```javascript
const { app, BrowserWindow } = require('electron');
const { autoUpdater } = require('electron-updater');

// Configure auto-updater to use YOUR server
autoUpdater.setFeedURL({
  provider: 'generic',
  url: 'http://192.168.1.100:8888/updates'  // YOUR COMPUTER'S IP
});

app.on('ready', () => {
  createWindow();

  // Check for updates on startup
  autoUpdater.checkForUpdatesAndNotify();
});

autoUpdater.on('update-available', (info) => {
  console.log('Update available:', info.version);
});

autoUpdater.on('update-downloaded', (info) => {
  console.log('Update downloaded. Will install on restart.');
});
```

Edit `/locaNext/src/lib/api/client.js` (line 6):

```javascript
// Change from localhost to YOUR IP
const API_BASE_URL = 'http://192.168.1.100:8888/api/v2';
```

### **Step 3: Build the Windows Installer**

```bash
cd /home/neil1988/LocalizationTools/locaNext
npm run build
npm run build:electron
```

This creates:
- `dist-electron/LocaNext Setup 1.0.0.exe` - Windows installer
- `dist-electron/latest.yml` - Update manifest

### **Step 4: Deploy to Updates Folder**

```bash
# Copy files to updates directory
cp dist-electron/"LocaNext Setup 1.0.0.exe" ../updates/
cp dist-electron/latest.yml ../updates/
```

Edit `updates/latest.yml` to point to your server:

```yaml
version: 1.0.0
releaseDate: '2025-11-08T00:00:00.000Z'
files:
  - url: http://192.168.1.100:8888/updates/download/LocaNext-Setup-1.0.0.exe
    sha512: [auto-generated hash]
    size: [file size in bytes]
path: http://192.168.1.100:8888/updates/download/LocaNext-Setup-1.0.0.exe
sha512: [auto-generated hash]
releaseDate: '2025-11-08T00:00:00.000Z'
```

### **Step 5: Start Your Server**

```bash
cd /home/neil1988/LocalizationTools
python3 server/main.py
```

Your server is now serving:
- Backend API: `http://192.168.1.100:8888`
- Admin Dashboard: `http://192.168.1.100:5175`
- Updates: `http://192.168.1.100:8888/updates/latest.yml`

### **Step 6: Distribute to Employees**

**First Time Installation:**
1. Copy `LocaNext Setup 1.0.0.exe` to employee computers (USB, shared drive, email)
2. Employees run the installer
3. LocaNext installs and auto-connects to YOUR server

**Future Updates:**
1. Build new version on your computer
2. Copy `.exe` and `latest.yml` to `updates/` folder
3. When employees open LocaNext, it auto-detects the update
4. They click "Update" and it downloads from YOUR server
5. Done!

---

## 🔄 **Pushing Updates Workflow**

When you want to release a new version:

```bash
# 1. Update version in package.json
cd locaNext
# Edit package.json: "version": "1.0.1"

# 2. Build new version
npm run build
npm run build:electron

# 3. Deploy to updates folder
cp dist-electron/"LocaNext Setup 1.0.1.exe" ../updates/
cp dist-electron/latest.yml ../updates/

# 4. Edit latest.yml URLs to point to your IP
nano ../updates/latest.yml
# Change: http://192.168.1.100:8888/updates/download/LocaNext-Setup-1.0.1.exe

# 5. Done! Employees will auto-detect the update
```

---

## 🔒 **Security Benefits**

✅ **No external network access needed**
- Everything stays within your company network
- No data leaves your network
- No external services or GitHub

✅ **You control everything**
- You build the updates
- You approve the updates
- You distribute the updates

✅ **Simple and auditable**
- Just `.exe` files served from your computer
- Security team can inspect the update server
- All traffic is within your network

---

## 📝 **Configuration Files Reference**

### `locaNext/package.json`:
```json
{
  "name": "locanext",
  "version": "1.0.0",
  "build": {
    "appId": "com.locanext.app",
    "productName": "LocaNext",
    "publish": null,  // No external publisher
    "win": {
      "target": "nsis",
      "icon": "build/icon.ico"
    }
  }
}
```

### `locaNext/electron/main.js`:
```javascript
autoUpdater.setFeedURL({
  provider: 'generic',
  url: 'http://YOUR_IP:8888/updates'
});
```

### `updates/latest.yml`:
```yaml
version: 1.0.0
files:
  - url: http://YOUR_IP:8888/updates/download/LocaNext-Setup-1.0.0.exe
path: http://YOUR_IP:8888/updates/download/LocaNext-Setup-1.0.0.exe
```

---

## 🎯 **Advantages Over GitHub Releases**

| Feature | GitHub Releases | Self-Hosted (Your Setup) |
|---------|----------------|--------------------------|
| **External Access** | ❌ Requires internet | ✅ No internet needed |
| **Security Control** | ❌ Data goes to GitHub | ✅ 100% internal |
| **Company Policy** | ❌ May not be allowed | ✅ Fully compliant |
| **Setup Complexity** | Easy | Easy (we built it!) |
| **Cost** | Free | Free |
| **Control** | Limited | ✅ Full control |

---

## 🆘 **Troubleshooting**

**Problem:** Employees can't connect to server
- **Solution:** Check firewall - allow port 8888 on your computer
- Windows: `Control Panel → Windows Firewall → Allow an app`

**Problem:** Updates not detected
- **Solution:** Check `latest.yml` URLs point to correct IP
- Test: Open `http://YOUR_IP:8888/updates/latest.yml` in browser

**Problem:** Can't download update
- **Solution:** Check file exists in `updates/` folder
- Check file permissions (readable)

---

## ✅ **Summary**

**What you have:**
- Self-hosted update server (FastAPI `/updates` endpoint) ✅
- Auto-update system (electron-updater) ✅
- No external dependencies ✅
- Full control over distribution ✅

**What you do:**
1. Build `.exe` on your computer
2. Copy to `updates/` folder
3. Employees auto-download from YOUR server
4. No GitHub, no external services needed!

**This is exactly what GitHub does, but 100% internal!** 🎉
