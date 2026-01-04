#!/usr/bin/env node
/**
 * Manifest Generator for LAUNCHER-Style Patch Updates
 *
 * Generates manifest.json with component hashes for delta updates.
 * Run after electron-builder to create patch update assets.
 *
 * Usage: node generate-manifest.js <version> <build-dir> <output-dir>
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// Configuration
const COMPONENTS = {
  'app.asar': {
    description: 'Frontend application bundle',
    required: true,
    restartRequired: true
  },
  'server': {
    description: 'Backend Python server',
    required: true,
    restartRequired: true,
    isDirectory: true
  }
};

/**
 * Calculate SHA256 hash of a file
 */
function hashFile(filePath) {
  const content = fs.readFileSync(filePath);
  return crypto.createHash('sha256').update(content).digest('hex');
}

/**
 * Calculate SHA256 hash of a directory (concatenated file hashes)
 */
function hashDirectory(dirPath) {
  const hash = crypto.createHash('sha256');

  function walkDir(dir) {
    const files = fs.readdirSync(dir).sort();
    for (const file of files) {
      const fullPath = path.join(dir, file);
      const stat = fs.statSync(fullPath);
      if (stat.isDirectory()) {
        // Skip __pycache__ and other cache directories
        if (!file.startsWith('__') && !file.startsWith('.')) {
          walkDir(fullPath);
        }
      } else {
        // Add file path and content to hash
        hash.update(file);
        hash.update(fs.readFileSync(fullPath));
      }
    }
  }

  walkDir(dirPath);
  return hash.digest('hex');
}

/**
 * Get file/directory size
 */
function getSize(itemPath) {
  const stat = fs.statSync(itemPath);
  if (stat.isDirectory()) {
    let total = 0;
    function walkDir(dir) {
      const files = fs.readdirSync(dir);
      for (const file of files) {
        const fullPath = path.join(dir, file);
        const fileStat = fs.statSync(fullPath);
        if (fileStat.isDirectory()) {
          walkDir(fullPath);
        } else {
          total += fileStat.size;
        }
      }
    }
    walkDir(itemPath);
    return total;
  }
  return stat.size;
}

/**
 * Create zip of a directory
 */
function zipDirectory(dirPath, outputPath) {
  const archiver = require('archiver');
  return new Promise((resolve, reject) => {
    const output = fs.createWriteStream(outputPath);
    const archive = archiver('zip', { zlib: { level: 9 } });

    output.on('close', () => resolve(archive.pointer()));
    archive.on('error', reject);

    archive.pipe(output);
    archive.directory(dirPath, false);
    archive.finalize();
  });
}

/**
 * Main function
 */
async function generateManifest(version, buildDir, outputDir) {
  console.log('╔════════════════════════════════════════════════════════════╗');
  console.log('║  MANIFEST GENERATOR - Patch Update System                  ║');
  console.log('╚════════════════════════════════════════════════════════════╝');
  console.log(`Version: ${version}`);
  console.log(`Build Dir: ${buildDir}`);
  console.log(`Output Dir: ${outputDir}`);
  console.log('');

  // Ensure output directory exists
  fs.mkdirSync(outputDir, { recursive: true });

  const resourcesDir = path.join(buildDir, 'resources');
  const manifest = {
    version: version,
    buildDate: new Date().toISOString(),
    components: {},
    minVersion: null, // Set if breaking changes require full update
    releaseNotes: `LocaNext v${version}`
  };

  // Process each component
  for (const [name, config] of Object.entries(COMPONENTS)) {
    const componentPath = path.join(resourcesDir, name);

    if (!fs.existsSync(componentPath)) {
      console.log(`⚠ Component not found: ${name}`);
      continue;
    }

    console.log(`Processing: ${name}`);

    let sha256, size, outputFile;

    if (config.isDirectory) {
      // Hash directory contents
      sha256 = hashDirectory(componentPath);
      size = getSize(componentPath);

      // Create zip for directory components
      outputFile = `${name}.zip`;
      const zipPath = path.join(outputDir, outputFile);

      try {
        const zipSize = await zipDirectory(componentPath, zipPath);
        console.log(`  → Created ${outputFile} (${(zipSize / 1024 / 1024).toFixed(2)} MB)`);
        size = zipSize; // Use zip size for download
      } catch (err) {
        // If archiver not available, just reference the directory
        console.log(`  → Directory mode (zip not created): ${err.message}`);
        outputFile = name;
      }
    } else {
      // Hash file directly
      sha256 = hashFile(componentPath);
      size = getSize(componentPath);
      outputFile = name;

      // Copy file to output
      const destPath = path.join(outputDir, name);
      fs.copyFileSync(componentPath, destPath);
      console.log(`  → Copied ${name} (${(size / 1024 / 1024).toFixed(2)} MB)`);
    }

    manifest.components[name] = {
      version: version,
      sha256: sha256,
      size: size,
      url: `patches/${version}/${outputFile}`,
      required: config.required,
      restartRequired: config.restartRequired,
      description: config.description
    };

    console.log(`  → SHA256: ${sha256.substring(0, 16)}...`);
    console.log(`  → Size: ${(size / 1024 / 1024).toFixed(2)} MB`);
  }

  // Write manifest
  const manifestPath = path.join(outputDir, 'manifest.json');
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
  console.log('');
  console.log(`✓ Manifest written to: ${manifestPath}`);

  // Also create a summary
  const totalSize = Object.values(manifest.components).reduce((sum, c) => sum + c.size, 0);
  console.log('');
  console.log('═══════════════════════════════════════════════════════════');
  console.log('  SUMMARY');
  console.log('═══════════════════════════════════════════════════════════');
  console.log(`  Components: ${Object.keys(manifest.components).length}`);
  console.log(`  Total Size: ${(totalSize / 1024 / 1024).toFixed(2)} MB`);
  console.log(`  vs Full Installer: ~624 MB`);
  console.log(`  Savings: ~${(100 - (totalSize / 624000000 * 100)).toFixed(0)}%`);
  console.log('═══════════════════════════════════════════════════════════');

  return manifest;
}

// CLI
if (require.main === module) {
  const args = process.argv.slice(2);

  if (args.length < 3) {
    console.log('Usage: node generate-manifest.js <version> <build-dir> <output-dir>');
    console.log('');
    console.log('Example:');
    console.log('  node generate-manifest.js 26.104.1600 ./dist/win-unpacked ./dist/patches');
    process.exit(1);
  }

  const [version, buildDir, outputDir] = args;

  generateManifest(version, buildDir, outputDir)
    .then(() => {
      console.log('');
      console.log('✓ Manifest generation complete!');
    })
    .catch(err => {
      console.error('✗ Error:', err.message);
      process.exit(1);
    });
}

module.exports = { generateManifest, hashFile, hashDirectory };
