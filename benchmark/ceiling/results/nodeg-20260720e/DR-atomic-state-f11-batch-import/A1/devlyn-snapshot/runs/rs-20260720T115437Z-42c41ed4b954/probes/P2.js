'use strict';
// P2: POST /items/import - malformed body probe.
// Covers three malformed shapes (empty body, missing `items`, non-array `items`),
// each must respond 400 with the exact { error: 'invalid_body' } body, and
// GET /items must be byte-for-byte unchanged.
// Run against BASE (pre-implementation): POST /items/import does not exist yet,
// so this is expected to fail (404 instead of 400).
const http = require('node:http');
const assert = require('node:assert');
const { app } = require('../../server');

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

function rawRequest(server, path, rawBody, headers) {
  return new Promise((resolve, reject) => {
    const { port } = server.address();
    const req = http.request({ host: '127.0.0.1', port, path, method: 'POST', headers }, (res) => {
      let body = '';
      res.on('data', (chunk) => (body += chunk));
      res.on('end', () => {
        let parsed;
        try {
          parsed = body ? JSON.parse(body) : {};
        } catch (e) {
          parsed = { __unparsed: body };
        }
        resolve({ status: res.statusCode, body: parsed });
      });
    });
    req.on('error', reject);
    if (rawBody !== null) req.write(rawBody);
    req.end();
  });
}

async function assertUnchangedAndRejected(server, label, rawBody, headers) {
  const before = await get(server, '/items');
  const res = await rawRequest(server, '/items/import', rawBody, headers);
  assert.strictEqual(res.status, 400, `[${label}] expected 400, got ${res.status} body=${JSON.stringify(res.body)}`);
  assert.deepStrictEqual(
    res.body,
    { error: 'invalid_body' },
    `[${label}] expected exact {error:'invalid_body'} with no extra/aliased keys, got ${JSON.stringify(res.body)}`
  );
  const after = await get(server, '/items');
  assert.deepStrictEqual(after.body, before.body, `[${label}] expected GET /items unchanged after malformed request`);
}

async function main() {
  const server = await startServer();
  try {
    // Case 1: empty body, no Content-Type
    await assertUnchangedAndRejected(server, 'empty-body', null, {});

    // Case 2: valid JSON object but missing `items` key
    const missingItemsBody = JSON.stringify({});
    await assertUnchangedAndRejected(server, 'missing-items', missingItemsBody, {
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(missingItemsBody),
    });

    // Case 3: `items` present but not an array
    const nonArrayBody = JSON.stringify({ items: 'not-an-array' });
    await assertUnchangedAndRejected(server, 'non-array-items', nonArrayBody, {
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(nonArrayBody),
    });

    console.log('P2 PASS');
  } finally {
    server.close();
  }
}

main().catch((err) => {
  console.error('P2 FAIL:', err.message);
  process.exit(1);
});
