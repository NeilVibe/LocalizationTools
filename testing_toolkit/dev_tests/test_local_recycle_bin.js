/**
 * P9-BIN-001: Test Local Recycle Bin for Offline Storage
 * Tests that local files/folders go to Recycle Bin when deleted
 */

const fs = require('fs');
const path = require('path');
const API_BASE = 'http://localhost:8888';

async function getAuthToken() {
  const response = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'admin', password: 'admin123' })
  });
  const data = await response.json();
  return data.access_token;
}

async function testLocalRecycleBin() {
  console.log('=== P9-BIN-001: Local Recycle Bin Test ===\n');

  const token = await getAuthToken();
  const headers = { 'Authorization': `Bearer ${token}` };

  // 1. Use sample test file (known to work)
  const testFilePath = '/home/neil1988/LocalizationTools/tests/fixtures/sample_language_data.txt';
  console.log('1. Using sample test file');

  // 2. Upload to Offline Storage (storage=local)
  console.log('\n2. Uploading file to Offline Storage...');
  const formData = new FormData();
  const fileContent = fs.readFileSync(testFilePath);
  formData.append('file', new Blob([fileContent]), 'test-recycle-bin.txt');
  formData.append('storage', 'local');  // P9: Store in SQLite Offline Storage

  const uploadResp = await fetch(`${API_BASE}/api/ldm/files/upload`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData
  });

  if (!uploadResp.ok) {
    const err = await uploadResp.text();
    console.error('Failed to upload file:', err);
    return false;
  }

  const uploadResult = await uploadResp.json();
  const fileId = uploadResult.id;
  console.log(`   Uploaded file: ${uploadResult.name} (ID: ${fileId})`);
  console.log(`   Rows: ${uploadResult.row_count}`);

  // 3. Verify file is in local files list
  console.log('\n3. Verifying file in Offline Storage...');
  const filesResp = await fetch(`${API_BASE}/api/ldm/offline/local-files`, { headers });
  const filesData = await filesResp.json();
  const localFile = filesData.files.find(f => f.id === fileId);

  if (!localFile) {
    console.error('   ERROR: File not found in Offline Storage!');
    return false;
  }
  console.log(`   Found: ${localFile.name}`);

  // 4. Delete the file (should go to trash)
  console.log('\n4. Deleting local file (should go to trash)...');
  const deleteResp = await fetch(`${API_BASE}/api/ldm/files/${fileId}`, {
    method: 'DELETE',
    headers
  });

  if (!deleteResp.ok) {
    const err = await deleteResp.json();
    console.error('Failed to delete local file:', err);
    return false;
  }

  const deleteResult = await deleteResp.json();
  console.log(`   Delete result: ${deleteResult.message}`);

  // Check if it went to trash (not permanent)
  if (deleteResult.permanent === true) {
    console.error('   ERROR: File was deleted permanently instead of going to trash!');
    return false;
  }
  console.log('   File moved to trash (soft delete)');

  // 5. Check if file is in local trash
  console.log('\n5. Checking local trash...');
  const trashResp = await fetch(`${API_BASE}/api/ldm/offline/trash`, { headers });

  if (!trashResp.ok) {
    const err = await trashResp.json();
    console.error('Failed to get local trash:', err);
    return false;
  }

  const trashData = await trashResp.json();
  console.log(`   Trash items: ${trashData.items.length}`);

  const trashItem = trashData.items.find(i => i.item_id === fileId);
  if (!trashItem) {
    console.error('   ERROR: File not found in trash!');
    console.log('   Available items:', trashData.items.map(i => `${i.item_name} (id=${i.item_id})`));
    return false;
  }

  console.log(`   Found in trash: ${trashItem.item_name} (trash ID: ${trashItem.id})`);
  console.log(`   Item type: ${trashItem.item_type}`);
  console.log(`   Expires at: ${trashItem.expires_at}`);

  // Verify 30-day expiry
  const expiresAt = new Date(trashItem.expires_at);
  const deletedAt = new Date(trashItem.deleted_at);
  const daysDiff = Math.round((expiresAt - deletedAt) / (1000 * 60 * 60 * 24));
  if (daysDiff !== 30) {
    console.error(`   WARNING: Expected 30 day retention, got ${daysDiff} days`);
  } else {
    console.log('   30-day retention period: CORRECT');
  }

  // 6. Test restore
  console.log('\n6. Testing restore...');
  const restoreResp = await fetch(`${API_BASE}/api/ldm/offline/trash/${trashItem.id}/restore`, {
    method: 'POST',
    headers
  });

  if (!restoreResp.ok) {
    const err = await restoreResp.json();
    console.error('Failed to restore:', err);
    return false;
  }

  const restoreResult = await restoreResp.json();
  console.log(`   Restored: item_type=${restoreResult.item_type}, item_id=${restoreResult.item_id}`);

  // 7. Verify file is restored
  console.log('\n7. Verifying file is back in Offline Storage...');
  const filesResp2 = await fetch(`${API_BASE}/api/ldm/offline/local-files`, { headers });
  const filesData2 = await filesResp2.json();

  const restoredFile = filesData2.files.find(f => f.id === restoreResult.item_id);
  if (!restoredFile) {
    console.error('   ERROR: Restored file not found in Offline Storage!');
    return false;
  }

  console.log(`   File restored: ${restoredFile.name} (ID: ${restoredFile.id})`);

  // 8. Delete again for permanent delete test
  console.log('\n8. Deleting file again for permanent delete test...');
  await fetch(`${API_BASE}/api/ldm/files/${restoredFile.id}`, {
    method: 'DELETE',
    headers
  });

  // 9. Get trash item ID again
  const trashResp2 = await fetch(`${API_BASE}/api/ldm/offline/trash`, { headers });
  const trashData2 = await trashResp2.json();
  const trashItem2 = trashData2.items.find(i => i.item_id === restoredFile.id);

  if (!trashItem2) {
    console.error('   ERROR: File not found in trash after second delete!');
    return false;
  }

  // 10. Permanent delete
  console.log('\n9. Testing permanent delete...');
  const permDeleteResp = await fetch(`${API_BASE}/api/ldm/offline/trash/${trashItem2.id}`, {
    method: 'DELETE',
    headers
  });

  if (!permDeleteResp.ok) {
    const err = await permDeleteResp.json();
    console.error('Failed to permanently delete:', err);
    return false;
  }

  console.log('   Permanent delete successful');

  // 11. Verify trash no longer has the file
  const trashResp3 = await fetch(`${API_BASE}/api/ldm/offline/trash`, { headers });
  const trashData3 = await trashResp3.json();
  const stillInTrash = trashData3.items.find(i => i.item_id === restoredFile.id);

  if (stillInTrash) {
    console.error('   ERROR: File still in trash after permanent delete!');
    return false;
  }

  console.log('   File permanently deleted (no longer in trash)');

  console.log('\n=== ALL TESTS PASSED ===');
  return true;
}

testLocalRecycleBin().then(success => {
  process.exit(success ? 0 : 1);
}).catch(err => {
  console.error('Test error:', err);
  process.exit(1);
});
