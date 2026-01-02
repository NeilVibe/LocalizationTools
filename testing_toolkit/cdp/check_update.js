/**
 * Test script to verify auto-updater is checking Gitea
 *
 * This script:
 * 1. Fetches latest.yml from Gitea (same URL the app uses)
 * 2. Compares with installed version
 * 3. Logs what the auto-updater would see
 *
 * Run from Windows:
 *   node testing_toolkit/cdp/check_update.js
 */

const https = require('https');
const http = require('http');

const GITEA_URL = 'http://172.28.150.120:3000/neilvibe/LocaNext/releases/download/latest/latest.yml';
const INSTALLED_VERSION = process.argv[2] || '26.102.1001';

console.log('=== Auto-Update Test ===\n');
console.log(`Installed version: ${INSTALLED_VERSION}`);
console.log(`Checking: ${GITEA_URL}\n`);

// Fetch latest.yml from Gitea
http.get(GITEA_URL, (res) => {
  let data = '';

  res.on('data', chunk => data += chunk);

  res.on('end', () => {
    console.log('=== Server Response ===');
    console.log(`Status: ${res.statusCode}`);
    console.log(`Content-Type: ${res.headers['content-type']}`);
    console.log('');
    console.log('=== latest.yml content ===');
    console.log(data);

    // Parse version from latest.yml
    const versionMatch = data.match(/version:\s*(.+)/);
    if (versionMatch) {
      const serverVersion = versionMatch[1].trim();
      console.log('');
      console.log('=== Comparison ===');
      console.log(`Server version:    ${serverVersion}`);
      console.log(`Installed version: ${INSTALLED_VERSION}`);

      // Simple version comparison
      if (serverVersion > INSTALLED_VERSION) {
        console.log('\n[UPDATE AVAILABLE] The auto-updater would download the update.');
      } else if (serverVersion === INSTALLED_VERSION) {
        console.log('\n[UP TO DATE] No update needed.');
      } else {
        console.log('\n[NEWER INSTALLED] Installed is newer than server (unusual).');
      }
    }
  });
}).on('error', (err) => {
  console.error('Error fetching latest.yml:', err.message);
  console.error('');
  console.error('This means the auto-updater CANNOT reach Gitea!');
});
