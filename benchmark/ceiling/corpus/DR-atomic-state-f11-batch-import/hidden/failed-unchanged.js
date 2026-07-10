'use strict';
const path = require('node:path');
const { invokeApp } = require('./invoke-app');

const work = process.env.BENCH_WORKDIR || process.cwd();
const { app } = require(path.join(work, 'server'));

async function main() {
  const before = await invokeApp(app, { path: '/items' });
  const response = await invokeApp(app, {
    method: 'POST',
    path: '/items/import',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      items: [
        { name: 'good1', qty: 1 },
        { name: '', qty: 2 },
        { name: 'good2', qty: 3 },
      ],
    }),
  });
  const after = await invokeApp(app, { path: '/items' });
  const unchanged = JSON.stringify(before.body) === JSON.stringify(after.body);
  const ok = response.status === 400 && unchanged;
  console.log(JSON.stringify({ status: response.status, store_unchanged: unchanged, ok }));
  process.exitCode = ok ? 0 : 1;
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
