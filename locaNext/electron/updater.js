/**
 * Auto-Updater Configuration
 *
 * PRIMARY: Gitea (internal company server) - where CI/CD builds and releases
 * BACKUP: GitHub (public) - for external distribution
 *
 * Set UPDATE_SERVER=github to use GitHub instead.
 */

/**
 * Update Flow:
 *
 * DEVELOPER:
 * 1. git push gitea main    ← Gitea (primary - triggers CI/CD)
 * 2. git push origin main   ← GitHub (backup)
 *
 * USER APP:
 * - Checks Gitea server for latest.yml (default)
 * - Downloads update if newer version found
 * - Installs on restart
 *
 * SERVERS:
 * - Gitea:  http://<GITEA_HOST>:3000/<GIT_USER>/LocaNext/releases (PRIMARY)
 * - GitHub: https://github.com/<GIT_USER>/LocalizationTools/releases (backup)
 */

// Determine update source from environment (default: gitea)
const UPDATE_SERVER = process.env.UPDATE_SERVER || 'gitea';

// Gitea server URL (internal)
const GITEA_URL = process.env.GITEA_URL || 'http://localhost:3000';

// Configuration based on update source
let autoUpdaterConfig;

if (UPDATE_SERVER === 'gitea') {
  // Gitea Releases (default - internal company server)
  // Uses generic provider with Gitea's release asset URL
  autoUpdaterConfig = {
    provider: 'generic',
    url: `${GITEA_URL}/<GIT_USER>/LocaNext/releases/download/latest`,
  };
} else if (UPDATE_SERVER === 'github') {
  // GitHub Releases (backup - public)
  autoUpdaterConfig = {
    provider: 'github',
    owner: '<GIT_USER>',
    repo: 'LocalizationTools',
  };
} else {
  // Custom server (nginx, S3, etc.)
  autoUpdaterConfig = {
    provider: 'generic',
    url: UPDATE_SERVER,
  };
}

export { autoUpdaterConfig };

// Disable auto-updates in development OR Light Mode (no external network calls)
// Must be a function (not a constant) because LOCANEXT_LIGHT_MODE is set after imports
export function isAutoUpdateEnabled() {
  return process.env.NODE_ENV !== 'development' && process.env.LOCANEXT_LIGHT_MODE !== '1';
}

/**
 * DEPLOYMENT OPTIONS:
 *
 * 1. Gitea (Default - PRIMARY):
 *    - No env var needed
 *    - Uses Gitea at http://<GITEA_HOST>:3000
 *    - This is where CI/CD builds and releases
 *
 * 2. GitHub (Backup):
 *    - Set: UPDATE_SERVER=github
 *    - Uses GitHub Releases for external distribution
 *
 * 3. Custom Server:
 *    - Set: UPDATE_SERVER=http://your-server/updates
 *    - Host latest.yml + .exe at that URL
 */
