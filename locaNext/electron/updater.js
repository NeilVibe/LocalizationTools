/**
 * Auto-Updater Configuration for GitHub Releases
 *
 * LocaNext checks for updates from GitHub Releases.
 * When you create a new release, users will be notified automatically.
 */

/**
 * GitHub Releases Auto-Update Flow:
 *
 * 1. You push code to GitHub
 * 2. GitHub Actions builds the installer
 * 3. Workflow creates a GitHub Release with the .exe
 * 4. User's app checks GitHub for new releases
 * 5. If newer version found → download and install
 *
 * To trigger an update:
 * 1. Update version in version.py
 * 2. Add build trigger to BUILD_TRIGGER.txt
 * 3. Push to main
 * 4. GitHub Actions builds and creates release
 * 5. All user apps will auto-update!
 */

// GitHub releases configuration
export const autoUpdaterConfig = {
  provider: 'github',
  owner: 'NeilVibe',
  repo: 'LocalizationTools',
  // Optional: use private token for private repos
  // token: process.env.GH_TOKEN
};

// For development, disable auto-updates
export const isAutoUpdateEnabled = process.env.NODE_ENV !== 'development';

/**
 * For INTERNAL/PRIVATE updates (no GitHub):
 * Change config to:
 *
 * export const autoUpdaterConfig = {
 *   provider: 'generic',
 *   url: 'http://YOUR_INTERNAL_SERVER:8888/updates'
 * };
 *
 * Then host latest.yml and .exe on your internal server.
 */
