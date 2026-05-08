#!/usr/bin/env bash
# F15 setup — pre-stage a plausibly-correct items API with a latent
# load-time correctness issue. The implementation passes existing tests;
# the bug only surfaces when several writes are in flight together.
set -e

mkdir -p data

# Seed persisted state.
cat > data/items.json <<'JSON'
{
  "items": [
    { "id": 1, "name": "alpha", "qty": 3 },
    { "id": 2, "name": "beta", "qty": 5 }
  ]
}
JSON

# Pre-staged server implementation. Looks normal — uses fs/promises async
# I/O, validates input, returns sensible status codes. The latent issue is
# that POST /items reads-modifies-writes the JSON file with `await fs.read
# File` followed by `await fs.writeFile`, with no serialization. Two
# concurrent POSTs interleave during the await gap.
cat > server/index.js <<'JS'
const express = require('express');
const fs = require('fs/promises');
const path = require('path');

const app = express();
app.use(express.json());

const DATA_PATH = path.join(__dirname, '..', 'data', 'items.json');

async function readStore() {
  const text = await fs.readFile(DATA_PATH, 'utf8');
  return JSON.parse(text);
}

async function writeStore(data) {
  await fs.writeFile(DATA_PATH, JSON.stringify(data, null, 2) + '\n');
}

app.get('/health', (_req, res) => {
  res.json({ status: 'ok' });
});

app.get('/items', async (_req, res) => {
  const data = await readStore();
  res.json({ items: data.items });
});

app.get('/items/:id', async (req, res) => {
  const id = Number(req.params.id);
  const data = await readStore();
  const item = data.items.find((it) => it.id === id);
  if (!item) {
    res.status(404).json({ error: 'not_found', id });
    return;
  }
  res.json({ item });
});

app.post('/items', async (req, res) => {
  const body = req.body || {};
  if (typeof body.name !== 'string' || body.name.trim() === '') {
    res.status(400).json({ error: 'invalid_body', field: 'name' });
    return;
  }
  if (typeof body.qty !== 'number' || !Number.isInteger(body.qty) || body.qty <= 0) {
    res.status(400).json({ error: 'invalid_body', field: 'qty' });
    return;
  }
  const data = await readStore();
  const newId = data.items.length + 1;
  const newItem = { id: newId, name: body.name, qty: body.qty };
  data.items.push(newItem);
  await writeStore(data);
  res.status(201).json({ item: newItem });
});

if (require.main === module) {
  const port = Number(process.env.PORT) || 3000;
  app.listen(port, () => {
    console.log(`bench-test-repo server listening on :${port}`);
  });
}

module.exports = { app };
JS

# Pre-staged tests covering existing happy paths. The arm must keep these
# passing AND add at least one test for the load-time fix.
cat > tests/server.test.js <<'JS'
const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { app } = require('../server');

const DATA_PATH = path.join(__dirname, '..', 'data', 'items.json');

function startServer() {
  return new Promise((resolve) => {
    const server = http.createServer(app);
    server.listen(0, () => resolve(server));
  });
}

function get(server, p) {
  return new Promise((resolve, reject) => {
    const { port } = server.address();
    http.get(`http://127.0.0.1:${port}${p}`, (res) => {
      let body = '';
      res.on('data', (c) => (body += c));
      res.on('end', () => resolve({ status: res.statusCode, body: JSON.parse(body) }));
    }).on('error', reject);
  });
}

