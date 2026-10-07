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

test('valid import appends two items', async () => {
  const server = await startServer();
  try {
    const before = (await get(server, '/items')).body.items.length;
    const result = await post(server, '/items/import', { items: [{ name: 'x', qty: 1 }, { name: 'y', qty: 2 }] });
    assert.strictEqual(result.status, 201);
    assert.deepStrictEqual(result.body, { inserted: 2 });
    assert.strictEqual((await get(server, '/items')).body.items.length, before + 2);
  } finally { server.close(); }
});

test('invalid middle element leaves prior list unchanged', async () => {
  const server = await startServer();
  try {
    const before = (await get(server, '/items')).body.items;
    const result = await post(server, '/items/import', { items: [{ name: 'ok', qty: 1 }, { name: '', qty: 2 }] });
    assert.strictEqual(result.status, 400);
    assert.deepStrictEqual((await get(server, '/items')).body.items, before);
  } finally { server.close(); }
});
