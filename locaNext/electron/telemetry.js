/**
 * Telemetry Client - P12.5.7
 *
 * Sends telemetry data to Central Server for monitoring.
 * Features:
 * - Auto-registration on first launch
 * - Session lifecycle (start/heartbeat/end)
 * - Log queue with offline support
 * - Automatic retry on failure
 */

import { app } from 'electron';
import fs from 'fs';
import path from 'path';
import https from 'https';
import http from 'http';

// Configuration (can be overridden via environment)
const CONFIG = {
    centralServerUrl: process.env.CENTRAL_SERVER_URL || '',
    enabled: process.env.TELEMETRY_ENABLED !== 'false',
    heartbeatInterval: parseInt(process.env.TELEMETRY_HEARTBEAT_INTERVAL || '300') * 1000, // 5 min
    retryInterval: parseInt(process.env.TELEMETRY_RETRY_INTERVAL || '60') * 1000, // 1 min
    maxQueueSize: parseInt(process.env.TELEMETRY_MAX_QUEUE_SIZE || '1000'),
    batchSize: 50, // Send logs in batches of 50
};

// State
let installationId = null;
let apiKey = null;
let sessionId = null;
let heartbeatTimer = null;
let logQueue = [];
let isOnline = true;
let loggerRef = console;

/**
 * Get the telemetry data file path
 */
function getTelemetryFilePath() {
    const userDataPath = app.getPath('userData');
    return path.join(userDataPath, 'telemetry.json');
}

/**
 * Load saved telemetry credentials
 */
function loadCredentials() {
    try {
        const filePath = getTelemetryFilePath();
        if (fs.existsSync(filePath)) {
            const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
            installationId = data.installationId;
            apiKey = data.apiKey;
            loggerRef.info(`[Telemetry] Loaded credentials: ${installationId?.slice(0, 8)}...`);
            return true;
        }
    } catch (err) {
        loggerRef.error('[Telemetry] Failed to load credentials:', err.message);
    }
    return false;
}

/**
 * Save telemetry credentials
 */
function saveCredentials() {
    try {
        const filePath = getTelemetryFilePath();
        fs.writeFileSync(filePath, JSON.stringify({
            installationId,
            apiKey,
            savedAt: new Date().toISOString()
        }, null, 2));
        loggerRef.info('[Telemetry] Credentials saved');
    } catch (err) {
        loggerRef.error('[Telemetry] Failed to save credentials:', err.message);
    }
}

/**
 * Make HTTP request to Central Server
 */
function request(method, endpoint, data = null) {
    return new Promise((resolve, reject) => {
        if (!CONFIG.centralServerUrl) {
            reject(new Error('CENTRAL_SERVER_URL not configured'));
            return;
        }

        const url = new URL(endpoint, CONFIG.centralServerUrl);
        const isHttps = url.protocol === 'https:';
        const httpModule = isHttps ? https : http;

        const options = {
            hostname: url.hostname,
            port: url.port || (isHttps ? 443 : 80),
            path: url.pathname,
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            timeout: 30000,
        };

        // Add API key if we have one
        if (apiKey) {
            options.headers['x-api-key'] = apiKey;
        }

        const req = httpModule.request(options, (res) => {
            let body = '';
            res.on('data', chunk => body += chunk);
            res.on('end', () => {
                try {
                    const json = JSON.parse(body);
                    if (res.statusCode >= 200 && res.statusCode < 300) {
                        resolve(json);
                    } else {
                        reject(new Error(`HTTP ${res.statusCode}: ${json.detail || body}`));
                    }
                } catch (e) {
                    reject(new Error(`Invalid JSON response: ${body}`));
                }
            });
        });

        req.on('error', reject);
        req.on('timeout', () => {
            req.destroy();
            reject(new Error('Request timeout'));
        });

        if (data) {
            req.write(JSON.stringify(data));
        }
        req.end();
    });
}

/**
 * Register with Central Server (first launch)
 */
async function register() {
    if (installationId && apiKey) {
        loggerRef.info('[Telemetry] Already registered');
        return true;
    }

    try {
        const appVersion = app.getVersion();
        const data = await request('POST', '/api/v1/remote-logs/register', {
            installation_name: `LocaNext-${process.platform}`,
            version: appVersion,
            platform: process.platform,
            os_version: process.getSystemVersion ? process.getSystemVersion() : 'unknown'
        });

        installationId = data.installation_id;
        apiKey = data.api_key;
        saveCredentials();

        loggerRef.info(`[Telemetry] Registered: ${installationId.slice(0, 8)}...`);
        return true;
    } catch (err) {
        loggerRef.error('[Telemetry] Registration failed:', err.message);
        return false;
    }
}

/**
 * Start a new session
 */
async function startSession() {
    if (!installationId || !apiKey) {
        loggerRef.warning('[Telemetry] Cannot start session - not registered');
        return false;
    }

    try {
        const data = await request('POST', '/api/v1/remote-logs/sessions/start', {
            installation_id: installationId,
            version: app.getVersion()
        });

        sessionId = data.session_id;
        loggerRef.info(`[Telemetry] Session started: ${sessionId.slice(0, 8)}...`);

        // Start heartbeat timer
        startHeartbeat();
        return true;
    } catch (err) {
        loggerRef.error('[Telemetry] Session start failed:', err.message);
        return false;
    }
}

