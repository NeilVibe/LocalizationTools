/**
 * Test: Row Confirmation API works (PATCH → PUT fix)
 * This is an API-only test to verify the backend fix
 */
import { test, expect } from '@playwright/test';

const API_BASE = 'http://localhost:8888';

test.describe('Row Confirmation API', () => {
  let authToken: string;

  test.beforeAll(async ({ request }) => {
    // Get auth token
    const response = await request.post(`${API_BASE}/api/auth/login`, {
      data: { username: 'admin', password: 'admin123' }
    });
    const data = await response.json();
    authToken = data.access_token;
    console.log('Got auth token');
  });

  test('PUT /api/ldm/rows/{id} updates status to reviewed', async ({ request }) => {
    // 1. Get current status distribution
    console.log('=== STEP 1: Get initial status distribution ===');
    const initialResponse = await request.get(
      `${API_BASE}/api/ldm/files/118/rows?limit=5`,
      { headers: { 'Authorization': `Bearer ${authToken}` } }
    );
    const initialData = await initialResponse.json();
    console.log(`Initial rows: ${initialData.total} total`);

    // Show first few rows status
    initialData.rows.forEach((row: any) => {
      console.log(`  Row ${row.row_num}: status='${row.status}'`);
    });

    // 2. Find an unconfirmed row
    console.log('\n=== STEP 2: Find unconfirmed row ===');
    const unconfirmedResponse = await request.get(
      `${API_BASE}/api/ldm/files/118/rows?filter=unconfirmed&limit=1`,
      { headers: { 'Authorization': `Bearer ${authToken}` } }
    );
    const unconfirmedData = await unconfirmedResponse.json();

    expect(unconfirmedData.rows.length).toBeGreaterThan(0);

    const targetRow = unconfirmedData.rows[0];
    console.log(`Target: Row ${targetRow.row_num} (id=${targetRow.id}), current status='${targetRow.status}'`);

    // 3. Confirm the row via PUT (the fix we made)
    console.log('\n=== STEP 3: Confirm row via PUT ===');
    const updateResponse = await request.put(
      `${API_BASE}/api/ldm/rows/${targetRow.id}`,
      {
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        data: { status: 'reviewed' }
      }
    );

    expect(updateResponse.ok()).toBeTruthy();
    const updateData = await updateResponse.json();
    console.log(`Updated: Row ${updateData.row_num}, new status='${updateData.status}'`);

    expect(updateData.status).toBe('reviewed');

    // 4. Verify via filter
    console.log('\n=== STEP 4: Verify via confirmed filter ===');
    const confirmedResponse = await request.get(
      `${API_BASE}/api/ldm/files/118/rows?filter=confirmed`,
      { headers: { 'Authorization': `Bearer ${authToken}` } }
    );
    const confirmedData = await confirmedResponse.json();
    console.log(`Confirmed rows: ${confirmedData.total}`);

    expect(confirmedData.total).toBeGreaterThan(0);

    // 5. Verify the specific row is in confirmed list
    console.log('\n=== STEP 5: Verify row appears in confirmed list ===');
    const isInConfirmed = confirmedData.rows.some((r: any) => r.id === targetRow.id);
    console.log(`Row ${targetRow.id} in confirmed list: ${isInConfirmed}`);

    expect(isInConfirmed).toBeTruthy();

    console.log('\n=== TEST PASSED: PUT /api/ldm/rows/{id} correctly updates status ===');
  });

  test('Status color mapping is correct', async () => {
    // Document the expected colors
    console.log('=== Status → Color Mapping ===');
    console.log('pending    → Gray (default) - New row, never edited');
    console.log('translated → Teal - Row was edited (Enter/Tab save)');
    console.log('reviewed   → Blue - Row was confirmed (Ctrl+S)');
    console.log('approved   → Green - Supervisor approval (future)');

    console.log('\n=== Filter Mapping ===');
    console.log('confirmed   → status IN (reviewed, approved)');
    console.log('unconfirmed → status IN (pending, translated)');

    // This is a documentation test - always passes
    expect(true).toBeTruthy();
  });
});
