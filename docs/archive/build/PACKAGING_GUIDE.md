# 📦 LocaNext - Complete Packaging & Distribution Guide

## 🎯 **Quick Summary**

You have **two apps** to distribute:

1. **LocaNext Desktop App** (Electron) - For employees
2. **Admin Dashboard** (Web) - For managers/CEOs

---

## 🖥️ **Part 1: LocaNext Desktop App (Employees)**

### **What Employees Get:**
- Windows `.exe` installer
- Installs LocaNext on their computer
- Auto-connects to YOUR server
- Auto-updates from YOUR server

### **How to Package & Distribute:**

#### **Step 1: Configure Server IP** (One-time setup)

Before building, set YOUR computer's IP address:

```bash
# Find your IP:
ipconfig   # Windows
ifconfig   # Linux/Mac
```

Let's say your IP is `192.168.1.100`

Edit these files:

**A. locaNext/src/lib/api/client.js** (line 6):
```javascript
const API_BASE_URL = 'http://192.168.1.100:8888/api/v2';  // Your IP
```

**B. locaNext/src/lib/api/websocket.js** (line 5):
```javascript
const SOCKET_URL = 'http://192.168.1.100:8888/ws';  // Your IP
```

**C. locaNext/electron/updater.js** (line 50):
```javascript
url: 'http://192.168.1.100:8888/updates'  // Your IP
```

#### **Step 2: Build the Windows Installer**

```bash
cd /home/neil1988/LocalizationTools/locaNext

# Build Svelte app
npm run build

# Build Electron app (creates .exe)
npm run build:electron
```

**Output:**
- `dist-electron/LocaNext Setup 1.0.0.exe` (Windows installer)
- `dist-electron/latest.yml` (Update manifest)

#### **Step 3: Deploy to Updates Folder**

```bash
# Copy files to updates directory
cp "dist-electron/LocaNext Setup 1.0.0.exe" ../updates/
cp dist-electron/latest.yml ../updates/
```

Edit `updates/latest.yml`:
```yaml
version: 1.0.0
releaseDate: '2025-11-08T00:00:00.000Z'
files:
  - url: http://192.168.1.100:8888/updates/download/LocaNext-Setup-1.0.0.exe
    sha512: [keep existing hash]
    size: [keep existing size]
path: http://192.168.1.100:8888/updates/download/LocaNext-Setup-1.0.0.exe
sha512: [keep existing hash]
```

#### **Step 4: Distribute to Employees**

**First Installation:**
1. Copy `LocaNext Setup 1.0.0.exe` to employees (USB, shared drive, email)
2. Employees double-click to install
3. LocaNext opens and connects to YOUR server automatically

**Future Updates:**
1. Build new version (repeat Steps 2-3)
2. Bump version in `package.json`: `"version": "1.0.1"`
3. Deploy to `updates/` folder
4. When employees open LocaNext, they get notified of update
5. They click "Update" and it downloads from YOUR server

---

## 🌐 **Part 2: Admin Dashboard (Managers/CEOs)**

### **What Managers Get:**
- Web URL to access dashboard
- No installation required
- Access from any browser

### **How to Deploy:**

#### **Option A: Access from Your Computer (Simplest)**

Start the dev server:
```bash
cd /home/neil1988/LocalizationTools/adminDashboard
npm run dev -- --port 5175
```

**Share with managers:**
- URL: `http://YOUR_IP:5175/`
- Example: `http://192.168.1.100:5175/`
- They open in browser (Chrome, Edge, etc.)

#### **Option B: Build for Production**

```bash
cd adminDashboard
npm run build
```

Then serve with a web server:

**Using Python (simple):**
```bash
cd build
python3 -m http.server 5175
```

**Using Nginx (advanced):**
```nginx
server {
    listen 5175;
    root /home/neil1988/LocalizationTools/adminDashboard/build;
    index index.html;
}
```

---

## 🚀 **Complete Deployment Workflow**

### **For YOU (Admin/Developer):**