function post(server, p, payload) {
  return new Promise((resolve, reject) => {
    const { port } = server.address();
    const data = JSON.stringify(payload);
    const req = http.request(
      { host: '127.0.0.1', port, method: 'POST', path: p,
        headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) } },
      (res) => {
        let body = '';
        res.on('data', (c) => (body += c));
        res.on('end', () => {
          let parsed = null;
          try { parsed = body ? JSON.parse(body) : null; } catch { parsed = body; }
          resolve({ status: res.statusCode, body: parsed });
        });
      }
    );
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

function snapshotStore() { return fs.readFileSync(DATA_PATH); }
function restoreStore(snapshot) { fs.writeFileSync(DATA_PATH, snapshot); }

test('GET /health returns ok', async () => {
  const s = await startServer();
  try {
    const r = await get(s, '/health');
    assert.strictEqual(r.status, 200);
    assert.deepStrictEqual(r.body, { status: 'ok' });
  } finally { s.close(); }
});

test('GET /items returns the persisted list', async () => {
  const s = await startServer();
  try {
    const r = await get(s, '/items');
    assert.strictEqual(r.status, 200);
    assert.ok(Array.isArray(r.body.items));
    assert.ok(r.body.items.length >= 2);
  } finally { s.close(); }
});

test('GET /items/:id returns a single item', async () => {
  const s = await startServer();
  try {
    const r = await get(s, '/items/1');
    assert.strictEqual(r.status, 200);
    assert.strictEqual(r.body.item.name, 'alpha');
  } finally { s.close(); }
});

test('GET /items/:id returns 404 for missing', async () => {
  const s = await startServer();
  try {
    const r = await get(s, '/items/99999');
    assert.strictEqual(r.status, 404);
    assert.strictEqual(r.body.error, 'not_found');
  } finally { s.close(); }
});

test('POST /items appends a new item with a fresh id', async () => {
  const snap = snapshotStore();
  const s = await startServer();
  try {
    const before = await get(s, '/items');
    const created = await post(s, '/items', { name: 'gamma', qty: 7 });
    assert.strictEqual(created.status, 201);
    assert.strictEqual(created.body.item.name, 'gamma');
    const after = await get(s, '/items');
    assert.strictEqual(after.body.items.length, before.body.items.length + 1);
  } finally { s.close(); restoreStore(snap); }
});

test('POST /items rejects invalid bodies with 400', async () => {
  const snap = snapshotStore();
  const s = await startServer();
  try {
    const r1 = await post(s, '/items', { name: 'noqty' });
    assert.strictEqual(r1.status, 400);
    const r2 = await post(s, '/items', { qty: 5 });
    assert.strictEqual(r2.status, 400);
    const r3 = await post(s, '/items', { name: 'bad', qty: -3 });
    assert.strictEqual(r3.status, 400);
  } finally { s.close(); restoreStore(snap); }
});
JS

# Verifier 1: concurrent POSTs must yield distinct ids and full length.
# This is the discriminator — current implementation FAILS this; a correct
# fix passes.
cat > data/_verify-concurrent.js <<'JS'
'use strict';
const http = require('http');
const fs = require('fs');
const { app } = require('../server');

const SNAP_PATH = 'data/items.json';
const SNAP = fs.readFileSync(SNAP_PATH);

const s = http.createServer(app).listen(0, async () => {
  const { port } = s.address();
  const post = (body) => new Promise((resolve) => {
    const req = http.request(
      { host: '127.0.0.1', port, method: 'POST', path: '/items',
        headers: { 'Content-Type': 'application/json' } },
      (r) => {
        let b = ''; r.on('data', (c) => (b += c));
        r.on('end', () => {
          let d = null; try { d = JSON.parse(b); } catch {}
          resolve({ status: r.statusCode, body: d });
        });
      }
    );
    req.on('error', () => resolve({ status: 0, body: null }));
    req.write(JSON.stringify(body));
    req.end();
  });

  const initial = JSON.parse(fs.readFileSync(SNAP_PATH, 'utf8'));
  const startLen = initial.items.length;

  const results = await Promise.all([
    post({ name: 'gamma', qty: 1 }),
    post({ name: 'delta', qty: 2 }),
    post({ name: 'epsilon', qty: 3 }),
    post({ name: 'zeta', qty: 4 }),
    post({ name: 'eta', qty: 5 }),
  ]);
  // Allow writes to settle.
  await new Promise((r) => setTimeout(r, 300));

  const acked = results.filter((r) => r.status === 201);
  const final = await new Promise((resolve) => {
    http.get(`http://127.0.0.1:${port}/items`, (r) => {
      let b = ''; r.on('data', (c) => (b += c));
      r.on('end', () => {
        let d = null; try { d = JSON.parse(b); } catch {}
        resolve(d);
      });
    });
  });
  const finalItems = (final && Array.isArray(final.items)) ? final.items : [];
  const ids = finalItems.map((i) => i && i.id);
  const uniqueIds = new Set(ids).size === ids.length;
  const lengthOk = finalItems.length === startLen + acked.length;

  // Each ack'd POST's claimed id must appear exactly once in final.
  const ackIdsPresent = acked.every((r) =>
    finalItems.some((it) => it && r.body && it.id === r.body.item.id)
  );
  const allAcked = acked.length === results.length;

  const ok = allAcked && uniqueIds && lengthOk && ackIdsPresent;
  console.log(JSON.stringify({
    acked: acked.length, total: results.length, finalLen: finalItems.length,
    startLen, uniqueIds, lengthOk, ackIdsPresent, ok,
  }));
  fs.writeFileSync(SNAP_PATH, SNAP); // restore for downstream verifiers
  s.close();
  process.exit(ok ? 0 : 1);
});
JS

# Verifier 2: single-POST regression — the fix must not break sequential use.
cat > data/_verify-single.js <<'JS'
'use strict';
const http = require('http');
const fs = require('fs');
const { app } = require('../server');

const SNAP_PATH = 'data/items.json';
const SNAP = fs.readFileSync(SNAP_PATH);

const s = http.createServer(app).listen(0, async () => {
  const { port } = s.address();
  const post = (body) => new Promise((resolve) => {
    const req = http.request(
      { host: '127.0.0.1', port, method: 'POST', path: '/items',
        headers: { 'Content-Type': 'application/json' } },
      (r) => {
        let b = ''; r.on('data', (c) => (b += c));
        r.on('end', () => {
          let d = null; try { d = JSON.parse(b); } catch {}
          resolve({ status: r.statusCode, body: d });
        });
      }
    );
    req.on('error', () => resolve({ status: 0, body: null }));
    req.write(JSON.stringify(body));
    req.end();
  });

  const r = await post({ name: 'solo_check', qty: 9 });
  const get = await new Promise((resolve) => {
    http.get(`http://127.0.0.1:${port}/items`, (rs) => {
      let b = ''; rs.on('data', (c) => (b += c));
      rs.on('end', () => {
        let d = null; try { d = JSON.parse(b); } catch {}
        resolve(d);
      });
    });
  });
  const final = (get && Array.isArray(get.items)) ? get.items : [];
  const present = final.some((it) => it && it.name === 'solo_check' && it.qty === 9);
  const ok = r.status === 201 && r.body && r.body.item && r.body.item.name === 'solo_check' && present;
  console.log(JSON.stringify({ status: r.status, present, ok }));
  fs.writeFileSync(SNAP_PATH, SNAP);
  s.close();
  process.exit(ok ? 0 : 1);
});
JS

exit 0
