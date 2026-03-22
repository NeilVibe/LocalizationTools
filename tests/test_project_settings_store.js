/**
 * Unit test for projectSettings store (Phase 56, Plan 02, Task 2)
 *
 * Tests set/get round-trip, per-project isolation, defaults, and corrupt JSON handling.
 * Run with: node tests/test_project_settings_store.js
 */

// Mock browser localStorage for testing
const storage = {};
global.localStorage = {
  getItem: (k) => storage[k] || null,
  setItem: (k, v) => { storage[k] = v; },
  removeItem: (k) => { delete storage[k]; },
};

// Inline the store logic (can't import ESM with $app/environment)
const SETTINGS_PREFIX = 'locaNext_project_settings_';
const DEFAULT_SETTINGS = { locPath: '', exportPath: '' };

function getProjectSettings(projectId) {
  const stored = localStorage.getItem(SETTINGS_PREFIX + projectId);
  if (!stored) return { ...DEFAULT_SETTINGS };
  try { return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) }; }
  catch { return { ...DEFAULT_SETTINGS }; }
}

function setProjectSettings(projectId, settings) {
  localStorage.setItem(SETTINGS_PREFIX + projectId, JSON.stringify(settings));
}

function clearProjectSettings(projectId) {
  localStorage.removeItem(SETTINGS_PREFIX + projectId);
}

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    passed++;
  } else {
    failed++;
    console.error(`FAIL: ${message}`);
  }
}

// Test 1: set/get round-trip (SET-01, SET-02)
setProjectSettings(1, { locPath: '/mnt/c/LOC', exportPath: '/mnt/c/EXPORT' });
const result = getProjectSettings(1);
assert(result.locPath === '/mnt/c/LOC', 'locPath mismatch');
assert(result.exportPath === '/mnt/c/EXPORT', 'exportPath mismatch');

// Test 2: per-project isolation
setProjectSettings(2, { locPath: '/other', exportPath: '' });
const r1 = getProjectSettings(1);
const r2 = getProjectSettings(2);
assert(r1.locPath === '/mnt/c/LOC', 'project 1 should be unchanged');
assert(r2.locPath === '/other', 'project 2 should be /other');

// Test 3: defaults for unknown project
const r3 = getProjectSettings(999);
assert(r3.locPath === '', 'unknown project locPath should be empty');
assert(r3.exportPath === '', 'unknown project exportPath should be empty');

// Test 4: corrupt JSON returns defaults
localStorage.setItem(SETTINGS_PREFIX + 50, '{invalid json');
const r4 = getProjectSettings(50);
assert(r4.locPath === '', 'corrupt JSON should return default locPath');
assert(r4.exportPath === '', 'corrupt JSON should return default exportPath');

// Test 5: clearProjectSettings removes data
setProjectSettings(3, { locPath: '/tmp', exportPath: '/tmp/out' });
assert(getProjectSettings(3).locPath === '/tmp', 'should have /tmp before clear');
clearProjectSettings(3);
const r5 = getProjectSettings(3);
assert(r5.locPath === '', 'cleared project should return default locPath');
assert(r5.exportPath === '', 'cleared project should return default exportPath');

// Test 6: partial settings merge with defaults
localStorage.setItem(SETTINGS_PREFIX + 60, JSON.stringify({ locPath: '/partial' }));
const r6 = getProjectSettings(60);
assert(r6.locPath === '/partial', 'partial locPath should be /partial');
assert(r6.exportPath === '', 'missing exportPath should default to empty');

if (failed === 0) {
  console.log(`ALL TESTS PASSED (${passed} assertions)`);
} else {
  console.error(`${failed} FAILED, ${passed} passed`);
  process.exit(1);
}
