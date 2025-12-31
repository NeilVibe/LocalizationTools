/**
 * AUTONOMOUS UPLOAD PERFORMANCE TEST
 *
 * Tests file upload speeds with EXTREME DETAILED LOGGING
 *
 * Usage: node test_upload_performance.js
 *
 * Test files (from TestFilesForLocaNext):
 * - SMALL: SMALLTESTFILEFORQUICKSEARCH.txt (379KB)
 * - MEDIUM: sampleofLanguageData.txt (16MB)
 * - BIG: languagedata_fr PC 1012 1813.txt (198MB)
 */

const fs = require('fs');
const path = require('path');
const FormData = require('form-data');
const http = require('http');

// Configuration
const API_BASE = 'http://localhost:8888';
const TEST_FILES_DIR = '/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/TestFilesForLocaNext';
const PROJECT_ID = 60; // Simple Test Project

// Test files
const TEST_FILES = {
  SMALL: 'SMALLTESTFILEFORQUICKSEARCH.txt',
  MEDIUM: 'sampleofLanguageData.txt',
  BIG: 'languagedata_fr PC 1012 1813.txt'
};

// Extreme detailed logger
function log(level, category, message, data = {}) {
  const timestamp = new Date().toISOString();
  const memUsage = process.memoryUsage();
  const logEntry = {
    timestamp,
    level,
    category,
    message,
    data,
    memory: {
      heapUsed: Math.round(memUsage.heapUsed / 1024 / 1024) + 'MB',
      heapTotal: Math.round(memUsage.heapTotal / 1024 / 1024) + 'MB',
      rss: Math.round(memUsage.rss / 1024 / 1024) + 'MB'
    }
  };

  const color = {
    INFO: '\x1b[36m',
    DEBUG: '\x1b[90m',
    SUCCESS: '\x1b[32m',
    ERROR: '\x1b[31m',
    PERF: '\x1b[33m',
    RESET: '\x1b[0m'
  };

  console.log(`${color[level] || ''}[${timestamp}] [${level}] [${category}] ${message}${color.RESET}`);
  if (Object.keys(data).length > 0) {
    console.log(`  └─ ${JSON.stringify(data)}`);
  }
}

// Performance metrics collector
class PerfMetrics {
  constructor(testName) {
    this.testName = testName;
    this.startTime = null;
    this.endTime = null;
    this.phases = [];
    this.currentPhase = null;
  }

  start() {
    this.startTime = process.hrtime.bigint();
    log('PERF', 'METRICS', `Starting test: ${this.testName}`);
  }

  startPhase(phaseName) {
    this.currentPhase = {
      name: phaseName,
      start: process.hrtime.bigint(),
      end: null,
      durationMs: null
    };
    log('DEBUG', 'PHASE', `Starting phase: ${phaseName}`);
  }

  endPhase() {
    if (this.currentPhase) {
      this.currentPhase.end = process.hrtime.bigint();
      this.currentPhase.durationMs = Number(this.currentPhase.end - this.currentPhase.start) / 1_000_000;
      this.phases.push(this.currentPhase);
      log('PERF', 'PHASE', `Phase "${this.currentPhase.name}" completed`, {
        durationMs: this.currentPhase.durationMs.toFixed(2)
      });
      this.currentPhase = null;
    }
  }

  end() {
    this.endTime = process.hrtime.bigint();
    const totalMs = Number(this.endTime - this.startTime) / 1_000_000;
    log('PERF', 'METRICS', `Test "${this.testName}" completed`, {
      totalDurationMs: totalMs.toFixed(2),
      phases: this.phases.map(p => ({ name: p.name, ms: p.durationMs.toFixed(2) }))
    });
    return totalMs;
  }

  getSummary() {
    return {
      testName: this.testName,
      totalMs: Number(this.endTime - this.startTime) / 1_000_000,
      phases: this.phases.map(p => ({
        name: p.name,
        durationMs: p.durationMs
      }))
    };
  }
}

