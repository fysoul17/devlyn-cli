'use strict';
const fs = require('fs');
const http = require('http');
const path = require('path');
const { app } = require(path.join(process.env.BENCH_WORKDIR, 'server'));

const before = fs.readFileSync('data/items.json');

const s = http.createServer(app).listen(0, () => {
  const { port } = s.address();
  const req = http.request(
    { host: '127.0.0.1', port, method: 'POST', path: '/items',
      headers: { 'Content-Type': 'application/json' } },
    (r) => {
      let b = '';
      r.on('data', (c) => (b += c));
      r.on('end', () => {
        const after = fs.readFileSync('data/items.json');
        const same = before.equals(after);
        const ok = r.statusCode === 400 && same;
        console.log(JSON.stringify({ status: r.statusCode, store_unchanged: same, ok }));
        s.close();
        process.exit(ok ? 0 : 1);
      });
    }
  );
  req.write(JSON.stringify({ name: 'noqty' }));
  req.end();
});