/**
 * Send heartbeat
 */
async function sendHeartbeat() {
    if (!sessionId) return;

    try {
        await request('POST', '/api/v1/remote-logs/sessions/heartbeat', {
            session_id: sessionId
        });
        loggerRef.debug?.('[Telemetry] Heartbeat sent') || loggerRef.info('[Telemetry] Heartbeat sent');

        // Also flush log queue on heartbeat
        await flushLogQueue();
    } catch (err) {
        loggerRef.warning?.('[Telemetry] Heartbeat failed:', err.message) || loggerRef.error('[Telemetry] Heartbeat failed:', err.message);
        isOnline = false;
    }
}

/**
 * Start heartbeat timer
 */
function startHeartbeat() {
    if (heartbeatTimer) {
        clearInterval(heartbeatTimer);
    }
    heartbeatTimer = setInterval(sendHeartbeat, CONFIG.heartbeatInterval);
}

/**
 * Stop heartbeat timer
 */
function stopHeartbeat() {
    if (heartbeatTimer) {
        clearInterval(heartbeatTimer);
        heartbeatTimer = null;
    }
}

/**
 * End the current session
 */
async function endSession(reason = 'user_closed') {
    stopHeartbeat();

    // Flush remaining logs
    await flushLogQueue();

    if (!sessionId) return;

    try {
        await request('POST', '/api/v1/remote-logs/sessions/end', {
            session_id: sessionId,
            end_reason: reason
        });
        loggerRef.info(`[Telemetry] Session ended: ${reason}`);
    } catch (err) {
        loggerRef.error('[Telemetry] Session end failed:', err.message);
    } finally {
        sessionId = null;
    }
}

/**
 * Add a log entry to the queue
 */
function queueLog(level, message, component = null, data = null) {
    if (!CONFIG.enabled || !installationId) return;

    // Enforce queue size limit
    if (logQueue.length >= CONFIG.maxQueueSize) {
        logQueue.shift(); // Remove oldest
    }

    logQueue.push({
        timestamp: new Date().toISOString(),
        level: level.toUpperCase(),
        message,
        source: 'desktop-app',
        component,
        installation_id: installationId,
        data
    });

    // Auto-flush if we have enough logs
    if (logQueue.length >= CONFIG.batchSize) {
        flushLogQueue().catch(() => {}); // Ignore errors, will retry
    }
}

/**
 * Flush the log queue to Central Server
 */
async function flushLogQueue() {
    if (!installationId || !apiKey || logQueue.length === 0) return;

    // Take a batch
    const batch = logQueue.splice(0, CONFIG.batchSize);

    try {
        await request('POST', '/api/v1/remote-logs/submit', {
            installation_id: installationId,
            logs: batch
        });
        loggerRef.debug?.(`[Telemetry] Flushed ${batch.length} logs`) || loggerRef.info(`[Telemetry] Flushed ${batch.length} logs`);
        isOnline = true;
    } catch (err) {
        // Put logs back in queue (at front)
        logQueue.unshift(...batch);
        loggerRef.warning?.(`[Telemetry] Flush failed, ${logQueue.length} logs queued`) || loggerRef.error(`[Telemetry] Flush failed, ${logQueue.length} logs queued`);
        isOnline = false;
    }
}

/**
 * Initialize telemetry client
 */
async function initializeTelemetry(customLogger = null) {
    if (customLogger) {
        loggerRef = customLogger;
    }

    if (!CONFIG.enabled) {
        loggerRef.info('[Telemetry] Disabled via config');
        return false;
    }

    if (!CONFIG.centralServerUrl) {
        loggerRef.info('[Telemetry] No CENTRAL_SERVER_URL configured - telemetry disabled');
        return false;
    }

    loggerRef.info(`[Telemetry] Initializing... (server: ${CONFIG.centralServerUrl})`);

    // Load existing credentials or register
    if (!loadCredentials()) {
        await register();
    }

    // Start session
    if (installationId && apiKey) {
        await startSession();
        return true;
    }

    return false;
}

/**
 * Shutdown telemetry client
 */
async function shutdownTelemetry() {
    loggerRef.info('[Telemetry] Shutting down...');
    await endSession('user_closed');
}

// Convenience logging methods
export const telemetryLog = {
    info: (message, component = null, data = null) => queueLog('INFO', message, component, data),
    success: (message, component = null, data = null) => queueLog('SUCCESS', message, component, data),
    warning: (message, component = null, data = null) => queueLog('WARNING', message, component, data),
    error: (message, component = null, data = null) => queueLog('ERROR', message, component, data),
    critical: (message, component = null, data = null) => queueLog('CRITICAL', message, component, data),
};

// Export state getter for debugging
export function getTelemetryState() {
    return {
        enabled: CONFIG.enabled,
        serverUrl: CONFIG.centralServerUrl,
        installationId: installationId ? installationId.slice(0, 8) + '...' : null,
        sessionId: sessionId ? sessionId.slice(0, 8) + '...' : null,
        queueSize: logQueue.length,
        isOnline
    };
}

export { initializeTelemetry, shutdownTelemetry, queueLog, flushLogQueue };
