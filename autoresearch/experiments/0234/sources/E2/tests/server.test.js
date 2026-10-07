const { test } = require('node:test');
const assert = require('node:assert');
const http = require('node:http');
const { app } = require('../server');

function startServer() {
  return new Promise((resolve) => {
    const server = http.createServer(app);
    server.listen(0, () => resolve(server));
  });
}

function get(server, path) {
  return new Promise((resolve, reject) => {
    const { port } = server.address();
    http
      .get(`http://127.0.0.1:${port}${path}`, (res) => {
        let body = '';
        res.on('data', (chunk) => (body += chunk));
        res.on('end', () => resolve({ status: res.statusCode, body: JSON.parse(body) }));
      })
      .on('error', reject);
  });
}

test('GET /health returns ok', async () => {
  const server = await startServer();
  try {
    const { status, body } = await get(server, '/health');
    assert.strictEqual(status, 200);
    assert.deepStrictEqual(body, { status: 'ok' });
  } finally {
    server.close();
  }
});

test('GET /items returns list', async () => {
  const server = await startServer();
  try {
    const { status, body } = await get(server, '/items');
    assert.strictEqual(status, 200);
    assert.ok(Array.isArray(body.items));
    assert.ok(body.items.length >= 2);
  } finally {
    server.close();
  }
});

test('GET /items/:id returns 404 for missing', async () => {
  const server = await startServer();
  try {
    const { status, body } = await get(server, '/items/99999');
    assert.strictEqual(status, 404);
    assert.strictEqual(body.error, 'not_found');
  } finally {
    server.close();
  }
});
