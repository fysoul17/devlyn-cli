#!/usr/bin/env bash
# F11 setup — stage verifier scripts. Store remains in-memory; no data file needed.
set -e

mkdir -p data

# Verifier: a batch with one bad item in the middle returns 400 and leaves
# the stored list exactly as it was before the import.
cat > data/_verify-failed-leaves-unchanged.js <<'JS'
'use strict';
const http = require('http');
const { app } = require('../server');

const s = http.createServer(app).listen(0, async () => {
  const { port } = s.address();

  const get = (path) => new Promise((resolve) => {
    http.get(`http://127.0.0.1:${port}${path}`, (r) => {
      let b = ''; r.on('data', (c) => (b += c));
      r.on('end', () => {
        let d = null; try { d = JSON.parse(b); } catch {}
        resolve({ status: r.statusCode, body: d });
      });
    }).on('error', () => resolve({ status: 0, body: null }));
  });

  const post = (path, body) => new Promise((resolve) => {
    const req = http.request(
      { host: '127.0.0.1', port, method: 'POST', path,
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

  const before = await get('/items');
  const r = await post('/items/import', {
    items: [
      { name: 'good1', qty: 1 },
      { name: '',       qty: 2 }, // invalid: empty name
      { name: 'good2', qty: 3 },
    ],
  });
  const after = await get('/items');

  const same = JSON.stringify(before.body) === JSON.stringify(after.body);
  const ok = r.status === 400 && same;
  console.log(JSON.stringify({ status: r.status, store_unchanged: same, ok }));
  s.close();
  process.exit(ok ? 0 : 1);
});
JS

# Verifier: a fully-valid batch returns 201 and items appear in order with distinct ids.
cat > data/_verify-success.js <<'JS'
'use strict';
const http = require('http');
const { app } = require('../server');

const s = http.createServer(app).listen(0, async () => {
  const { port } = s.address();

  const get = (path) => new Promise((resolve) => {
    http.get(`http://127.0.0.1:${port}${path}`, (r) => {
      let b = ''; r.on('data', (c) => (b += c));
      r.on('end', () => {
        let d = null; try { d = JSON.parse(b); } catch {}
        resolve({ status: r.statusCode, body: d });
      });
    }).on('error', () => resolve({ status: 0, body: null }));
  });

  const post = (path, body) => new Promise((resolve) => {
    const req = http.request(
      { host: '127.0.0.1', port, method: 'POST', path,
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

  const before = await get('/items');
  const beforeLen = (before.body && Array.isArray(before.body.items)) ? before.body.items.length : 0;
  const r = await post('/items/import', {
    items: [
      { name: 'gamma',   qty: 1 },
      { name: 'delta',   qty: 2 },
      { name: 'epsilon', qty: 3 },
    ],
  });
  const after = await get('/items');
  const afterItems = (after.body && Array.isArray(after.body.items)) ? after.body.items : [];

  const ids = afterItems.map((i) => i && i.id);
  const uniq = new Set(ids).size === ids.length;
  const lenOk = afterItems.length === beforeLen + 3;
  const last3Names = afterItems.slice(-3).map((i) => i && i.name).join(',');
  const orderOk = last3Names === 'gamma,delta,epsilon';

  const ok = r.status === 201 && uniq && lenOk && orderOk;
  console.log(JSON.stringify({ status: r.status, uniq, lenOk, orderOk, last3Names, ok }));
  s.close();
  process.exit(ok ? 0 : 1);
});
JS

# Verifier: malformed body (missing items) returns 400 and store is unchanged.
cat > data/_verify-invalid-body.js <<'JS'
'use strict';
const http = require('http');
const { app } = require('../server');

const s = http.createServer(app).listen(0, async () => {
  const { port } = s.address();

  const get = (path) => new Promise((resolve) => {
    http.get(`http://127.0.0.1:${port}${path}`, (r) => {
      let b = ''; r.on('data', (c) => (b += c));
      r.on('end', () => {
        let d = null; try { d = JSON.parse(b); } catch {}
        resolve({ status: r.statusCode, body: d });
      });
    }).on('error', () => resolve({ status: 0, body: null }));
  });

  const post = (path, raw) => new Promise((resolve) => {
    const req = http.request(
      { host: '127.0.0.1', port, method: 'POST', path,
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
    req.write(raw);
    req.end();
  });

  const before = await get('/items');
  const r = await post('/items/import', JSON.stringify({ wrong: 'shape' }));
  const after = await get('/items');

  const same = JSON.stringify(before.body) === JSON.stringify(after.body);
  const ok = r.status === 400 && same;
  console.log(JSON.stringify({ status: r.status, store_unchanged: same, ok }));
  s.close();
  process.exit(ok ? 0 : 1);
});
JS

exit 0
