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


function post(server, route, body) {
  return new Promise((resolve, reject) => {
    const req = http.request({ port: server.address().port, host: '127.0.0.1', method: 'POST', path: route,
      headers: { 'content-type': 'application/json' } }, res => {
      let text = '';
      res.on('data', c => text += c);
      res.on('end', () => resolve({ status: res.statusCode, body: JSON.parse(text) }));
    });
    req.on('error', reject);
    req.end(JSON.stringify(body));
  });
}

test('parallel POSTs persist all items with distinct ids', async () => {
  const server = await startServer();
  try {
    const before = (await get(server, '/items')).body.items;
    const results = await Promise.all(Array.from({ length: 5 }, (_, i) => post(server, '/items', { name: `new${i}`, qty: i + 1 })));
    const after = (await get(server, '/items')).body.items;
    assert.ok(results.every(r => r.status === 201));
    assert.strictEqual(new Set(results.map(r => r.body.item.id)).size, 5);
    assert.strictEqual(after.length, before.length + 5);
  } finally { server.close(); }
});

test('invalid POST leaves store bytes unchanged', async () => {
  const fs = require('node:fs');
  const path = require('node:path');
  const store = path.join(__dirname, '../data/items.json');
  const server = await startServer();
  try {
    const before = fs.readFileSync(store);
    const result = await post(server, '/items', { name: 'bad', qty: 0 });
    assert.strictEqual(result.status, 400);
    assert.ok(before.equals(fs.readFileSync(store)));
  } finally { server.close(); }
});
