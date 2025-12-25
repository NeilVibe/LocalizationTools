/**
 * CDP Client Library with Live DevTools Logging
 *
 * Provides:
 * - WebSocket connection to CDP
 * - Live console logging from browser
 * - Network request/response logging
 * - Error capture and reporting
 * - Screenshot capture
 */

const WebSocket = require('ws');
const http = require('http');
const fs = require('fs');
const path = require('path');

const CDP_URL = 'http://127.0.0.1:9222';

// ANSI color codes for terminal output
const colors = {
    reset: '\x1b[0m',
    bright: '\x1b[1m',
    dim: '\x1b[2m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    magenta: '\x1b[35m',
    cyan: '\x1b[36m',
    white: '\x1b[37m',
    bgRed: '\x1b[41m',
    bgGreen: '\x1b[42m',
    bgYellow: '\x1b[43m'
};

class CDPClient {
    constructor(options = {}) {
        this.ws = null;
        this.id = 1;
        this.callbacks = new Map();
        this.options = {
            enableConsoleLog: options.enableConsoleLog ?? true,
            enableNetworkLog: options.enableNetworkLog ?? false,
            enableErrorCapture: options.enableErrorCapture ?? true,
            screenshotDir: options.screenshotDir || path.join(__dirname, '..', 'screenshots'),
            verbose: options.verbose ?? false,
            ...options
        };
        this.errors = [];
        this.consoleMessages = [];
        this.networkRequests = [];
    }

    /**
     * Log with timestamp and color
     */
    log(level, ...args) {
        const timestamp = new Date().toISOString().substring(11, 23);
        const prefix = {
            info: `${colors.cyan}[${timestamp}]${colors.reset} ${colors.blue}ℹ${colors.reset}`,
            warn: `${colors.yellow}[${timestamp}]${colors.reset} ${colors.yellow}⚠${colors.reset}`,
            error: `${colors.red}[${timestamp}]${colors.reset} ${colors.red}✖${colors.reset}`,
            success: `${colors.green}[${timestamp}]${colors.reset} ${colors.green}✔${colors.reset}`,
            debug: `${colors.dim}[${timestamp}]${colors.reset} ${colors.dim}●${colors.reset}`,
            console: `${colors.magenta}[${timestamp}]${colors.reset} ${colors.magenta}»${colors.reset}`,
            network: `${colors.cyan}[${timestamp}]${colors.reset} ${colors.cyan}↔${colors.reset}`
        };
        console.log(prefix[level] || prefix.info, ...args);
    }

    /**
     * Get CDP targets from browser
     */
    async getTargets() {
        return new Promise((resolve, reject) => {
            const req = http.get(`${CDP_URL}/json`, (res) => {
                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => {
                    try {
                        resolve(JSON.parse(data));
                    } catch (e) {
                        reject(new Error(`Failed to parse CDP targets: ${e.message}`));
                    }
                });
            });
            req.on('error', (e) => {
                reject(new Error(`CDP connection failed (is the app running with --remote-debugging-port=9222?): ${e.message}`));
            });
            req.setTimeout(5000, () => {
                req.destroy();
                reject(new Error('CDP connection timeout - is LocaNext.exe running?'));
            });
        });
    }

    /**
     * Connect to CDP target
     */
    async connect() {
        this.log('info', 'Connecting to CDP...');

        const targets = await this.getTargets();
        const page = targets.find(t => t.type === 'page');

        if (!page) {
            throw new Error('No CDP page target found - is the app showing a window?');
        }

        this.log('info', `Found page: ${page.title || page.url}`);

        return new Promise((resolve, reject) => {
            this.ws = new WebSocket(page.webSocketDebuggerUrl);

            this.ws.on('open', async () => {
                this.log('success', 'CDP WebSocket connected');

                // Enable domains for logging
                await this.send('Runtime.enable');

                if (this.options.enableConsoleLog) {
                    await this.send('Console.enable');
                }

                if (this.options.enableNetworkLog) {
                    await this.send('Network.enable');
                }

                if (this.options.enableErrorCapture) {
                    await this.send('Log.enable');
                }

                resolve();
            });

            this.ws.on('error', (err) => {
                this.log('error', `WebSocket error: ${err.message}`);
                reject(err);
            });

            this.ws.on('message', (data) => {
                this.handleMessage(JSON.parse(data.toString()));
            });

            this.ws.on('close', () => {
                this.log('info', 'CDP WebSocket closed');
            });
        });
    }

    /**
     * Handle incoming CDP messages
     */
    handleMessage(msg) {
        // Handle responses to our commands
        if (msg.id && this.callbacks.has(msg.id)) {
            this.callbacks.get(msg.id)(msg);
            this.callbacks.delete(msg.id);
            return;
        }

        // Handle events
        if (msg.method) {
            this.handleEvent(msg.method, msg.params);
        }
    }

    /**
     * Handle CDP events (console, network, errors)
     */
    handleEvent(method, params) {
        switch (method) {
            case 'Console.messageAdded':
            case 'Runtime.consoleAPICalled':
                if (this.options.enableConsoleLog) {
                    this.handleConsoleMessage(params);
                }
                break;

            case 'Runtime.exceptionThrown':
                this.handleException(params);
                break;

            case 'Log.entryAdded':
                if (this.options.enableErrorCapture) {
                    this.handleLogEntry(params);
                }
                break;

            case 'Network.requestWillBeSent':
                if (this.options.enableNetworkLog) {
                    this.handleNetworkRequest(params);
                }
                break;

            case 'Network.responseReceived':
                if (this.options.enableNetworkLog) {
                    this.handleNetworkResponse(params);
                }
                break;

            default:
                if (this.options.verbose) {
                    this.log('debug', `Event: ${method}`);
                }
        }
    }

    /**
     * Handle console messages from the browser
     */
    handleConsoleMessage(params) {
        let text = '';
        let level = 'log';

        if (params.message) {
            text = params.message.text || params.message;
            level = params.message.level || 'log';
        } else if (params.args) {
            text = params.args.map(arg => arg.value || arg.description || '').join(' ');
            level = params.type || 'log';
        }

        if (!text) return;

        this.consoleMessages.push({ level, text, timestamp: Date.now() });

        const levelColors = {
            log: colors.white,
            info: colors.blue,
            warn: colors.yellow,
            error: colors.red,
            debug: colors.dim
        };

        const color = levelColors[level] || colors.white;
        this.log('console', `${color}[${level.toUpperCase()}]${colors.reset} ${text}`);

        // Track errors
        if (level === 'error') {
            this.errors.push({ type: 'console', message: text, timestamp: Date.now() });
        }
    }

    /**
     * Handle JavaScript exceptions
     */
    handleException(params) {
        const exception = params.exceptionDetails;
        const message = exception.exception?.description || exception.text || 'Unknown error';

        this.log('error', `${colors.bgRed}${colors.white} EXCEPTION ${colors.reset} ${message}`);

        if (exception.stackTrace) {
            for (const frame of exception.stackTrace.callFrames.slice(0, 5)) {
                this.log('error', `  at ${frame.functionName || '(anonymous)'} (${frame.url}:${frame.lineNumber}:${frame.columnNumber})`);
            }
        }

        this.errors.push({
            type: 'exception',
            message,
            stack: exception.stackTrace,
            timestamp: Date.now()
        });
    }

    /**
     * Handle log entries (browser-level logs)
     */
    handleLogEntry(params) {
        const entry = params.entry;
        const level = entry.level || 'info';
        const text = entry.text || '';

        if (level === 'error' || level === 'warning') {
            this.log(level === 'error' ? 'error' : 'warn', `[Browser] ${text}`);

            if (level === 'error') {
                this.errors.push({ type: 'browser', message: text, timestamp: Date.now() });
            }
        }
    }

    /**
     * Handle network requests
     */
    handleNetworkRequest(params) {
        const req = params.request;
        this.networkRequests.push({
            requestId: params.requestId,
            method: req.method,
            url: req.url,
            timestamp: Date.now()
        });

        if (this.options.verbose) {
            this.log('network', `→ ${req.method} ${req.url}`);
        }
    }

    /**
     * Handle network responses
     */
    handleNetworkResponse(params) {
        const resp = params.response;
        const request = this.networkRequests.find(r => r.requestId === params.requestId);

        if (request) {
            request.status = resp.status;
            request.responseTime = Date.now() - request.timestamp;
        }

        const statusColor = resp.status >= 400 ? colors.red : resp.status >= 300 ? colors.yellow : colors.green;

        if (this.options.verbose || resp.status >= 400) {
            this.log('network', `← ${statusColor}${resp.status}${colors.reset} ${resp.url.substring(0, 80)}${resp.url.length > 80 ? '...' : ''}`);
        }

        if (resp.status >= 500) {
            this.errors.push({
                type: 'network',
                message: `HTTP ${resp.status}: ${resp.url}`,
                timestamp: Date.now()
            });
        }
    }

    /**
     * Send CDP command and wait for response
     */
    async send(method, params = {}) {
        return new Promise((resolve, reject) => {
            const id = this.id++;

            this.callbacks.set(id, (response) => {
                if (response.error) {
                    reject(new Error(`CDP ${method} failed: ${response.error.message}`));
                } else {
                    resolve(response);
                }
            });

            this.ws.send(JSON.stringify({ id, method, params }));

            // Timeout after 30 seconds
            setTimeout(() => {
                if (this.callbacks.has(id)) {
                    this.callbacks.delete(id);
                    reject(new Error(`CDP ${method} timeout`));
                }
            }, 30000);
        });
    }

    /**
     * Evaluate JavaScript in the browser context
     */
    async evaluate(expression, options = {}) {
        const result = await this.send('Runtime.evaluate', {
            expression,
            returnByValue: true,
            awaitPromise: options.awaitPromise ?? true,
            ...options
        });

        if (result.result?.exceptionDetails) {
            const error = result.result.exceptionDetails;
            throw new Error(`Evaluation failed: ${error.exception?.description || error.text}`);
        }

        return result.result?.result?.value;
    }

    /**
     * Wait for an element to appear
     */
    async waitForSelector(selector, timeout = 10000) {
        const start = Date.now();
        while (Date.now() - start < timeout) {
            const exists = await this.evaluate(`!!document.querySelector('${selector}')`);
            if (exists) return true;
            await this.sleep(200);
        }
        return false;
    }

    /**
     * Click an element
     */
    async click(selector) {
        await this.evaluate(`
            const el = document.querySelector('${selector}');
            if (el) el.click();
            else throw new Error('Element not found: ${selector}');
        `);
    }

    /**
     * Type text into an input
     */
    async type(selector, text) {
        await this.evaluate(`
            const el = document.querySelector('${selector}');
            if (el) {
                el.value = ${JSON.stringify(text)};
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            } else {
                throw new Error('Element not found: ${selector}');
            }
        `);
    }

    /**
     * Take a screenshot
     */
    async screenshot(name = 'screenshot') {
        const result = await this.send('Page.captureScreenshot', { format: 'png' });

        if (!fs.existsSync(this.options.screenshotDir)) {
            fs.mkdirSync(this.options.screenshotDir, { recursive: true });
        }

        const filename = `${name}_${Date.now()}.png`;
        const filepath = path.join(this.options.screenshotDir, filename);

        fs.writeFileSync(filepath, Buffer.from(result.result.data, 'base64'));
        this.log('info', `Screenshot saved: ${filepath}`);

        return filepath;
    }

    /**
     * Get page content
     */
    async getPageText() {
        return await this.evaluate('document.body.innerText');
    }

    /**
     * Get current URL
     */
    async getUrl() {
        return await this.evaluate('window.location.href');
    }

    /**
     * Sleep helper
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Get error summary
     */
    getErrorSummary() {
        return {
            total: this.errors.length,
            exceptions: this.errors.filter(e => e.type === 'exception').length,
            consoleErrors: this.errors.filter(e => e.type === 'console').length,
            networkErrors: this.errors.filter(e => e.type === 'network').length,
            browserErrors: this.errors.filter(e => e.type === 'browser').length,
            errors: this.errors
        };
    }

    /**
     * Print test results
     */
    printResults(testName, passed, details = '') {
        if (passed) {
            console.log(`\n${colors.bgGreen}${colors.white} PASS ${colors.reset} ${testName}`);
        } else {
            console.log(`\n${colors.bgRed}${colors.white} FAIL ${colors.reset} ${testName}`);
        }
        if (details) {
            console.log(`  ${colors.dim}${details}${colors.reset}`);
        }
    }

    /**
     * Close connection
     */
    close() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}

module.exports = { CDPClient, colors };
