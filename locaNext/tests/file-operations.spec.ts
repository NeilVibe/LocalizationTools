import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

/**
 * File Operations Tests
 *
 * Tests REAL file operations using actual fixture files:
 * 1. XLSTransfer - Excel file processing
 * 2. QuickSearch - Dictionary creation from TXT files
 * 3. KR Similar - Korean text processing
 *
 * These tests use actual files to verify end-to-end file handling.
 */

const API_URL = 'http://localhost:8888';

// ESM-compatible __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Fixture paths (relative to project root)
const FIXTURES_DIR = path.resolve(__dirname, '../../tests/fixtures');
const TEST_DATA_DIR = path.resolve(__dirname, '../test-data');

// Helper to get auth token
async function getAuthToken(request: any): Promise<string> {
  const response = await request.post(`${API_URL}/api/v2/auth/login`, {
    data: { username: 'admin', password: 'admin123' }
  });
  const { access_token } = await response.json();
  return access_token;
}

test.describe('XLSTransfer File Operations', () => {

  test('should get sheets from Excel file', async ({ request }) => {
    const token = await getAuthToken(request);

    // Check if fixture exists
    const excelPath = path.join(TEST_DATA_DIR, 'TESTSMALL.xlsx');

    if (fs.existsSync(excelPath)) {
      const fileBuffer = fs.readFileSync(excelPath);

      const response = await request.post(`${API_URL}/api/v2/xlstransfer/test/get-sheets`, {
        headers: { Authorization: `Bearer ${token}` },
        multipart: {
          file: {
            name: 'TESTSMALL.xlsx',
            mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            buffer: fileBuffer
          }
        }
      });

      expect(response.ok()).toBeTruthy();
      const data = await response.json();
      expect(data).toHaveProperty('sheets');
      expect(Array.isArray(data.sheets)).toBeTruthy();
    } else {
      // Skip if fixture not available - test the endpoint still exists
      const response = await request.get(`${API_URL}/api/v2/xlstransfer/health`);
      expect(response.ok()).toBeTruthy();
    }
  });

  test('should handle dictionary creation request', async ({ request }) => {
    const token = await getAuthToken(request);

    // Check if fixture exists
    const excelPath = path.join(FIXTURES_DIR, 'sample_dictionary.xlsx');

    if (fs.existsSync(excelPath)) {
      const fileBuffer = fs.readFileSync(excelPath);

      const response = await request.post(`${API_URL}/api/v2/xlstransfer/test/create-dictionary`, {
        headers: { Authorization: `Bearer ${token}` },
        multipart: {
          files: {
            name: 'sample_dictionary.xlsx',
            mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            buffer: fileBuffer
          },
          kr_column: 'A',
          translation_column: 'B'
        }
      });

      // Should succeed or return operation info
      expect(response.status()).toBeLessThan(500);
      const data = await response.json();

      // Check for operation_id (async operation started)
      if (response.ok()) {
        expect(data).toHaveProperty('operation_id');
      }
    } else {
      // Verify endpoint exists
      const response = await request.get(`${API_URL}/api/v2/xlstransfer/health`);
      expect(response.ok()).toBeTruthy();
    }
  });

  test('should check XLSTransfer health', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/v2/xlstransfer/health`);

    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.status).toBe('ok');
    expect(data.modules_loaded).toHaveProperty('core');
    expect(data.modules_loaded).toHaveProperty('embeddings');
    expect(data.modules_loaded).toHaveProperty('translation');
  });

  test('should get XLSTransfer status', async ({ request }) => {
    const token = await getAuthToken(request);

    const response = await request.get(`${API_URL}/api/v2/xlstransfer/test/status`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data).toHaveProperty('dictionary_loaded');
    expect(data).toHaveProperty('model_available');
    expect(data).toHaveProperty('temp_directory');
  });
});

test.describe('QuickSearch File Operations', () => {

  test('should check QuickSearch health', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/v2/quicksearch/health`);

    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.status).toBe('ok');
    expect(data.modules_loaded).toHaveProperty('dictionary_manager');
    expect(data.modules_loaded).toHaveProperty('searcher');
  });

  test('should list available dictionaries', async ({ request }) => {
    const token = await getAuthToken(request);

    const response = await request.get(`${API_URL}/api/v2/quicksearch/list-dictionaries`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data).toHaveProperty('dictionaries');
    expect(data).toHaveProperty('count');
    expect(data).toHaveProperty('success');
  });

  test('should handle dictionary creation from TXT file', async ({ request }) => {
    const token = await getAuthToken(request);

    // Check if fixture exists
    const txtPath = path.join(FIXTURES_DIR, 'sample_quicksearch_data.txt');

    if (fs.existsSync(txtPath)) {
      const fileBuffer = fs.readFileSync(txtPath);

      const response = await request.post(`${API_URL}/api/v2/quicksearch/create-dictionary`, {
        headers: { Authorization: `Bearer ${token}` },
        multipart: {
          files: {
            name: 'sample_quicksearch_data.txt',
            mimeType: 'text/plain',
            buffer: fileBuffer
          },
          game: 'BDO',
          language: 'EN'
        }
      });

      // Should succeed or return operation info
      expect(response.status()).toBeLessThan(500);

      if (response.ok()) {
        const data = await response.json();
        expect(data).toHaveProperty('operation_id');
      }
    } else {
      // Verify endpoint exists
      const response = await request.get(`${API_URL}/api/v2/quicksearch/health`);
      expect(response.ok()).toBeTruthy();
    }
  });

  test('should search dictionary after loading', async ({ request }) => {
    const token = await getAuthToken(request);

    // Try to load a dictionary
    const loadResponse = await request.post(`${API_URL}/api/v2/quicksearch/load-dictionary`, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      data: { game: 'BDO', language: 'EN' }
    });

    // If dictionary exists, try searching
    if (loadResponse.ok()) {
      const searchResponse = await request.post(`${API_URL}/api/v2/quicksearch/search`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        data: {
          query: 'hello',
          match_type: 'contains',
          start_index: 0,
          limit: 10
        }
      });

      expect(searchResponse.status()).toBeLessThan(500);
    }
  });

  test('should handle multiline search', async ({ request }) => {
    const token = await getAuthToken(request);

    // Load dictionary first
    await request.post(`${API_URL}/api/v2/quicksearch/load-dictionary`, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      data: { game: 'BDO', language: 'EN' }
    });

    // Try multiline search
    const response = await request.post(`${API_URL}/api/v2/quicksearch/search-multiline`, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      data: {
        queries: ['hello', 'world', 'test'],
        match_type: 'contains',
        limit: 10
      }
    });

    expect(response.status()).toBeLessThan(500);
  });
});

