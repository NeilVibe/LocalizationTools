/**
 * Secure Credentials Module
 *
 * NEVER hardcode credentials. This module provides a single source of truth
 * for credential handling across all CDP tests.
 *
 * Security Model:
 * - CI: Uses Gitea secrets (CI_TEST_USER, CI_TEST_PASS)
 * - Local: Uses environment variables or .env.local file
 * - NO fallback credentials - tests fail if not configured
 */

const fs = require('fs');
const path = require('path');

// Load .env.local if it exists (for local development)
function loadEnvLocal() {
    const envPath = path.join(__dirname, '..', '..', '..', '.env.local');
    if (fs.existsSync(envPath)) {
        const content = fs.readFileSync(envPath, 'utf-8');
        for (const line of content.split('\n')) {
            const match = line.match(/^([A-Z_]+)=(.+)$/);
            if (match) {
                const [, key, value] = match;
                if (!process.env[key]) {
                    process.env[key] = value.replace(/^["']|["']$/g, '');
                }
            }
        }
    }
}

// Initialize
loadEnvLocal();

/**
 * Get test credentials
 * @returns {{ username: string, password: string }}
 * @throws {Error} If credentials not configured
 */
function getCredentials() {
    // Priority: CDP_TEST_* > CI_TEST_* > Error
    const username = process.env.CDP_TEST_USER || process.env.CI_TEST_USER;
    const password = process.env.CDP_TEST_PASS || process.env.CI_TEST_PASS;

    if (!username || !password) {
        console.error('╔════════════════════════════════════════════════════════════╗');
        console.error('║  CREDENTIAL ERROR: Test credentials not configured!        ║');
        console.error('╠════════════════════════════════════════════════════════════╣');
        console.error('║  For CI: Configure Gitea secrets:                          ║');
        console.error('║    - CI_TEST_USER                                          ║');
        console.error('║    - CI_TEST_PASS                                          ║');
        console.error('║                                                            ║');
        console.error('║  For local testing:                                        ║');
        console.error('║    export CDP_TEST_USER=your_username                      ║');
        console.error('║    export CDP_TEST_PASS=your_password                      ║');
        console.error('║                                                            ║');
        console.error('║  Or create .env.local in project root:                     ║');
        console.error('║    CDP_TEST_USER=your_username                             ║');
        console.error('║    CDP_TEST_PASS=your_password                             ║');
        console.error('╚════════════════════════════════════════════════════════════╝');
        throw new Error('Test credentials not configured - see above for setup instructions');
    }

    return { username, password };
}

/**
 * Mask password for logging (show first/last char only)
 * @param {string} password
 * @returns {string}
 */
function maskPassword(password) {
    if (!password || password.length < 3) return '***';
    return password[0] + '*'.repeat(password.length - 2) + password[password.length - 1];
}

/**
 * Check if running in CI environment
 * @returns {boolean}
 */
function isCI() {
    return !!(process.env.CI || process.env.GITEA_ACTIONS || process.env.GITHUB_ACTIONS);
}

module.exports = {
    getCredentials,
    maskPassword,
    isCI,
    loadEnvLocal
};
