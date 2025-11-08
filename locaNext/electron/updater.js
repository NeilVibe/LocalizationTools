/**
 * Auto-Updater Configuration for Self-Hosted Updates
 *
 * This allows LocaNext to check for updates from YOUR internal server
 * instead of GitHub or external services.
 */

// NOTE: electron-updater needs to be installed
// Run: npm install electron-updater

/**
 * To enable auto-updates:
 *
 * 1. Install electron-updater:
 *    cd locaNext
 *    npm install electron-updater
 *
 * 2. Import in electron/main.js:
 *    import { autoUpdater } from 'electron-updater';
 *
 * 3. Add after app.on('ready', ...) in main.js:
 *
 *    // Configure for self-hosted updates
 *    autoUpdater.setFeedURL({
 *      provider: 'generic',
 *      url: 'http://YOUR_SERVER_IP:8888/updates'  // Change to your IP
 *    });
 *
 *    // Check for updates on startup
 *    autoUpdater.checkForUpdatesAndNotify();
 *
 *    // Optional: Listen for update events
 *    autoUpdater.on('update-available', (info) => {
 *      console.log('Update available:', info.version);
 *      mainWindow.webContents.send('update-available', info);
 *    });
 *
 *    autoUpdater.on('update-downloaded', (info) => {
 *      console.log('Update downloaded. Will install on restart.');
 *      mainWindow.webContents.send('update-downloaded', info);
 *    });
 *
 *    autoUpdater.on('error', (err) => {
 *      console.error('Update error:', err);
 *    });
 *
 * 4. Update package.json "build" section:
 *    "build": {
 *      "appId": "com.locanext.app",
 *      "productName": "LocaNext",
 *      "publish": null,  // No automatic publishing
 *      ...
 *    }
 *
 * 5. Build and deploy:
 *    npm run build
 *    npm run build:electron
 *    cp dist-electron/LocaNext-Setup-*.exe ../updates/
 *    cp dist-electron/latest.yml ../updates/
 *
 * 6. Edit updates/latest.yml:
 *    Change URLs to: http://YOUR_SERVER_IP:8888/updates/download/LocaNext-Setup-1.0.0.exe
 *
 * 7. Employees' apps will auto-check for updates from YOUR server!
 */

export const autoUpdaterConfig = {
  provider: 'generic',
  url: 'http://localhost:8888/updates'  // CHANGE THIS to your server IP for production
};

// For development, you can disable auto-updates
export const isAutoUpdateEnabled = process.env.NODE_ENV !== 'development';