// Upload file using raw HTTP (more control than fetch)
async function uploadFile(filePath, projectId) {
  return new Promise((resolve, reject) => {
    const metrics = new PerfMetrics(`Upload ${path.basename(filePath)}`);

    // Phase 1: Read file
    metrics.start();
    metrics.startPhase('file_read');

    const fileStats = fs.statSync(filePath);
    const fileSizeKB = fileStats.size / 1024;
    const fileSizeMB = fileSizeKB / 1024;

    log('INFO', 'FILE', `Reading file: ${path.basename(filePath)}`, {
      sizeBytes: fileStats.size,
      sizeKB: fileSizeKB.toFixed(2),
      sizeMB: fileSizeMB.toFixed(2)
    });

    const fileStream = fs.createReadStream(filePath);
    metrics.endPhase();

    // Phase 2: Create form data
    metrics.startPhase('form_create');
    const form = new FormData();
    form.append('project_id', projectId.toString());
    form.append('file', fileStream, path.basename(filePath));
    metrics.endPhase();

    // Phase 3: HTTP request
    metrics.startPhase('http_request');

    const url = new URL(`${API_BASE}/api/ldm/files/upload`);
    const options = {
      method: 'POST',
      hostname: url.hostname,
      port: url.port,
      path: url.pathname,
      headers: {
        ...form.getHeaders(),
        'X-Dev-User': 'admin'
      }
    };

    log('DEBUG', 'HTTP', 'Sending request', {
      url: url.toString(),
      method: 'POST',
      fileSize: fileStats.size
    });

    const req = http.request(options, (res) => {
      let data = '';

      res.on('data', (chunk) => {
        data += chunk;
        log('DEBUG', 'HTTP', `Received chunk: ${chunk.length} bytes`);
      });

      res.on('end', () => {
        metrics.endPhase();

        // Phase 4: Parse response
        metrics.startPhase('response_parse');
        const totalMs = metrics.end();

        const uploadSpeedKBps = fileSizeKB / (totalMs / 1000);
        const uploadSpeedMBps = fileSizeMB / (totalMs / 1000);

        try {
          const result = JSON.parse(data);
          log('SUCCESS', 'UPLOAD', `Upload completed: ${path.basename(filePath)}`, {
            httpStatus: res.statusCode,
            rowCount: result.row_count,
            totalTimeMs: totalMs.toFixed(2),
            speedKBps: uploadSpeedKBps.toFixed(2),
            speedMBps: uploadSpeedMBps.toFixed(4)
          });

          resolve({
            success: true,
            file: path.basename(filePath),
            sizeKB: fileSizeKB,
            sizeMB: fileSizeMB,
            totalMs,
            speedKBps: uploadSpeedKBps,
            speedMBps: uploadSpeedMBps,
            rowCount: result.row_count,
            metrics: metrics.getSummary()
          });
        } catch (e) {
          log('ERROR', 'UPLOAD', 'Failed to parse response', { error: e.message, data });
          reject(e);
        }
      });
    });

    req.on('error', (e) => {
      log('ERROR', 'HTTP', 'Request failed', { error: e.message });
      reject(e);
    });

    // Track upload progress
    let uploaded = 0;
    form.on('data', (chunk) => {
      uploaded += chunk.length;
      const percent = ((uploaded / fileStats.size) * 100).toFixed(1);
      if (percent % 10 < 1) {
        log('DEBUG', 'UPLOAD', `Progress: ${percent}%`, { bytesUploaded: uploaded });
      }
    });

    form.pipe(req);
  });
}

