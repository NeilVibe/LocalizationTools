/**
 * LocaNext Bootstrap - Early Error Capture
 *
 * This file catches ANY startup error (including import failures)
 * and writes it to logs/startup_crash.txt BEFORE showing the error dialog.
 *
 * This allows Claude to diagnose Windows startup failures without
 * needing the user to provide screenshots.
 */

import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { writeFileSync, mkdirSync, existsSync } from 'fs';
import { app } from 'electron';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Determine logs directory (works in both dev and production)
function getLogsDir() {
  const appPath = app.isPackaged
    ? dirname(app.getPath('exe'))
    : join(__dirname, '..');
  return join(appPath, 'logs');
}

// Write crash to file - SYNCHRONOUS, no dependencies
function writeCrashLog(error) {
  try {
    const logsDir = getLogsDir();
    if (!existsSync(logsDir)) {
      mkdirSync(logsDir, { recursive: true });
    }

    const crashFile = join(logsDir, 'startup_crash.txt');
    const timestamp = new Date().toISOString();
    const content = `=== STARTUP CRASH ===
Timestamp: ${timestamp}
Error: ${error.message || error}
Code: ${error.code || 'N/A'}

Stack:
${error.stack || 'No stack trace'}

This file is auto-generated when the app fails to start.
Check this file from WSL: cat /mnt/d/LocaNext/logs/startup_crash.txt
`;

    writeFileSync(crashFile, content, 'utf8');
    console.error(`Crash logged to: ${crashFile}`);
  } catch (e) {
    console.error('Failed to write crash log:', e);
  }
}

// Clear previous crash log on successful start
function clearCrashLog() {
  try {
    const crashFile = join(getLogsDir(), 'startup_crash.txt');
    if (existsSync(crashFile)) {
      writeFileSync(crashFile, `Last successful start: ${new Date().toISOString()}\n`, 'utf8');
    }
  } catch (e) {
    // Ignore
  }
}

// Main bootstrap - dynamically import main.js to catch import errors
async function bootstrap() {
  try {
    // Clear old crash log
    clearCrashLog();

    // Dynamic import catches module resolution errors
    await import('./main.js');

  } catch (error) {
    // Write crash to file FIRST
    writeCrashLog(error);

    // Re-throw to show the error dialog
    throw error;
  }
}

// Run bootstrap
bootstrap().catch((error) => {
  console.error('Bootstrap failed:', error);
  // Error dialog will show automatically
});