```bash
# 1. Start backend server (keeps running)
cd /home/neil1988/LocalizationTools
python3 server/main.py &

# 2. Start admin dashboard (keeps running)
cd adminDashboard
npm run dev -- --port 5175 &

# 3. Build LocaNext for employees
cd ../locaNext
npm run build
npm run build:electron

# 4. Deploy to updates folder
cp "dist-electron/LocaNext Setup 1.0.0.exe" ../updates/
cp dist-electron/latest.yml ../updates/
# Edit latest.yml URLs to your IP

# 5. Distribute LocaNext Setup.exe to employees
```

### **For Employees:**

```
1. Receive LocaNext Setup 1.0.0.exe
2. Double-click to install
3. Open LocaNext
4. Login with credentials
5. Use XLSTransfer and other tools
```

### **For Managers/CEOs:**

```
1. Open browser (Chrome, Edge, etc.)
2. Go to http://YOUR_IP:5175/
3. View dashboard:
   - User activity
   - System statistics
   - Live operations
   - Export reports
```

---

## 📊 **What Needs to Run on Your Computer**

For everything to work, YOUR computer must run:

1. **Backend Server** (port 8888)
   ```bash
   python3 server/main.py
   ```

2. **Admin Dashboard** (port 5175)
   ```bash
   cd adminDashboard && npm run dev -- --port 5175
   ```

**Keep these running!** They serve:
- API for LocaNext apps
- WebSocket for real-time updates
- Admin dashboard for managers
- Update files for auto-updates

---

## 🔄 **Updating LocaNext (Push New Version)**

When you want to release v1.0.1:

```bash
cd locaNext

# 1. Update version
nano package.json
# Change: "version": "1.0.1"

# 2. Build
npm run build
npm run build:electron

# 3. Deploy
cp "dist-electron/LocaNext Setup 1.0.1.exe" ../updates/
cp dist-electron/latest.yml ../updates/

# 4. Edit latest.yml
nano ../updates/latest.yml
# Update version and URLs

# 5. Done! Employees auto-notified when they open LocaNext
```

---

## 📁 **File Locations Reference**

```
LocalizationTools/
├── server/
│   └── main.py                    # Backend server (run this)
│
├── adminDashboard/
│   ├── npm run dev                # Dev server (run this)
│   └── build/                     # Production build (optional)
│
├── locaNext/
│   ├── dist-electron/             # Built .exe appears here
│   │   ├── LocaNext Setup 1.0.0.exe
│   │   └── latest.yml
│   └── package.json               # Version number here
│
└── updates/                       # Deploy .exe files here
    ├── LocaNext Setup 1.0.0.exe
    └── latest.yml
```

---

## ✅ **Checklist Before Distribution**

- [ ] Backend server running
- [ ] Admin dashboard accessible
- [ ] Server IP configured in all files
- [ ] LocaNext.exe built successfully
- [ ] Files copied to updates/ folder
- [ ] latest.yml URLs point to your IP
- [ ] Firewall allows port 8888 and 5175
- [ ] Tested update check: `curl http://YOUR_IP:8888/updates/latest.yml`

---

## 🆘 **Troubleshooting**

**Problem:** Employees can't connect
- Check server is running: `curl http://YOUR_IP:8888/health`
- Check firewall allows port 8888
- Verify IP address is correct

**Problem:** Updates not detected
- Check `updates/latest.yml` exists
- Verify URLs point to correct IP
- Test: `curl http://YOUR_IP:8888/updates/latest.yml`

**Problem:** Admin dashboard won't load
- Check dev server running: `ps aux | grep "npm run dev"`
- Test: `curl http://YOUR_IP:5175/`
- Check firewall allows port 5175

---

## 🎉 **Summary**

**You have everything you need!**

- ✅ Self-hosted update server (no GitHub needed)
- ✅ Simple build process
- ✅ Internal distribution only
- ✅ Auto-updates from YOUR server
- ✅ Admin dashboard for managers
- ✅ All within company network

**No external services. Maximum security. Full control.** 🔒