// Main test runner
async function runPerformanceTests() {
  console.log('\n' + '='.repeat(80));
  console.log('  AUTONOMOUS UPLOAD PERFORMANCE TEST');
  console.log('  ' + new Date().toISOString());
  console.log('='.repeat(80) + '\n');

  log('INFO', 'INIT', 'Starting autonomous performance tests');
  log('DEBUG', 'CONFIG', 'Test configuration', {
    apiBase: API_BASE,
    projectId: PROJECT_ID,
    testFilesDir: TEST_FILES_DIR
  });

  // Check server
  log('INFO', 'SERVER', 'Checking server health...');
  try {
    const healthRes = await fetch(`${API_BASE}/health`);
    const health = await healthRes.json();
    log('SUCCESS', 'SERVER', 'Server is healthy', health);
  } catch (e) {
    log('ERROR', 'SERVER', 'Server not responding!', { error: e.message });
    process.exit(1);
  }

  // Check test files exist
  log('INFO', 'FILES', 'Checking test files...');
  const testFilePaths = {};
  for (const [size, filename] of Object.entries(TEST_FILES)) {
    const fullPath = path.join(TEST_FILES_DIR, filename);
    if (fs.existsSync(fullPath)) {
      const stats = fs.statSync(fullPath);
      testFilePaths[size] = fullPath;
      log('SUCCESS', 'FILES', `Found ${size} file: ${filename}`, {
        sizeKB: (stats.size / 1024).toFixed(2),
        sizeMB: (stats.size / 1024 / 1024).toFixed(2)
      });
    } else {
      log('ERROR', 'FILES', `Missing ${size} file: ${filename}`);
    }
  }

  // Run tests
  const results = [];

  // Test SMALL file
  if (testFilePaths.SMALL) {
    console.log('\n' + '-'.repeat(60));
    log('INFO', 'TEST', '=== SMALL FILE TEST ===');
    try {
      const result = await uploadFile(testFilePaths.SMALL, PROJECT_ID);
      results.push({ size: 'SMALL', ...result });
    } catch (e) {
      log('ERROR', 'TEST', 'SMALL file test failed', { error: e.message });
    }
  }

  // Test MEDIUM file
  if (testFilePaths.MEDIUM) {
    console.log('\n' + '-'.repeat(60));
    log('INFO', 'TEST', '=== MEDIUM FILE TEST ===');
    try {
      const result = await uploadFile(testFilePaths.MEDIUM, PROJECT_ID);
      results.push({ size: 'MEDIUM', ...result });
    } catch (e) {
      log('ERROR', 'TEST', 'MEDIUM file test failed', { error: e.message });
    }
  }

  // Test BIG file (optional - can take long time)
  if (testFilePaths.BIG) {
    console.log('\n' + '-'.repeat(60));
    log('INFO', 'TEST', '=== BIG FILE TEST (may take a while) ===');
    try {
      const result = await uploadFile(testFilePaths.BIG, PROJECT_ID);
      results.push({ size: 'BIG', ...result });
    } catch (e) {
      log('ERROR', 'TEST', 'BIG file test failed', { error: e.message });
    }
  }

  // Summary
  console.log('\n' + '='.repeat(80));
  console.log('  PERFORMANCE TEST SUMMARY');
  console.log('='.repeat(80));

  for (const result of results) {
    console.log(`\n  ${result.size} FILE: ${result.file}`);
    console.log(`    Size: ${result.sizeKB.toFixed(2)} KB (${result.sizeMB.toFixed(2)} MB)`);
    console.log(`    Time: ${result.totalMs.toFixed(2)} ms`);
    console.log(`    Speed: ${result.speedKBps.toFixed(2)} KB/s (${result.speedMBps.toFixed(4)} MB/s)`);
    console.log(`    Rows: ${result.rowCount}`);
  }

  console.log('\n' + '='.repeat(80) + '\n');

  log('SUCCESS', 'DONE', 'All performance tests completed', {
    testsRun: results.length,
    testsPassed: results.filter(r => r.success).length
  });
}

// Run if executed directly
runPerformanceTests().catch(e => {
  log('ERROR', 'FATAL', 'Test runner crashed', { error: e.message, stack: e.stack });
  process.exit(1);
});
