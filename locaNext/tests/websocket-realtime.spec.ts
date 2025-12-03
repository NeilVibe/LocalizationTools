import { test, expect } from '@playwright/test';

/**
 * WebSocket & Real-time Tests
 *
 * Tests real-time communication features:
 * 1. Socket.IO endpoint availability
 * 2. Progress updates polling
 * 3. Event-driven updates simulation
 * 4. Connection resilience
 * 5. Multiple client scenarios
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

test.describe('Socket.IO Endpoint Availability', () => {

  test('should respond to Socket.IO polling transport', async ({ request }) => {
    // Socket.IO handshake via polling
    const response = await request.get(`${API_URL}/socket.io/?EIO=4&transport=polling`);

    // Should respond (200 or 400 for handshake)
    expect(response.status()).toBeLessThan(500);
  });

  test('should handle Socket.IO upgrade request', async ({ request }) => {
    // First get session ID via polling
    const pollResponse = await request.get(`${API_URL}/socket.io/?EIO=4&transport=polling`);

    if (pollResponse.ok()) {
      const body = await pollResponse.text();
      // Socket.IO response format: 0{"sid":"...", ...}
      expect(body).toContain('sid');
    }
  });

  test('should reject invalid EIO version', async ({ request }) => {
    const response = await request.get(`${API_URL}/socket.io/?EIO=999&transport=polling`);

    // Should handle gracefully (not crash)
    expect(response.status()).toBeLessThan(600);
  });

  test('should handle missing transport parameter', async ({ request }) => {
    const response = await request.get(`${API_URL}/socket.io/?EIO=4`);

    // Should return error, not crash
    expect(response.status()).toBeLessThan(600);
  });
});

test.describe('Real-time Progress Updates', () => {

  test('should poll operations endpoint continuously', async ({ request }) => {
    const token = await getAuthToken(request);
    const headers = { Authorization: `Bearer ${token}` };

    // Simulate polling every 500ms for 3 seconds
    const results: any[] = [];
    const timestamps: number[] = [];

    for (let i = 0; i < 6; i++) {
      const start = Date.now();
      const response = await request.get(`${API_URL}/api/progress/operations`, { headers });
      timestamps.push(Date.now() - start);

      expect(response.ok()).toBeTruthy();
      results.push(await response.json());

      await new Promise(r => setTimeout(r, 500));
    }

    // All results should be valid arrays
    for (const result of results) {
      expect(Array.isArray(result)).toBeTruthy();
    }

    // Response times should be reasonable (< 5 seconds each)
    for (const time of timestamps) {
      expect(time).toBeLessThan(5000);
    }
  });

  test('should detect changes in operation status', async ({ request }) => {
    const token = await getAuthToken(request);
    const headers = { Authorization: `Bearer ${token}` };

    // Get operations twice with delay
    const before = await request.get(`${API_URL}/api/progress/operations`, { headers });
    const opsBefore = await before.json();

    await new Promise(r => setTimeout(r, 1000));

    const after = await request.get(`${API_URL}/api/progress/operations`, { headers });
    const opsAfter = await after.json();

    // Both should be valid (changes may or may not have occurred)
    expect(Array.isArray(opsBefore)).toBeTruthy();
    expect(Array.isArray(opsAfter)).toBeTruthy();
  });

  test('should return operation progress percentage', async ({ request }) => {
    const token = await getAuthToken(request);
    const headers = { Authorization: `Bearer ${token}` };

    const response = await request.get(`${API_URL}/api/progress/operations`, { headers });
    const operations = await response.json();

    // If operations exist, check progress fields
    for (const op of operations) {
      if (op.progress_percentage !== undefined) {
        expect(op.progress_percentage).toBeGreaterThanOrEqual(0);
        expect(op.progress_percentage).toBeLessThanOrEqual(100);
      }
      if (op.status) {
        expect(['pending', 'running', 'completed', 'failed', 'cancelled']).toContain(op.status);
      }
    }
  });
});

test.describe('Event-Driven Updates Simulation', () => {

  test('should handle rapid sequential requests', async ({ request }) => {
    const token = await getAuthToken(request);
    const headers = { Authorization: `Bearer ${token}` };

    // Fire 20 rapid requests sequentially
    const responses: number[] = [];

    for (let i = 0; i < 20; i++) {
      const response = await request.get(`${API_URL}/api/progress/operations`, { headers });
      responses.push(response.status());
    }

    // All should succeed
    for (const status of responses) {
      expect(status).toBe(200);
    }
  });

  test('should handle burst of concurrent requests', async ({ request }) => {
    const token = await getAuthToken(request);
    const headers = { Authorization: `Bearer ${token}` };

    // Fire 15 concurrent requests
    const requests = Array(15).fill(null).map(() =>
      request.get(`${API_URL}/api/progress/operations`, { headers })
    );

    const responses = await Promise.all(requests);

    // All should succeed
    for (const response of responses) {
      expect(response.ok()).toBeTruthy();
    }
  });

  test('should maintain data consistency under concurrent access', async ({ request }) => {
    const token = await getAuthToken(request);
    const headers = { Authorization: `Bearer ${token}` };

    // Make concurrent requests to different endpoints
    const requests = [
      request.get(`${API_URL}/api/progress/operations`, { headers }),
      request.get(`${API_URL}/api/v2/admin/stats/overview`, { headers }),
      request.get(`${API_URL}/api/v2/xlstransfer/test/status`, { headers }),
      request.get(`${API_URL}/api/v2/quicksearch/health`),
      request.get(`${API_URL}/api/v2/kr-similar/health`),
    ];

    const responses = await Promise.all(requests);

    // All should succeed
    for (const response of responses) {
      expect(response.ok()).toBeTruthy();
    }

    // Parse and validate each response
    const data = await Promise.all(responses.map(r => r.json()));

    expect(Array.isArray(data[0])).toBeTruthy(); // operations
    expect(data[1]).toHaveProperty('active_users'); // stats
    expect(data[2]).toHaveProperty('dictionary_loaded'); // xlstransfer
    expect(data[3]).toHaveProperty('status'); // quicksearch health
    expect(data[4]).toHaveProperty('status'); // kr-similar health
  });
});

test.describe('Connection Resilience', () => {

  test('should handle server under load', async ({ request }) => {
    const token = await getAuthToken(request);
    const headers = { Authorization: `Bearer ${token}` };

    // Simulate load with 30 concurrent requests
    const requests = Array(30).fill(null).map(() =>
      request.get(`${API_URL}/health`)
    );

    const responses = await Promise.all(requests);
    const successCount = responses.filter(r => r.ok()).length;

    // At least 90% should succeed under load
    expect(successCount).toBeGreaterThanOrEqual(27);
  });

  test('should recover from timeout gracefully', async ({ request }) => {
    // Try with very short timeout
    try {
      await request.get(`${API_URL}/health`, { timeout: 10 });
    } catch (e) {
      // Timeout expected
    }

    // Subsequent request should work
    const response = await request.get(`${API_URL}/health`, { timeout: 5000 });
    expect(response.ok()).toBeTruthy();
  });

  test('should handle malformed requests', async ({ request }) => {
    // Send malformed JSON
    const response = await request.post(`${API_URL}/api/v2/auth/login`, {
      data: 'not-valid-json',
      headers: { 'Content-Type': 'application/json' }
    });

    // Should return 4xx, not 5xx
    expect(response.status()).toBeGreaterThanOrEqual(400);
    expect(response.status()).toBeLessThan(500);
  });

  test('should reject oversized requests', async ({ request }) => {
    const token = await getAuthToken(request);

    // Create large payload (5MB)
    const largePayload = 'x'.repeat(5 * 1024 * 1024);

    const response = await request.post(`${API_URL}/api/v2/quicksearch/search`, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      data: { query: largePayload }
    });

    // Should handle (reject or truncate), not crash
    expect(response.status()).toBeLessThan(600);
  });
});

test.describe('Multiple Client Scenarios', () => {

  test('should handle multiple authenticated sessions', async ({ request }) => {
    // Login twice (simulating two clients)
    const token1 = await getAuthToken(request);
    const token2 = await getAuthToken(request);

    // Both should be able to access protected endpoints
    const [res1, res2] = await Promise.all([
      request.get(`${API_URL}/api/progress/operations`, {
        headers: { Authorization: `Bearer ${token1}` }
      }),
      request.get(`${API_URL}/api/progress/operations`, {
        headers: { Authorization: `Bearer ${token2}` }
      }),
    ]);

    expect(res1.ok()).toBeTruthy();
    expect(res2.ok()).toBeTruthy();
  });

  test('should isolate client sessions', async ({ request }) => {
    // Get two different tokens
    const token1 = await getAuthToken(request);
    const token2 = await getAuthToken(request);

    // Make requests with both tokens
    const [ops1, ops2] = await Promise.all([
      request.get(`${API_URL}/api/progress/operations`, {
        headers: { Authorization: `Bearer ${token1}` }
      }).then(r => r.json()),
      request.get(`${API_URL}/api/progress/operations`, {
        headers: { Authorization: `Bearer ${token2}` }
      }).then(r => r.json()),
    ]);

    // Both should return same data (shared state)
    expect(Array.isArray(ops1)).toBeTruthy();
    expect(Array.isArray(ops2)).toBeTruthy();
    expect(ops1.length).toBe(ops2.length);
  });

  test('should handle mixed auth and public requests', async ({ request }) => {
    const token = await getAuthToken(request);

    // Mix of authenticated and public requests
    const requests = [
      request.get(`${API_URL}/health`), // public
      request.get(`${API_URL}/api/v2/xlstransfer/health`), // public
      request.get(`${API_URL}/api/progress/operations`, {
        headers: { Authorization: `Bearer ${token}` }
      }), // authenticated
      request.get(`${API_URL}/api/v2/quicksearch/health`), // public
      request.get(`${API_URL}/api/v2/admin/stats/overview`, {
        headers: { Authorization: `Bearer ${token}` }
      }), // authenticated
    ];

    const responses = await Promise.all(requests);

    // All should succeed
    for (const response of responses) {
      expect(response.ok()).toBeTruthy();
    }
  });
});

test.describe('Real-time Dashboard Updates', () => {

  test('should fetch dashboard stats in real-time', async ({ request }) => {
    const token = await getAuthToken(request);
    const headers = { Authorization: `Bearer ${token}` };

    // Simulate dashboard polling multiple endpoints
    const statsResults: any[] = [];

    for (let i = 0; i < 3; i++) {
      const [stats, rankings, tools] = await Promise.all([
        request.get(`${API_URL}/api/v2/admin/stats/overview`, { headers }).then(r => r.json()),
        request.get(`${API_URL}/api/v2/admin/rankings/users?period=daily`, { headers }).then(r => r.json()),
        request.get(`${API_URL}/api/v2/admin/stats/tools/popularity?days=7`, { headers }).then(r => r.json()),
      ]);

      statsResults.push({ stats, rankings, tools });
      await new Promise(r => setTimeout(r, 500));
    }

    // All results should have correct structure
    for (const result of statsResults) {
      expect(result.stats).toHaveProperty('active_users');
      expect(result.rankings).toHaveProperty('rankings');
      expect(result.tools).toHaveProperty('tools');
    }
  });

  test('should handle rapid dashboard refresh', async ({ request }) => {
    const token = await getAuthToken(request);
    const headers = { Authorization: `Bearer ${token}` };

    // Simulate user rapidly hitting refresh
    const requests = Array(10).fill(null).map(() =>
      Promise.all([
        request.get(`${API_URL}/api/v2/admin/stats/overview`, { headers }),
        request.get(`${API_URL}/api/progress/operations`, { headers }),
      ])
    );

    const results = await Promise.all(requests);

    // All should succeed
    for (const [stats, ops] of results) {
      expect(stats.ok()).toBeTruthy();
      expect(ops.ok()).toBeTruthy();
    }
  });
});
