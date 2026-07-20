'use strict';
// P1: POST /items/import - compound probe covering
//   (a) all-valid batch: 201, input order preserved, distinct non-colliding ids
//   (b) mixed valid/invalid batch (invalid item not first): 400 with exact
//       { error: 'invalid_batch', index, field } and GET /items left byte-for-byte
//       unchanged (no partial append).
// Run against BASE (pre-implementation): POST /items/import does not exist yet,
// so this is expected to fail (404 instead of 201/400).
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

function post(server, path, payload) {
  return new Promise((resolve, reject) => {
    const { port } = server.address();
    const data = JSON.stringify(payload);
    const req = http.request(
      {
        host: '127.0.0.1',
        port,
        path,
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) },
      },
      (res) => {
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
      }
    );
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

async function main() {
  const server = await startServer();
  try {
    // --- Case A: all-valid batch -> 201, distinct ids, input order preserved ---
    const before = await get(server, '/items');
    const validPayload = { items: [{ name: 'gamma', qty: 2 }, { name: 'delta', qty: 7 }] };
    const validRes = await post(server, '/items/import', validPayload);
    assert.strictEqual(validRes.status, 201, `expected 201 on valid batch, got ${validRes.status} body=${JSON.stringify(validRes.body)}`);
    assert.deepStrictEqual(validRes.body, { inserted: 2 }, `expected exact {inserted:2}, got ${JSON.stringify(validRes.body)}`);

    const afterValid = await get(server, '/items');
    const appended = afterValid.body.items.slice(before.body.items.length);
    assert.strictEqual(appended.length, 2, `expected 2 appended items, got ${appended.length}`);
    assert.strictEqual(appended[0].name, 'gamma', 'expected input order preserved (gamma first)');
    assert.strictEqual(appended[1].name, 'delta', 'expected input order preserved (delta second)');
    const newIds = appended.map((it) => it.id);
    assert.strictEqual(new Set(newIds).size, newIds.length, 'expected distinct ids within the appended batch');
    const existingIds = before.body.items.map((it) => it.id);
    for (const id of newIds) {
      assert.ok(!existingIds.includes(id), `appended id ${id} collides with a pre-existing item id`);
    }

    // --- Case B: mixed valid/invalid batch (invalid item not first) -> 400, unchanged store ---
    const beforeInvalid = await get(server, '/items');
    const invalidPayload = {
      items: [
        { name: 'epsilon', qty: 1 },
        { name: '   ', qty: 4 }, // invalid: whitespace-only name -> fails trim check
        { name: 'zeta', qty: 9 },
      ],
    };
    const invalidRes = await post(server, '/items/import', invalidPayload);
    assert.strictEqual(invalidRes.status, 400, `expected 400 on mixed invalid batch, got ${invalidRes.status} body=${JSON.stringify(invalidRes.body)}`);
    assert.deepStrictEqual(
      invalidRes.body,
      { error: 'invalid_batch', index: 1, field: 'name' },
      `expected exact invalid_batch error body identifying index 1 / field 'name', got ${JSON.stringify(invalidRes.body)}`
    );

    const afterInvalid = await get(server, '/items');
    assert.deepStrictEqual(
      afterInvalid.body,
      beforeInvalid.body,
      'expected GET /items to be byte-for-byte unchanged after a rejected mixed batch (no partial append)'
    );

    console.log('P1 PASS');
  } finally {
    server.close();
  }
}

main().catch((err) => {
  console.error('P1 FAIL:', err.message);
  process.exit(1);
});
