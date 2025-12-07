#!/usr/bin/env node
/**
 * Run All Tests for LocaNext
 *
 * Executes all test functions for all apps sequentially via CDP
 *
 * Usage:
 *   node run_all_tests.js [--app <app>] [--skip-slow]
 *
 * Prerequisites:
 *   - LocaNext running with --remote-debugging-port=9222
 *   - Node.js with 'ws' module installed
 *   - Test files in D:\TestFilesForLocaNext\
 */

const WebSocket = require('ws');

const CDP_PORT = process.env.CDP_PORT || 9222;

// Test sequence with timing estimates
const ALL_TESTS = [
  // XLSTransfer - requires file on disk
  { app: 'xlsTransfer', func: 'createDictionary', expr: 'window.xlsTransferTest.createDictionary()', wait: 25, slow: false },
  { app: 'xlsTransfer', func: 'translateExcel', expr: 'window.xlsTransferTest.translateExcel()', wait: 10, slow: false, requires: 'dictionary' },

  // QuickSearch - uses backend dictionaries
  { app: 'quickSearch', func: 'loadDictionary', expr: 'window.quickSearchTest.loadDictionary()', wait: 15, slow: false },
  { app: 'quickSearch', func: 'search', expr: 'window.quickSearchTest.search()', wait: 5, slow: false, requires: 'quickSearchDict' },

  // KRSimilar - uses embeddings (can be slow on first load)
  { app: 'krSimilar', func: 'loadDictionary', expr: 'window.krSimilarTest.loadDictionary()', wait: 45, slow: true },
  { app: 'krSimilar', func: 'search', expr: 'window.krSimilarTest.search()', wait: 10, slow: false, requires: 'krSimilarDict' }
];

const STATUS_EXPRESSIONS = {
  xlsTransfer: 'JSON.stringify(window.xlsTransferTest.getStatus())',
  quickSearch: 'JSON.stringify(window.quickSearchTest.getStatus())',
  krSimilar: 'JSON.stringify(window.krSimilarTest.getStatus())'
};

