#!/usr/bin/env node
/**
 * CDP Test Runner - Run a single test
 *
 * Usage:
 *   node run_test.js <app> <test> [environment]
 *
 * Examples:
 *   node run_test.js ldm file_upload dev     # Test LDM upload via API
 *   node run_test.js ldm file_upload app     # Test LDM upload in electron:dev
 *   node run_test.js ldm file_upload exe     # Test LDM upload in LocaNext.exe
 *
 * Available apps: xlstransfer, quicksearch, krsimilar, ldm
 */

const path = require('path');
const { spawn } = require('child_process');

const args = process.argv.slice(2);

if (args.length < 2) {
    console.log('Usage: node run_test.js <app> <test> [environment]');
    console.log('');
    console.log('Examples:');
    console.log('  node run_test.js ldm file_upload dev');
    console.log('  node run_test.js ldm file_upload exe');
    console.log('');
    console.log('Apps: xlstransfer, quicksearch, krsimilar, ldm');
    console.log('Environments: dev (API), app (electron:dev), exe (LocaNext.exe)');
    process.exit(1);
}

const [app, test, env = 'exe'] = args;
const testFile = path.join(__dirname, '..', 'apps', app, `test_${test}.js`);

console.log(`Running: ${app}/${test} in ${env} mode`);
console.log(`File: ${testFile}`);
console.log('');

const child = spawn('node', [testFile, env], {
    stdio: 'inherit',
    cwd: path.join(__dirname, '..')
});

child.on('close', (code) => {
    process.exit(code);
});
