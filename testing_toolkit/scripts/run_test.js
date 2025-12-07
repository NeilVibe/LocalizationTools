#!/usr/bin/env node
/**
 * CDP Test Runner for LocaNext
 *
 * Executes test functions via Chrome DevTools Protocol
 *
 * Usage:
 *   node run_test.js <app>.<function>
 *   node run_test.js xlsTransfer.createDictionary
 *   node run_test.js quickSearch.loadDictionary
 *   node run_test.js krSimilar.search
 *
 * Prerequisites:
 *   - LocaNext running with --remote-debugging-port=9222
 *   - Node.js with 'ws' module installed
 */

const WebSocket = require('ws');

// Available test functions
const TEST_FUNCTIONS = {
  xlsTransfer: {
    createDictionary: 'window.xlsTransferTest.createDictionary()',
    loadDictionary: 'window.xlsTransferTest.loadDictionary()',
    translateExcel: 'window.xlsTransferTest.translateExcel()',
    transferToClose: 'window.xlsTransferTest.transferToClose()',
    getStatus: 'JSON.stringify(window.xlsTransferTest.getStatus())'
  },
  quickSearch: {
    loadDictionary: 'window.quickSearchTest.loadDictionary()',
    search: 'window.quickSearchTest.search()',
    getStatus: 'JSON.stringify(window.quickSearchTest.getStatus())'
  },
  krSimilar: {
    loadDictionary: 'window.krSimilarTest.loadDictionary()',
    search: 'window.krSimilarTest.search()',
    getStatus: 'JSON.stringify(window.krSimilarTest.getStatus())'
  }
};

const CDP_PORT = process.env.CDP_PORT || 9222;
const TIMEOUT_MS = parseInt(process.env.TIMEOUT_MS) || 120000;

async function main() {
  const args = process.argv.slice(2);

  if (args.length === 0 || args[0] === '--help') {
    console.log(`
LocaNext CDP Test Runner

Usage: node run_test.js <app>.<function> [--wait <seconds>]

Available tests:
  xlsTransfer.createDictionary  Create dictionary from test file (~20s)
  xlsTransfer.loadDictionary    Load existing dictionary
  xlsTransfer.translateExcel    Translate Excel file (~5s)
  xlsTransfer.transferToClose   Transfer to Close tool
  xlsTransfer.getStatus         Get current status

  quickSearch.loadDictionary    Load BDO_EN dictionary (~10s)
  quickSearch.search            Search for test query
  quickSearch.getStatus         Get current status

  krSimilar.loadDictionary      Load BDO embeddings (~30s)
  krSimilar.search              Find similar texts
  krSimilar.getStatus           Get current status

Options:
  --wait <seconds>              Wait after execution (default: 5)
  --port <port>                 CDP port (default: 9222)

Examples:
  node run_test.js xlsTransfer.createDictionary
  node run_test.js quickSearch.loadDictionary --wait 20
`);
    process.exit(0);
  }

  // Parse arguments
  const testArg = args[0];
  const parts = testArg.split('.');

  if (parts.length !== 2) {
    console.error(`Error: Invalid format. Use <app>.<function>`);
    process.exit(1);
  }

  const [appName, funcName] = parts;

  if (!TEST_FUNCTIONS[appName]) {
    console.error(`Error: Unknown app '${appName}'. Use: xlsTransfer, quickSearch, krSimilar`);
    process.exit(1);
  }

  if (!TEST_FUNCTIONS[appName][funcName]) {
    console.error(`Error: Unknown function '${funcName}' for ${appName}`);
    console.error(`Available: ${Object.keys(TEST_FUNCTIONS[appName]).join(', ')}`);
    process.exit(1);
  }

  // Parse wait time
  let waitTime = 5;
  const waitIdx = args.indexOf('--wait');
  if (waitIdx !== -1 && args[waitIdx + 1]) {
    waitTime = parseInt(args[waitIdx + 1]);
  }

  // Parse port
  let port = CDP_PORT;
  const portIdx = args.indexOf('--port');
  if (portIdx !== -1 && args[portIdx + 1]) {
    port = parseInt(args[portIdx + 1]);
  }

  const expression = TEST_FUNCTIONS[appName][funcName];

  console.log(`\n=== LocaNext CDP Test Runner ===`);
  console.log(`App: ${appName}`);
  console.log(`Function: ${funcName}`);
  console.log(`CDP Port: ${port}`);
  console.log(`Wait after: ${waitTime}s`);
  console.log(`Expression: ${expression}\n`);

  try {
    // Get WebSocket URL from CDP
    console.log(`Connecting to CDP at http://localhost:${port}...`);
    const response = await fetch(`http://localhost:${port}/json`);
    const pages = await response.json();

    if (pages.length === 0) {
      console.error('Error: No pages found in CDP');
      process.exit(1);
    }

    // Find the main page (not devtools)
    const mainPage = pages.find(p => !p.url.includes('devtools')) || pages[0];
    console.log(`Target: ${mainPage.title || mainPage.url}`);

    // Connect via WebSocket
    const ws = new WebSocket(mainPage.webSocketDebuggerUrl);
    let msgId = 1;

    function send(method, params = {}) {
      return new Promise((resolve, reject) => {
        const id = msgId++;
        const timeout = setTimeout(() => {
          reject(new Error(`Timeout waiting for response to ${method}`));
        }, TIMEOUT_MS);

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

    // Execute the test function
    console.log(`Executing: ${expression}`);
    const result = await send('Runtime.evaluate', {
      expression: expression,
      returnByValue: true,
      awaitPromise: true
    });

    if (result.result && result.result.value !== undefined) {
      console.log(`\nResult: ${JSON.stringify(result.result.value, null, 2)}`);
    } else if (result.result && result.result.type === 'undefined') {
      console.log('\nResult: (void - function started)');
    } else {
      console.log(`\nResult: ${JSON.stringify(result, null, 2)}`);
    }

    // Wait for operation to complete
    if (waitTime > 0) {
      console.log(`\nWaiting ${waitTime}s for operation to complete...`);
      await new Promise(r => setTimeout(r, waitTime * 1000));

      // Get status after waiting
      const statusExpr = TEST_FUNCTIONS[appName].getStatus;
      const statusResult = await send('Runtime.evaluate', {
        expression: statusExpr,
        returnByValue: true
      });

      if (statusResult.result && statusResult.result.value) {
        const status = JSON.parse(statusResult.result.value);
        console.log(`\nFinal Status:`);
        console.log(JSON.stringify(status, null, 2));

        // Determine success/failure
        if (status.statusMessage && status.statusMessage.toLowerCase().includes('error')) {
          console.log('\n[FAIL] Operation failed');
          ws.close();
          process.exit(1);
        } else if (!status.isProcessing) {
          console.log('\n[OK] Operation completed');
        } else {
          console.log('\n[WAIT] Still processing...');
        }
      }
    }

    ws.close();
    console.log('\nDone!');
    process.exit(0);

  } catch (error) {
    console.error(`\nError: ${error.message}`);
    process.exit(1);
  }
}

main();
