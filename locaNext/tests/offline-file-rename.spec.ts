import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

/**
 * P9-FILE: Offline File Rename Tests
 *
 * Tests file rename functionality in Offline Storage:
 * 1. Create local file in Offline Storage
 * 2. Rename local file - should SUCCEED
 * 3. Try to rename synced file - should FAIL (by design)
 *
 * Issue: P9-FILE in ISSUES_TO_FIX.md
 */

const API_URL = 'http://localhost:8888';

// ESM-compatible __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Fixture path
const FIXTURES_DIR = path.resolve(__dirname, '../../tests/fixtures');

// Helper to get auth token
async function getAuthToken(request: any): Promise<string> {
  const response = await request.post(`${API_URL}/api/v2/auth/login`, {
    data: { username: 'admin', password: 'admin123' }
  });
  const { access_token } = await response.json();
  return access_token;
}

// Helper to upload a file to Offline Storage
async function uploadToOfflineStorage(
  request: any,
  token: string,
  filename: string,
  fileBuffer: Buffer
): Promise<{ id: number; name: string }> {
  const response = await request.post(`${API_URL}/api/ldm/files/upload`, {
    headers: { Authorization: `Bearer ${token}` },
    multipart: {
      file: {
        name: filename,
        mimeType: 'text/plain',
        buffer: fileBuffer
      },
      storage: 'local'  // P9: Upload to SQLite Offline Storage
    }
  });

  if (!response.ok()) {
    const errorText = await response.text();
    throw new Error(`Upload failed: ${response.status()} - ${errorText}`);
  }

  return await response.json();
}

