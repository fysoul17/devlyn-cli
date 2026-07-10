'use strict';
const path = require('node:path');
const { invokeApp } = require('./invoke-app');

const work = process.env.BENCH_WORKDIR || process.cwd();
const { app } = require(path.join(work, 'server'));

async function main() {
  const before = await invokeApp(app, { path: '/items' });
  const beforeItems = before.body && Array.isArray(before.body.items) ? before.body.items : [];
  const response = await invokeApp(app, {
    method: 'POST',
    path: '/items/import',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      items: [
        { name: 'gamma', qty: 1 },
        { name: 'delta', qty: 2 },
        { name: 'epsilon', qty: 3 },
      ],
    }),
  });
  const after = await invokeApp(app, { path: '/items' });
  const afterItems = after.body && Array.isArray(after.body.items) ? after.body.items : [];
  const ids = afterItems.map((item) => item && item.id);
  const unique = new Set(ids).size === ids.length;
  const lengthOk = afterItems.length === beforeItems.length + 3;
  const names = afterItems.slice(-3).map((item) => item && item.name).join(',');
  const orderOk = names === 'gamma,delta,epsilon';
  const ok = response.status === 201 && unique && lengthOk && orderOk;
  console.log(JSON.stringify({ status: response.status, unique, lengthOk, orderOk, names, ok }));
  process.exitCode = ok ? 0 : 1;
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
