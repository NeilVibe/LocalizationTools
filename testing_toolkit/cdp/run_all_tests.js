#!/usr/bin/env node
/**
 * Master Test Runner - CDP Tests
 *
 * Runs all CDP tests in sequence with comprehensive logging.
 * Captures console errors, network failures, and exceptions.
 *
 * Usage (from Windows PowerShell):
 *   $env:CDP_TEST_USER="your_user"; $env:CDP_TEST_PASS="your_pass"
 *   node run_all_tests.js [--quick] [--verbose]
 *
 * Options:
 *   --quick    Run only essential tests (login, quick_check, test_qa)
 *   --verbose  Show all console output
 *   --fail-fast Stop on first failure
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// ANSI colors
const C = {
    reset: '\x1b[0m',
    bright: '\x1b[1m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    cyan: '\x1b[36m',
    bgRed: '\x1b[41m',
    bgGreen: '\x1b[42m',
    bgYellow: '\x1b[43m'
};

// Test definitions - order matters!
const ALL_TESTS = [
    // Essential tests (always run first)
    { name: 'login.js', category: 'essential', desc: 'Login to app' },
    { name: 'quick_check.js', category: 'essential', desc: 'Page state check' },

    // Core functionality
    { name: 'test_qa.js', category: 'core', desc: 'QA basic test' },
    { name: 'test_qa_comprehensive.js', category: 'core', desc: 'QA comprehensive' },
    { name: 'create_project_upload.js', category: 'core', desc: 'Project creation + upload' },
    { name: 'upload_file.js', category: 'core', desc: 'File upload' },
    { name: 'test_file_download.js', category: 'core', desc: 'File download' },

    // TM tests
    { name: 'test_full_tm_sync.js', category: 'tm', desc: 'TM full sync' },
    { name: 'test_auto_sync.js', category: 'tm', desc: 'TM auto sync' },
    { name: 'test_ui047_tm_status.js', category: 'tm', desc: 'TM status UI' },

    // Bug verification
    { name: 'test_bug023.js', category: 'bugs', desc: 'Bug 023 - TM status' },
    { name: 'test_bug023_build.js', category: 'bugs', desc: 'Bug 023 - TM build' },
    { name: 'test_bug029.js', category: 'bugs', desc: 'Bug 029 - Upload as TM' },

    // UI verification
    { name: 'verify_font_fix.js', category: 'ui', desc: 'Font fix verification' },
    { name: 'verify_tooltip.js', category: 'ui', desc: 'Tooltip verification' },
    { name: 'verify_ui027_no_confirm.js', category: 'ui', desc: 'UI 027 - no confirm' },
    { name: 'verify_ui031_ui032.js', category: 'ui', desc: 'UI 031/032' },
    { name: 'verify_ui034_tooltips.js', category: 'ui', desc: 'UI 034 tooltips' },
    { name: 'verify_build_308.js', category: 'ui', desc: 'Build 308 verification' },

    // Settings & debugging
    { name: 'check_all_settings.js', category: 'debug', desc: 'All settings' },
    { name: 'check_display_settings.js', category: 'debug', desc: 'Display settings' },
    { name: 'check_console_errors.js', category: 'debug', desc: 'Console errors' },
    { name: 'check_network.js', category: 'debug', desc: 'Network check' },
    { name: 'check_server_status.js', category: 'debug', desc: 'Server status' },
    { name: 'test_server_status.js', category: 'debug', desc: 'Server status test' },
    { name: 'test_font_settings.js', category: 'debug', desc: 'Font settings' },

    // Cleanup
    { name: 'test_clean_slate.js', category: 'cleanup', desc: 'Clean slate' },
    { name: 'close_modal.js', category: 'cleanup', desc: 'Close modals' },
];

const QUICK_TESTS = ALL_TESTS.filter(t => t.category === 'essential' || t.category === 'core');

class TestRunner {
    constructor(options = {}) {
        this.options = {
            quick: options.quick || false,
            verbose: options.verbose || false,
            failFast: options.failFast || false,
            ...options
        };
        this.results = [];
        this.startTime = Date.now();
    }

    log(msg) {
        const ts = new Date().toISOString().substring(11, 23);
        console.log(`${C.cyan}[${ts}]${C.reset} ${msg}`);
    }

    async runTest(test) {
        const testPath = path.join(__dirname, test.name);

        // Check if test file exists
        if (!fs.existsSync(testPath)) {
            return { name: test.name, status: 'skipped', reason: 'File not found', duration: 0 };
        }

        return new Promise((resolve) => {
            const start = Date.now();
            let stdout = '';
            let stderr = '';

            const proc = spawn('node', [testPath], {
                cwd: __dirname,
                env: process.env,
                timeout: 120000 // 2 minute timeout per test
            });

            proc.stdout.on('data', (data) => {
                stdout += data.toString();
                if (this.options.verbose) {
                    process.stdout.write(data);
                }
            });

            proc.stderr.on('data', (data) => {
                stderr += data.toString();
                if (this.options.verbose) {
                    process.stderr.write(data);
                }
            });

            proc.on('close', (code) => {
                const duration = Date.now() - start;
                const status = code === 0 ? 'pass' : 'fail';

                resolve({
                    name: test.name,
                    desc: test.desc,
                    category: test.category,
                    status,
                    code,
                    duration,
                    stdout: stdout.trim(),
                    stderr: stderr.trim(),
                    errors: this.extractErrors(stdout + stderr)
                });
            });

            proc.on('error', (err) => {
                resolve({
                    name: test.name,
                    desc: test.desc,
                    category: test.category,
                    status: 'error',
                    duration: Date.now() - start,
                    error: err.message
                });
            });
        });
    }

    extractErrors(output) {
        const errors = [];
        const lines = output.split('\n');

        for (const line of lines) {
            if (line.includes('Error:') ||
                line.includes('FAIL') ||
                line.includes('Cannot read properties') ||
                line.includes('undefined') && line.includes('reading')) {
                errors.push(line.trim());
            }
        }

        return errors;
    }

    printHeader() {
        console.log('\n' + '═'.repeat(70));
        console.log(`${C.bright}${C.cyan}  CDP TEST RUNNER - LocaNext${C.reset}`);
        console.log(`${C.cyan}  Mode: ${this.options.quick ? 'QUICK' : 'FULL'} | Verbose: ${this.options.verbose ? 'ON' : 'OFF'}${C.reset}`);
        console.log('═'.repeat(70) + '\n');
    }

    printResult(result) {
        const statusIcon = {
            pass: `${C.green}✔${C.reset}`,
            fail: `${C.red}✖${C.reset}`,
            skipped: `${C.yellow}○${C.reset}`,
            error: `${C.red}⚠${C.reset}`
        };

        const duration = `${(result.duration / 1000).toFixed(1)}s`;
        const status = result.status.toUpperCase().padEnd(4);

        console.log(
            `${statusIcon[result.status]} ${C.bright}${status}${C.reset} ` +
            `${result.name.padEnd(30)} ` +
            `${C.cyan}${duration.padStart(6)}${C.reset} ` +
            `${C.dim}${result.desc || ''}${C.reset}`
        );

        if (result.status === 'fail' && result.errors.length > 0 && !this.options.verbose) {
            for (const error of result.errors.slice(0, 3)) {
                console.log(`  ${C.red}└─ ${error.substring(0, 70)}${C.reset}`);
            }
        }
    }

    printSummary() {
        const passed = this.results.filter(r => r.status === 'pass').length;
        const failed = this.results.filter(r => r.status === 'fail').length;
        const skipped = this.results.filter(r => r.status === 'skipped').length;
        const errors = this.results.filter(r => r.status === 'error').length;
        const total = this.results.length;
        const duration = ((Date.now() - this.startTime) / 1000).toFixed(1);

        console.log('\n' + '─'.repeat(70));
        console.log(`\n${C.bright}TEST SUMMARY${C.reset}\n`);

        console.log(`  ${C.green}Passed:${C.reset}  ${passed}/${total}`);
        console.log(`  ${C.red}Failed:${C.reset}  ${failed}/${total}`);
        if (skipped > 0) console.log(`  ${C.yellow}Skipped:${C.reset} ${skipped}`);
        if (errors > 0) console.log(`  ${C.red}Errors:${C.reset}  ${errors}`);
        console.log(`  ${C.cyan}Duration:${C.reset} ${duration}s`);

        // List all failures
        const failures = this.results.filter(r => r.status === 'fail' || r.status === 'error');
        if (failures.length > 0) {
            console.log(`\n${C.red}${C.bright}FAILURES:${C.reset}`);
            for (const f of failures) {
                console.log(`  ${C.red}• ${f.name}${C.reset}`);
                for (const err of (f.errors || []).slice(0, 2)) {
                    console.log(`    ${C.dim}${err.substring(0, 60)}${C.reset}`);
                }
            }
        }

        // Collect all unique errors across all tests
        const allErrors = new Set();
        for (const r of this.results) {
            for (const err of (r.errors || [])) {
                if (err.includes('Cannot read properties') ||
                    err.includes('undefined') ||
                    err.includes('Error:')) {
                    allErrors.add(err);
                }
            }
        }

        if (allErrors.size > 0) {
            console.log(`\n${C.yellow}${C.bright}ALL DETECTED ERRORS (${allErrors.size}):${C.reset}`);
            let i = 1;
            for (const err of allErrors) {
                console.log(`  ${i++}. ${err.substring(0, 80)}`);
            }
        }

        console.log('\n' + '═'.repeat(70) + '\n');

        // Return exit code
        return failed + errors > 0 ? 1 : 0;
    }

    async run() {
        this.printHeader();

        // Check credentials
        if (!process.env.CDP_TEST_USER || !process.env.CDP_TEST_PASS) {
            console.log(`${C.red}ERROR: CDP_TEST_USER and CDP_TEST_PASS environment variables required!${C.reset}`);
            console.log(`\nSet credentials and try again:`);
            console.log(`  $env:CDP_TEST_USER="username"; $env:CDP_TEST_PASS="password"`);
            process.exit(1);
        }

        const tests = this.options.quick ? QUICK_TESTS : ALL_TESTS;
        this.log(`Running ${tests.length} tests...\n`);

        for (const test of tests) {
            const result = await this.runTest(test);
            this.results.push(result);
            this.printResult(result);

            if (this.options.failFast && (result.status === 'fail' || result.status === 'error')) {
                console.log(`\n${C.red}Stopping on first failure (--fail-fast)${C.reset}`);
                break;
            }

            // Small delay between tests to prevent overwhelming CDP
            await new Promise(r => setTimeout(r, 500));
        }

        return this.printSummary();
    }
}

// Parse args and run
const args = process.argv.slice(2);
const options = {
    quick: args.includes('--quick'),
    verbose: args.includes('--verbose'),
    failFast: args.includes('--fail-fast')
};

const runner = new TestRunner(options);
runner.run().then(code => process.exit(code));