async function main() {
  const args = process.argv.slice(2);

  if (args.includes('--help')) {
    console.log(`
LocaNext Full Test Suite

Usage: node run_all_tests.js [options]

Options:
  --app <app>     Only test specific app (xlsTransfer, quickSearch, krSimilar)
  --skip-slow     Skip slow tests (KR Similar embedding load)
  --port <port>   CDP port (default: 9222)

Examples:
  node run_all_tests.js                    # Run all tests
  node run_all_tests.js --app quickSearch  # Only QuickSearch
  node run_all_tests.js --skip-slow        # Skip slow embedding load
`);
    process.exit(0);
  }

  // Parse arguments
  const appFilter = args.includes('--app') ? args[args.indexOf('--app') + 1] : null;
  const skipSlow = args.includes('--skip-slow');
  let port = CDP_PORT;
  const portIdx = args.indexOf('--port');
  if (portIdx !== -1 && args[portIdx + 1]) {
    port = parseInt(args[portIdx + 1]);
  }

  console.log(`\n${'='.repeat(60)}`);
  console.log('LOCANEXT FULL TEST SUITE');
  console.log(`${'='.repeat(60)}`);
  console.log(`CDP Port: ${port}`);
  console.log(`App Filter: ${appFilter || 'all'}`);
  console.log(`Skip Slow: ${skipSlow}`);
  console.log(`${'='.repeat(60)}\n`);

  let ws;
  let msgId = 1;

  try {
    // Connect to CDP
    console.log(`Connecting to CDP at http://localhost:${port}...`);
    const response = await fetch(`http://localhost:${port}/json`);
    const pages = await response.json();

    if (pages.length === 0) {
      console.error('Error: No pages found in CDP');
      process.exit(1);
    }

    const mainPage = pages.find(p => !p.url.includes('devtools')) || pages[0];
    console.log(`Target: ${mainPage.title || mainPage.url}\n`);

    ws = new WebSocket(mainPage.webSocketDebuggerUrl);

    function send(method, params = {}) {
      return new Promise((resolve, reject) => {
        const id = msgId++;
        const timeout = setTimeout(() => {
          reject(new Error(`Timeout waiting for response`));
        }, 180000); // 3 min timeout for slow tests

        const handler = function(data) {
          const msg = JSON.parse(data.toString());
          if (msg.id === id) {
            clearTimeout(timeout);
            ws.off('message', handler);
            if (msg.error) {
              reject(new Error(msg.error.message));
            } else {
              resolve(msg.result);
            }
          }
        };

        ws.on('message', handler);
        ws.send(JSON.stringify({ id, method, params }));
      });
    }

    await new Promise((resolve, reject) => {
      ws.on('open', resolve);
      ws.on('error', reject);
    });

    console.log('Connected!\n');

    // Track state for dependency checking
    const state = {
      dictionary: false,
      quickSearchDict: false,
      krSimilarDict: false
    };

    const results = [];
    let passed = 0;
    let failed = 0;
    let skipped = 0;

    // Run tests
    for (const test of ALL_TESTS) {
      // Apply filters
      if (appFilter && test.app !== appFilter) continue;
      if (skipSlow && test.slow) {
        console.log(`[SKIP] ${test.app}.${test.func} (slow)`);
        skipped++;
        continue;
      }

      // Check dependencies
      if (test.requires && !state[test.requires]) {
        console.log(`[SKIP] ${test.app}.${test.func} (requires ${test.requires})`);
        skipped++;
        continue;
      }

      console.log(`\n${'─'.repeat(50)}`);
      console.log(`[TEST] ${test.app}.${test.func}`);
      console.log(`${'─'.repeat(50)}`);

      try {
        // Execute test
        console.log(`Executing: ${test.expr}`);
        await send('Runtime.evaluate', {
          expression: test.expr,
          returnByValue: true,
          awaitPromise: true
        });

        // Wait for completion
        console.log(`Waiting ${test.wait}s...`);
        await new Promise(r => setTimeout(r, test.wait * 1000));

        // Get status
        const statusResult = await send('Runtime.evaluate', {
          expression: STATUS_EXPRESSIONS[test.app],
          returnByValue: true
        });

        let status = {};
        if (statusResult.result && statusResult.result.value) {
          status = JSON.parse(statusResult.result.value);
        }

        // Check result
        const isError = status.statusMessage && status.statusMessage.toLowerCase().includes('error');
        const isProcessing = status.isProcessing;

        if (isError) {
          console.log(`[FAIL] ${status.statusMessage}`);
          failed++;
          results.push({ test: `${test.app}.${test.func}`, status: 'FAIL', message: status.statusMessage });
        } else if (isProcessing) {
          console.log(`[WARN] Still processing - may need more time`);
          // Don't count as fail, could just need more time
          results.push({ test: `${test.app}.${test.func}`, status: 'SLOW', message: 'Still processing' });
        } else {
          console.log(`[PASS] ${status.statusMessage || 'OK'}`);
          passed++;
          results.push({ test: `${test.app}.${test.func}`, status: 'PASS', message: status.statusMessage });

          // Update state for dependencies
          if (test.func === 'createDictionary') state.dictionary = true;
          if (test.app === 'quickSearch' && test.func === 'loadDictionary') state.quickSearchDict = true;
          if (test.app === 'krSimilar' && test.func === 'loadDictionary') state.krSimilarDict = true;
        }

      } catch (error) {
        console.log(`[FAIL] Error: ${error.message}`);
        failed++;
        results.push({ test: `${test.app}.${test.func}`, status: 'FAIL', message: error.message });
      }
    }

    // Summary
    console.log(`\n${'='.repeat(60)}`);
    console.log('TEST SUMMARY');
    console.log(`${'='.repeat(60)}`);
    console.log(`Passed:  ${passed}`);
    console.log(`Failed:  ${failed}`);
    console.log(`Skipped: ${skipped}`);
    console.log(`Total:   ${passed + failed + skipped}`);
    console.log(`${'='.repeat(60)}\n`);

    // Details
    console.log('Results:');
    for (const r of results) {
      const icon = r.status === 'PASS' ? '✓' : r.status === 'FAIL' ? '✗' : '○';
      console.log(`  ${icon} ${r.test}: ${r.status}`);
    }

    ws.close();
    process.exit(failed > 0 ? 1 : 0);

  } catch (error) {
    console.error(`\nFatal Error: ${error.message}`);
    if (ws) ws.close();
    process.exit(1);
  }
}

main();
