/**
 * Post-build script to fix SvelteKit paths for Electron's file:// protocol
 *
 * Problem: SvelteKit generates absolute paths like /_app/... which resolve
 * to C:/_app/... on Windows when using file:// protocol in Electron.
 *
 * Solution: Convert all absolute paths to relative paths (./_app/...)
 *
 * Run automatically after vite build via package.json:
 *   "build": "vite build && node scripts/fix-electron-paths.js"
 */

import { readFileSync, writeFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const indexPath = join(__dirname, '..', 'build', 'index.html');

console.log('Fixing Electron paths in build/index.html...');

try {
  let content = readFileSync(indexPath, 'utf-8');

  // Count replacements
  let count = 0;

  // Replace href="/_app/ with href="./_app/
  const hrefPattern = /href="\/_app\//g;
  const hrefMatches = content.match(hrefPattern);
  if (hrefMatches) count += hrefMatches.length;
  content = content.replace(hrefPattern, 'href="./_app/');

  // Replace import("/_app/ with import("./_app/
  const importPattern = /import\("\/_app\//g;
  const importMatches = content.match(importPattern);
  if (importMatches) count += importMatches.length;
  content = content.replace(importPattern, 'import("./_app/');

  // Replace href="/favicon with href="./favicon
  const faviconPattern = /href="\/favicon/g;
  const faviconMatches = content.match(faviconPattern);
  if (faviconMatches) count += faviconMatches.length;
  content = content.replace(faviconPattern, 'href="./favicon');

  writeFileSync(indexPath, content);

  console.log(`Done! Fixed ${count} absolute paths to relative paths.`);
  console.log('  - href="/_app/" -> href="./_app/"');
  console.log('  - import("/_app/") -> import("./_app/")');
  console.log('  - href="/favicon" -> href="./favicon"');

} catch (error) {
  console.error('Error fixing paths:', error.message);
  process.exit(1);
}