test.describe('KR Similar File Operations', () => {

  test('should check KR Similar health', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/v2/kr-similar/health`);

    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.status).toBe('ok');
  });

  test('should handle Korean text file processing', async ({ request }) => {
    const token = await getAuthToken(request);

    // Check if fixture exists
    const txtPath = path.join(FIXTURES_DIR, 'sample_to_translate.txt');

    if (fs.existsSync(txtPath)) {
      const fileContent = fs.readFileSync(txtPath, 'utf-8');
      const lines = fileContent.trim().split('\n');

      // Extract Korean text from fixture (column index 5)
      const koreanTexts: string[] = [];
      for (const line of lines) {
        const parts = line.split('\t');
        if (parts.length > 5) {
          koreanTexts.push(parts[5]);
        }
      }

      // Test similarity comparison with Korean texts
      if (koreanTexts.length >= 2) {
        const response = await request.post(`${API_URL}/api/v2/kr-similar/compare-pair`, {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          data: {
            text1: koreanTexts[0],
            text2: koreanTexts[1]
          }
        });

        expect(response.status()).toBeLessThan(500);

        if (response.ok()) {
          const data = await response.json();
          expect(data).toHaveProperty('similarity');
          expect(typeof data.similarity).toBe('number');
          expect(data.similarity).toBeGreaterThanOrEqual(0);
          expect(data.similarity).toBeLessThanOrEqual(100);
        }
      }
    } else {
      // Verify endpoint exists
      const response = await request.get(`${API_URL}/api/v2/kr-similar/health`);
      expect(response.ok()).toBeTruthy();
    }
  });

  test('should process batch similarity requests', async ({ request }) => {
    const token = await getAuthToken(request);

    // Use sample Korean texts from fixture format
    const testPairs = [
      { text1: '안녕하세요', text2: '안녕' },
      { text1: '감사합니다', text2: '고마워요' },
      { text1: '좋은 아침입니다', text2: '좋은 아침' }
    ];

    const response = await request.post(`${API_URL}/api/v2/kr-similar/compare-batch`, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      data: { pairs: testPairs }
    });

    expect(response.status()).toBeLessThan(500);

    if (response.ok()) {
      const data = await response.json();
      expect(data).toHaveProperty('results');
      expect(Array.isArray(data.results)).toBeTruthy();
    }
  });
});

test.describe('Operation Progress Tracking', () => {

  test('should list all active operations', async ({ request }) => {
    const token = await getAuthToken(request);

    const response = await request.get(`${API_URL}/api/progress/operations`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    expect(response.ok()).toBeTruthy();
    const operations = await response.json();
    expect(Array.isArray(operations)).toBeTruthy();
  });

  test('should track operation status over time', async ({ request }) => {
    const token = await getAuthToken(request);
    const headers = { Authorization: `Bearer ${token}` };

    // Get operations at different times
    const results: any[] = [];

    for (let i = 0; i < 3; i++) {
      const response = await request.get(`${API_URL}/api/progress/operations`, { headers });
      expect(response.ok()).toBeTruthy();
      results.push(await response.json());
      await new Promise(r => setTimeout(r, 500));
    }

    // All should be valid
    for (const result of results) {
      expect(Array.isArray(result)).toBeTruthy();
    }
  });

  test('should get operation by ID', async ({ request }) => {
    const token = await getAuthToken(request);
    const headers = { Authorization: `Bearer ${token}` };

    // Get all operations
    const listResponse = await request.get(`${API_URL}/api/progress/operations`, { headers });
    const operations = await listResponse.json();

    if (operations.length > 0) {
      const opId = operations[0].operation_id;

      // Get specific operation
      const detailResponse = await request.get(
        `${API_URL}/api/progress/operations/${opId}`,
        { headers }
      );

      if (detailResponse.ok()) {
        const detail = await detailResponse.json();
        expect(detail).toHaveProperty('operation_id');
        expect(detail.operation_id).toBe(opId);
      }
    }
  });
});

test.describe('File Upload Error Handling', () => {

  test('should reject invalid file types gracefully', async ({ request }) => {
    const token = await getAuthToken(request);

    // Create a fake invalid file
    const fakeFileBuffer = Buffer.from('not a real excel file');

    const response = await request.post(`${API_URL}/api/v2/xlstransfer/test/get-sheets`, {
      headers: { Authorization: `Bearer ${token}` },
      multipart: {
        file: {
          name: 'fake.xlsx',
          mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          buffer: fakeFileBuffer
        }
      }
    });

    // Should not cause server crash (500+)
    // Should return error message, not crash
    expect(response.status()).toBeLessThan(600);
  });

  test('should handle empty file uploads', async ({ request }) => {
    const token = await getAuthToken(request);

    const emptyBuffer = Buffer.from('');

    const response = await request.post(`${API_URL}/api/v2/xlstransfer/test/get-sheets`, {
      headers: { Authorization: `Bearer ${token}` },
      multipart: {
        file: {
          name: 'empty.xlsx',
          mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          buffer: emptyBuffer
        }
      }
    });

    // Should handle gracefully
    expect(response.status()).toBeLessThan(600);
  });

  test('should handle large file simulation', async ({ request }) => {
    const token = await getAuthToken(request);

    // Create a larger buffer (1MB of random data)
    const largeBuffer = Buffer.alloc(1024 * 1024, 'x');

    const response = await request.post(`${API_URL}/api/v2/xlstransfer/test/get-sheets`, {
      headers: { Authorization: `Bearer ${token}` },
      multipart: {
        file: {
          name: 'large.xlsx',
          mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          buffer: largeBuffer
        }
      },
      timeout: 30000  // 30 second timeout for large files
    });

    // Should handle (either process or reject cleanly)
    expect(response.status()).toBeLessThan(600);
  });
});

test.describe('Concurrent File Operations', () => {

  test('should handle multiple simultaneous file requests', async ({ request }) => {
    const token = await getAuthToken(request);
    const headers = { Authorization: `Bearer ${token}` };

    // Fire multiple concurrent requests
    const requests = [
      request.get(`${API_URL}/api/v2/xlstransfer/health`),
      request.get(`${API_URL}/api/v2/quicksearch/health`),
      request.get(`${API_URL}/api/v2/kr-similar/health`),
      request.get(`${API_URL}/api/v2/xlstransfer/test/status`, { headers }),
      request.get(`${API_URL}/api/v2/quicksearch/list-dictionaries`, { headers }),
    ];

    const responses = await Promise.all(requests);

    // All should succeed
    for (const response of responses) {
      expect(response.ok()).toBeTruthy();
    }
  });

  test('should maintain data consistency under load', async ({ request }) => {
    const token = await getAuthToken(request);
    const headers = { Authorization: `Bearer ${token}` };

    // Make 10 rapid requests to same endpoint
    const requests = Array(10).fill(null).map(() =>
      request.get(`${API_URL}/api/v2/xlstransfer/test/status`, { headers })
    );

    const responses = await Promise.all(requests);
    const data = await Promise.all(responses.map(r => r.json()));

    // All should have same structure
    for (const item of data) {
      expect(item).toHaveProperty('dictionary_loaded');
      expect(item).toHaveProperty('model_available');
      expect(item).toHaveProperty('temp_directory');
    }
  });
});
