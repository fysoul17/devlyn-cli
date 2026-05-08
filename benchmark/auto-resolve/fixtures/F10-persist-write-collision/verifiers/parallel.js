'use strict';
const http = require('http');
const path = require('path');
const { app } = require(path.join(process.env.BENCH_WORKDIR, 'server'));

const s = http.createServer(app).listen(0, () => {
  const { port } = s.address();
  const post = (body) => new Promise((resolve) => {
    const req = http.request(
      { host: '127.0.0.1', port, method: 'POST', path: '/items',
        headers: { 'Content-Type': 'application/json' } },
      (r) => {
        let b = '';
        r.on('data', (c) => (b += c));
        r.on('end', () => resolve({ status: r.statusCode, body: b ? safeJson(b) : null }));
      }
    );
    req.on('error', () => resolve({ status: 0, body: null }));
    req.write(JSON.stringify(body));
    req.end();
  });

  Promise.all([
    post({ name: 'gamma', qty: 1 }),
    post({ name: 'delta', qty: 2 }),
    post({ name: 'epsilon', qty: 3 }),
  ]).then(async (results) => {
    await new Promise((r) => setTimeout(r, 250));
    http.get(`http://127.0.0.1:${port}/items`, (r) => {
      let b = '';
      r.on('data', (c) => (b += c));
      r.on('end', () => {
        let data;
        try { data = JSON.parse(b); } catch { data = { items: [] }; }
        const items = Array.isArray(data.items) ? data.items : [];
        const ids = items.map((i) => i && i.id);
        const uniq = new Set(ids).size;
        const allPosted = results.every((x) => x.status === 201);
        const ok = allPosted && items.length === 5 && uniq === 5;
        console.log(JSON.stringify({
          len: items.length, uniq, status: results.map((r) => r.status), ok,
        }));
        s.close();
        process.exit(ok ? 0 : 1);
      });
    });
  });
});

function safeJson(s) { try { return JSON.parse(s); } catch { return null; } }
