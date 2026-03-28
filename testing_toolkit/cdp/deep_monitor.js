/**
 * CDP Deep Monitor — THE freeze detection tool
 *
 * Captures EVERY console message, network request, exception, and heartbeat.
 * Detects exact freeze moment via eval latency spikes.
 * Found the 161,424 API call infinite loop that 3 AI experts missed.
 *
 * Usage (from WSL):
 *   /mnt/c/Program\ Files/nodejs/node.exe deep_monitor.js [duration_seconds]
 *
 * Default: 120 seconds
 * Output: /tmp/cdp_deep_log.json (full structured log)
 */

const WebSocket = require('ws');
const http = require('http');
const fs = require('fs');

const DURATION = (parseInt(process.argv[2]) || 120) * 1000;
const CDP_PORT = 9222;

http.get(`http://127.0.0.1:${CDP_PORT}/json`, res => {
  let d = '';
  res.on('data', c => d += c);
  res.on('end', () => {
    const page = JSON.parse(d).find(t => t.type === 'page');
    if (!page) { console.log('No page found'); process.exit(1); }

    const ws = new WebSocket(page.webSocketDebuggerUrl);
    const log = [];
    const t0 = Date.now();
    const ts = () => ((Date.now() - t0) / 1000).toFixed(3) + 's';

    ws.on('open', () => {
      // Enable ALL CDP domains
      ws.send(JSON.stringify({ id: 1, method: 'Console.enable' }));
      ws.send(JSON.stringify({ id: 2, method: 'Runtime.enable' }));
      ws.send(JSON.stringify({ id: 3, method: 'Network.enable' }));
      ws.send(JSON.stringify({ id: 4, method: 'Log.enable' }));
      ws.send(JSON.stringify({ id: 5, method: 'Debugger.enable' }));

      console.log(`[${ts()}] === DEEP MONITOR ACTIVE (${DURATION/1000}s) ===`);
      console.log(`[${ts()}] === Reproduce the issue NOW ===`);

      // Heartbeat: detect freeze via eval latency
      let hbId = 100;
      const heartbeat = setInterval(() => {
        const myId = hbId++;
        const sendTime = Date.now();
        ws.send(JSON.stringify({
          id: myId,
          method: 'Runtime.evaluate',
          params: { expression: 'JSON.stringify({t:Date.now(),dom:document.querySelectorAll("*").length,heap:Math.round(performance.memory?.usedJSHeapSize/1024/1024)})' }
        }));

        const handler = (msg) => {
          const m = JSON.parse(msg);
          if (m.id === myId) {
            const latency = Date.now() - sendTime;
            if (latency > 500) {
              console.log(`[${ts()}] *** HEARTBEAT SLOW: ${latency}ms *** ${m.result?.result?.value}`);
              log.push({ t: ts(), type: 'heartbeat:slow', latency, value: m.result?.result?.value });
            }
            ws.removeListener('message', handler);
          }
        };
        ws.on('message', handler);
        setTimeout(() => ws.removeListener('message', handler), 5000);
      }, 2000);

      setTimeout(() => clearInterval(heartbeat), DURATION - 5000);
    });

    ws.on('message', msg => {
      const m = JSON.parse(msg);

      // Console messages
      if (m.method === 'Runtime.consoleAPICalled') {
        const type = m.params.type;
        const text = m.params.args.map(a => a.value !== undefined ? String(a.value) : (a.description || a.type)).join(' ');
        let clean = text;
        const match = text.match(/\| (INFO|SUCCESS|WARNING|ERROR|DEBUG)\s+\| (.+?)(?:\s+color:|$)/);
        if (match) clean = `[${match[1]}] ${match[2]}`;

        console.log(`[${ts()}] [CONSOLE:${type}] ${clean.substring(0, 200)}`);
        log.push({ t: ts(), type: `console:${type}`, text: clean.substring(0, 500) });
      }

      // Network requests
      if (m.method === 'Network.requestWillBeSent') {
        const url = m.params.request.url;
        if (url.includes('localhost:8888') || url.includes('127.0.0.1:8888')) {
          console.log(`[${ts()}] [NET:REQ] ${m.params.request.method} ${url.split('?')[0]}`);
          log.push({ t: ts(), type: 'net:req', method: m.params.request.method, url });
        }
      }
      if (m.method === 'Network.responseReceived') {
        const url = m.params.response.url;
        if (url.includes('localhost:8888') || url.includes('127.0.0.1:8888')) {
          console.log(`[${ts()}] [NET:RES] ${m.params.response.status} ${url.split('?')[0]}`);
          log.push({ t: ts(), type: 'net:res', status: m.params.response.status, url });
        }
      }
      if (m.method === 'Network.loadingFailed') {
        console.log(`[${ts()}] [NET:FAIL] ${m.params.errorText || JSON.stringify(m.params)}`);
        log.push({ t: ts(), type: 'net:fail', data: m.params });
      }

      // Exceptions
      if (m.method === 'Runtime.exceptionThrown') {
        const ex = m.params.exceptionDetails;
        console.log(`[${ts()}] [EXCEPTION] ${ex.exception?.description || ex.text}`);
        log.push({ t: ts(), type: 'exception', text: ex.exception?.description || ex.text });
      }

      // Debugger paused
      if (m.method === 'Debugger.paused') {
        console.log(`[${ts()}] *** DEBUGGER PAUSED ***`);
        const frames = m.params.callFrames || [];
        frames.slice(0, 15).forEach((f, i) => {
          console.log(`  ${i}: ${f.functionName || '(anon)'} @ ${f.url?.split('/').pop()}:${f.location?.lineNumber}`);
        });
        log.push({ t: ts(), type: 'debugger:paused', frames: frames.slice(0, 15).map(f => `${f.functionName}@${f.url?.split('/').pop()}:${f.location?.lineNumber}`) });
        ws.send(JSON.stringify({ id: 999, method: 'Debugger.resume' }));
      }
    });

    // Finish
    setTimeout(() => {
      console.log(`\n[${ts()}] === MONITORING COMPLETE ===`);
      console.log(`[${ts()}] Total events: ${log.length}`);

      // Summary: count repeated patterns
      const urlCounts = {};
      log.filter(e => e.type === 'net:req').forEach(e => {
        const short = e.url.split('?')[0];
        urlCounts[short] = (urlCounts[short] || 0) + 1;
      });
      const sorted = Object.entries(urlCounts).sort((a, b) => b[1] - a[1]);
      if (sorted.length > 0) {
        console.log('\n=== TOP API CALLS ===');
        sorted.slice(0, 10).forEach(([url, count]) => {
          console.log(`  ${count}x ${url}${count > 100 ? ' *** INFINITE LOOP? ***' : ''}`);
        });
      }

      fs.writeFileSync('/tmp/cdp_deep_log.json', JSON.stringify(log, null, 2));
      console.log('\nFull log: /tmp/cdp_deep_log.json');
      ws.close();
      process.exit(0);
    }, DURATION);
  });
}).on('error', e => {
  console.log('CDP unavailable:', e.message);
  console.log('Launch app with: LocaNext.exe --remote-debugging-port=9222');
  process.exit(1);
});
