import { test, expect } from '@playwright/test';

/**
 * P9: Offline Storage Folder Tests
 *
 * Tests folder CRUD operations in Offline Storage:
 * 1. Create folder in Offline Storage
 * 2. List folders in Offline Storage
 * 3. Delete folder from Offline Storage
 * 4. Rename folder in Offline Storage
 */

const API_URL = 'http://localhost:8888';

// Helper to get auth token
async function getAuthToken(request: any): Promise<string> {
  const response = await request.post(`${API_URL}/api/v2/auth/login`, {
    data: { username: 'admin', password: 'admin123' }
  });
  const { access_token } = await response.json();
  return access_token;
}

test.describe('P9: Offline Storage Folder Operations', () => {

  test('should create folder in Offline Storage', async ({ request }) => {
    const token = await getAuthToken(request);

    const timestamp = Date.now();
    const folderName = `test_folder_${timestamp}`;

    const response = await request.post(`${API_URL}/api/ldm/offline/storage/folders`, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      data: { name: folderName }
    });

    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.success).toBe(true);
    expect(data.id).toBeDefined();
    expect(data.name).toBe(folderName);
    console.log(`Created folder: id=${data.id}, name='${data.name}'`);

    // Cleanup
    await request.delete(`${API_URL}/api/ldm/offline/storage/folders/${data.id}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
  });

  test('should list folders in Offline Storage', async ({ request }) => {
    const token = await getAuthToken(request);

    // First, create a test folder
    const timestamp = Date.now();
    const folderName = `list_test_folder_${timestamp}`;

    const createResponse = await request.post(`${API_URL}/api/ldm/offline/storage/folders`, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      data: { name: folderName }
    });

    expect(createResponse.ok()).toBeTruthy();
    const createData = await createResponse.json();
    const folderId = createData.id;

    // List folders
    const listResponse = await request.get(`${API_URL}/api/ldm/offline/local-files`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    expect(listResponse.ok()).toBeTruthy();
    const listData = await listResponse.json();
    expect(listData.folders).toBeDefined();
    expect(Array.isArray(listData.folders)).toBe(true);

    // Find our folder
    const foundFolder = listData.folders.find((f: any) => f.id === folderId);
    expect(foundFolder).toBeTruthy();
    expect(foundFolder.name).toBe(folderName);
    console.log(`Found folder in list: id=${foundFolder.id}, name='${foundFolder.name}'`);

    // Cleanup
    await request.delete(`${API_URL}/api/ldm/offline/storage/folders/${folderId}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
  });

  test('should delete folder from Offline Storage', async ({ request }) => {
    const token = await getAuthToken(request);

    // First, create a test folder
    const timestamp = Date.now();
    const folderName = `delete_test_folder_${timestamp}`;

    const createResponse = await request.post(`${API_URL}/api/ldm/offline/storage/folders`, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      data: { name: folderName }
    });

    expect(createResponse.ok()).toBeTruthy();
    const createData = await createResponse.json();
    const folderId = createData.id;

    // Delete the folder
    const deleteResponse = await request.delete(
      `${API_URL}/api/ldm/offline/storage/folders/${folderId}`,
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    );

    expect(deleteResponse.ok()).toBeTruthy();
    const deleteData = await deleteResponse.json();
    expect(deleteData.success).toBe(true);
    console.log(`Deleted folder: id=${folderId}`);

    // Verify folder is gone
    const listResponse = await request.get(`${API_URL}/api/ldm/offline/local-files`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    expect(listResponse.ok()).toBeTruthy();
    const listData = await listResponse.json();
    const foundFolder = listData.folders.find((f: any) => f.id === folderId);
    expect(foundFolder).toBeFalsy();
    console.log(`Verified folder is deleted`);
  });

  test('should rename folder in Offline Storage', async ({ request }) => {
    const token = await getAuthToken(request);

    // First, create a test folder
    const timestamp = Date.now();
    const originalName = `rename_test_folder_${timestamp}`;

    const createResponse = await request.post(`${API_URL}/api/ldm/offline/storage/folders`, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      data: { name: originalName }
    });

    expect(createResponse.ok()).toBeTruthy();
    const createData = await createResponse.json();
    const folderId = createData.id;

    // Rename the folder
    const newName = `renamed_folder_${timestamp}`;
    const renameResponse = await request.put(
      `${API_URL}/api/ldm/offline/storage/folders/${folderId}/rename`,
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
    console.log(`Renamed folder: '${originalName}' -> '${newName}'`);

    // Verify new name
    const listResponse = await request.get(`${API_URL}/api/ldm/offline/local-files`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    expect(listResponse.ok()).toBeTruthy();
    const listData = await listResponse.json();
    const foundFolder = listData.folders.find((f: any) => f.id === folderId);
    expect(foundFolder).toBeTruthy();
    expect(foundFolder.name).toBe(newName);
    console.log(`Verified folder name: '${foundFolder.name}'`);

    // Cleanup
    await request.delete(`${API_URL}/api/ldm/offline/storage/folders/${folderId}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
  });

  test('should create nested folders in Offline Storage', async ({ request }) => {
    const token = await getAuthToken(request);

    const timestamp = Date.now();

    // Create parent folder
    const parentName = `parent_folder_${timestamp}`;
    const parentResponse = await request.post(`${API_URL}/api/ldm/offline/storage/folders`, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      data: { name: parentName }
    });

    expect(parentResponse.ok()).toBeTruthy();
    const parentData = await parentResponse.json();
    const parentId = parentData.id;
    console.log(`Created parent folder: id=${parentId}`);

    // Create child folder inside parent
    const childName = `child_folder_${timestamp}`;
    const childResponse = await request.post(`${API_URL}/api/ldm/offline/storage/folders`, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      data: { name: childName, parent_id: parentId }
    });

    expect(childResponse.ok()).toBeTruthy();
    const childData = await childResponse.json();
    const childId = childData.id;
    console.log(`Created child folder: id=${childId}, parent=${parentId}`);

    // List contents of parent folder
    const listResponse = await request.get(
      `${API_URL}/api/ldm/offline/local-files?parent_id=${parentId}`,
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    );

    expect(listResponse.ok()).toBeTruthy();
    const listData = await listResponse.json();
    expect(listData.folders).toBeDefined();

    // Find child folder
    const foundChild = listData.folders.find((f: any) => f.id === childId);
    expect(foundChild).toBeTruthy();
    expect(foundChild.name).toBe(childName);
    console.log(`Found child folder in parent: '${foundChild.name}'`);

    // Cleanup - delete parent (should cascade)
    await request.delete(`${API_URL}/api/ldm/offline/storage/folders/${parentId}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    console.log(`Cleaned up parent folder (and children)`);
  });

  test('should reject empty folder name', async ({ request }) => {
    const token = await getAuthToken(request);

    const response = await request.post(`${API_URL}/api/ldm/offline/storage/folders`, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      data: { name: '' }
    });

    expect(response.status()).toBeGreaterThanOrEqual(400);
    console.log(`Empty name correctly rejected with status ${response.status()}`);
  });

  test('should reject delete of non-existent folder', async ({ request }) => {
    const token = await getAuthToken(request);

    const fakeId = 999999999;
    const response = await request.delete(
      `${API_URL}/api/ldm/offline/storage/folders/${fakeId}`,
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    );

    expect(response.status()).toBe(400);
    const data = await response.json();
    expect(data.detail).toContain('not found');
    console.log(`Non-existent folder delete correctly rejected: ${data.detail}`);
  });
});
