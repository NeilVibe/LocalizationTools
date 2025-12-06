/**
 * Auto-Updater Configuration
 *
 * Supports both GitHub (public) and Gitea (internal company) updates.
 * Set UPDATE_SERVER environment variable to switch sources.
 */

/**
 * Update Flow (Dual Push - Always Both!):
 *
 * DEVELOPER:
 * 1. git push origin main   ← GitHub
 * 2. git push gitea main    ← Gitea (internal)
 * 3. Both CI/CD pipelines build and create releases
 *
 * USER APP:
 * - Checks configured server for latest.yml
 * - Downloads update if newer version found
 * - Installs on restart
 *
 * SERVERS:
 * - GitHub: https://github.com/NeilVibe/LocalizationTools/releases
 * - Gitea:  http://localhost:3000/neilvibe/LocaNext/releases (internal)
 */

// Determine update source from environment
const UPDATE_SERVER = process.env.UPDATE_SERVER || 'github';

// Configuration based on update source
let autoUpdaterConfig;

if (UPDATE_SERVER === 'github') {
  // GitHub Releases (default - public)
  autoUpdaterConfig = {
    provider: 'github',
    owner: 'NeilVibe',
    repo: 'LocalizationTools',
  };
} else if (UPDATE_SERVER === 'gitea') {
  // Gitea Releases (internal company server)
  // Uses generic provider with Gitea's release asset URL
  const GITEA_URL = process.env.GITEA_URL || 'http://localhost:3000';
  autoUpdaterConfig = {
    provider: 'generic',
    url: `${GITEA_URL}/neilvibe/LocaNext/releases/download/latest`,
  };
} else {
  // Custom server (nginx, S3, etc.)
  autoUpdaterConfig = {
    provider: 'generic',
    url: UPDATE_SERVER,
  };
}

export { autoUpdaterConfig };

// For development, disable auto-updates
export const isAutoUpdateEnabled = process.env.NODE_ENV !== 'development';

/**
 * DEPLOYMENT OPTIONS:
 *
 * 1. GitHub (Default):
 *    - No env var needed
 *    - Uses GitHub Releases
 *
 * 2. Gitea (Company Internal):
 *    - Set: UPDATE_SERVER=gitea
 *    - Set: GITEA_URL=http://your-gitea-server:3000
 *    - Uses Gitea Releases
 *
 * 3. Custom Server:
 *    - Set: UPDATE_SERVER=http://your-server/updates
 *    - Host latest.yml + .exe at that URL
 *
 * DUAL PUSH REQUIRED:
 *    git push origin main   # GitHub
 *    git push gitea main    # Gitea
 */