test.describe('P9-FILE: Offline File Rename', () => {

  test('should upload file to Offline Storage', async ({ request }) => {
    const token = await getAuthToken(request);

    // Use sample fixture
    const txtPath = path.join(FIXTURES_DIR, 'sample_language_data.txt');

    if (!fs.existsSync(txtPath)) {
      test.skip();
      return;
    }

    const fileBuffer = fs.readFileSync(txtPath);

    // Upload to Offline Storage using helper
    const data = await uploadToOfflineStorage(request, token, 'test_rename_file.txt', fileBuffer);
    expect(data).toHaveProperty('id');
    expect(data).toHaveProperty('name');
    console.log(`Uploaded file to Offline Storage: id=${data.id}, name='${data.name}'`);

    // Cleanup
    await request.delete(`${API_URL}/api/ldm/offline/storage/files/${data.id}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
  });

  test('should rename local file in Offline Storage', async ({ request }) => {
    const token = await getAuthToken(request);

    // First, upload a test file
    const txtPath = path.join(FIXTURES_DIR, 'sample_language_data.txt');

    if (!fs.existsSync(txtPath)) {
      test.skip();
      return;
    }

    const fileBuffer = fs.readFileSync(txtPath);
    const timestamp = Date.now();
    const originalName = `rename_test_${timestamp}.txt`;

    // Upload to Offline Storage using helper
    const uploadData = await uploadToOfflineStorage(request, token, originalName, fileBuffer);
    const fileId = uploadData.id;
    console.log(`Uploaded file: id=${fileId}, name='${uploadData.name}'`);

    // Now rename the file
    const newName = `renamed_${timestamp}.txt`;
    const renameResponse = await request.put(
      `${API_URL}/api/ldm/offline/storage/files/${fileId}/rename`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        data: { new_name: newName }
      }
    );

    expect(renameResponse.ok()).toBeTruthy();
    const renameData = await renameResponse.json();
    expect(renameData.success).toBe(true);
    expect(renameData.message).toContain(newName);
    console.log(`✅ Rename SUCCESS: '${originalName}' -> '${newName}'`);

    // Verify by fetching file list
    const listResponse = await request.get(`${API_URL}/api/ldm/offline/local-files`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    expect(listResponse.ok()).toBeTruthy();
    const listData = await listResponse.json();

    // Find the renamed file
    const renamedFile = listData.files.find((f: any) => f.id === fileId);
    expect(renamedFile).toBeTruthy();
    expect(renamedFile.name).toBe(newName);
    console.log(`✅ Verified: File now has name '${renamedFile.name}'`);

    // Cleanup: Delete the test file
    const deleteResponse = await request.delete(
      `${API_URL}/api/ldm/offline/storage/files/${fileId}`,
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    );
    expect(deleteResponse.ok()).toBeTruthy();
    console.log(`Cleaned up test file: id=${fileId}`);
  });

  test('should reject rename with empty name', async ({ request }) => {
    const token = await getAuthToken(request);

    // First, upload a test file
    const txtPath = path.join(FIXTURES_DIR, 'sample_language_data.txt');

    if (!fs.existsSync(txtPath)) {
      test.skip();
      return;
    }

    const fileBuffer = fs.readFileSync(txtPath);
    const timestamp = Date.now();

    // Upload to Offline Storage using helper
    const uploadData = await uploadToOfflineStorage(request, token, `empty_name_test_${timestamp}.txt`, fileBuffer);
    const fileId = uploadData.id;

    // Try to rename with empty name
    const renameResponse = await request.put(
      `${API_URL}/api/ldm/offline/storage/files/${fileId}/rename`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        data: { new_name: '' }
      }
    );

    // Should fail with validation error
    expect(renameResponse.status()).toBeGreaterThanOrEqual(400);
    console.log(`✅ Empty name correctly rejected with status ${renameResponse.status()}`);

    // Cleanup
    await request.delete(`${API_URL}/api/ldm/offline/storage/files/${fileId}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
  });

  test('should reject rename of non-existent file', async ({ request }) => {
    const token = await getAuthToken(request);

    // Try to rename a non-existent file
    const fakeFileId = 999999;
    const renameResponse = await request.put(
      `${API_URL}/api/ldm/offline/storage/files/${fakeFileId}/rename`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        data: { new_name: 'should_not_work.txt' }
      }
    );

    // Should fail with 400 (file not found or not in Offline Storage)
    expect(renameResponse.status()).toBe(400);
    const data = await renameResponse.json();
    expect(data.detail).toContain('not found');
    console.log(`✅ Non-existent file correctly rejected: ${data.detail}`);
  });

  test('PATCH /files/{id}/rename falls back to SQLite for local files', async ({ request }) => {
    const token = await getAuthToken(request);

    // First, upload a test file to Offline Storage
    const txtPath = path.join(FIXTURES_DIR, 'sample_language_data.txt');

    if (!fs.existsSync(txtPath)) {
      test.skip();
      return;
    }

    const fileBuffer = fs.readFileSync(txtPath);
    const timestamp = Date.now();
    const originalName = `patch_rename_test_${timestamp}.txt`;

    // Upload to Offline Storage using helper
    const uploadData = await uploadToOfflineStorage(request, token, originalName, fileBuffer);
    const fileId = uploadData.id;
    console.log(`Uploaded local file: id=${fileId}`);

    // Use the PATCH endpoint (which should fallback to SQLite)
    const newName = `patch_renamed_${timestamp}.txt`;
    const renameResponse = await request.patch(
      `${API_URL}/api/ldm/files/${fileId}/rename?name=${encodeURIComponent(newName)}`,
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    );

    expect(renameResponse.ok()).toBeTruthy();
    const renameData = await renameResponse.json();
    expect(renameData.success).toBe(true);
    expect(renameData.name).toBe(newName);
    console.log(`✅ PATCH endpoint fallback worked: '${originalName}' -> '${newName}'`);

    // Cleanup
    await request.delete(`${API_URL}/api/ldm/offline/storage/files/${fileId}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
  });
});

test.describe('P9-FILE: Synced File Rename (Should Fail)', () => {

  test('synced files from server cannot be renamed locally', async ({ request }) => {
    const token = await getAuthToken(request);

    // Get list of offline files that are synced (not local)
    const listResponse = await request.get(`${API_URL}/api/ldm/offline/subscriptions`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (!listResponse.ok()) {
      console.log('No subscriptions endpoint available, skipping synced file test');
      test.skip();
      return;
    }

    const data = await listResponse.json();
    const subscriptions = data.subscriptions || data;

    // Ensure we have an array
    if (!Array.isArray(subscriptions)) {
      console.log('Subscriptions response is not an array, skipping test');
      console.log('Response:', JSON.stringify(data).slice(0, 200));
      test.skip();
      return;
    }

    // Find a synced file (sync_status = 'synced')
    const syncedFile = subscriptions.find((s: any) =>
      s.entity_type === 'file' && s.sync_status === 'synced'
    );

    if (!syncedFile) {
      console.log('No synced files found to test. This is expected if no files have been synced.');
      console.log('To test synced file rename rejection:');
      console.log('  1. Enable offline sync for a file from the server');
      console.log('  2. Run this test again');
      test.skip();
      return;
    }

    // Try to rename the synced file using the Offline Storage endpoint
    const renameResponse = await request.put(
      `${API_URL}/api/ldm/offline/storage/files/${syncedFile.entity_id}/rename`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        data: { new_name: 'should_not_work.txt' }
      }
    );

    // Should fail because synced files can't be renamed locally
    expect(renameResponse.status()).toBe(400);
    const renameData = await renameResponse.json();
    expect(renameData.detail).toContain('not found');
    console.log(`✅ Synced file rename correctly rejected: ${renameData.detail}`);
  });
});
