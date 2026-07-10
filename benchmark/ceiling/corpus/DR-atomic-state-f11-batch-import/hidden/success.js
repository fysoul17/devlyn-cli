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
  const appended = afterItems.slice(beforeItems.length);
  const appendedIds = appended.map((item) => item && item.id);
  const beforeIds = new Set(beforeItems.map((item) => item && item.id));
  // Public contract (task.txt): "Every appended row must receive a distinct numeric `id` that does not collide with any existing item id."
  const numericIds = appendedIds.every((id) => typeof id === 'number');
  const distinctIds = new Set(appendedIds).size === appendedIds.length;
  const noExistingCollision = appendedIds.every((id) => !beforeIds.has(id));
  const lengthOk = afterItems.length === beforeItems.length + 3;
  const names = appended.map((item) => item && item.name).join(',');
  const orderOk = names === 'gamma,delta,epsilon';
  // Public contract (task.txt): "When every item is valid, append all of them in input order and respond `201` with `{ inserted: <count> }`."
  const responseBodyExact = JSON.stringify(response.body) === JSON.stringify({ inserted: 3 });
  const ok = response.status === 201
    && responseBodyExact
    && numericIds
    && distinctIds
    && noExistingCollision
    && lengthOk
    && orderOk;
  console.log(JSON.stringify({
    status: response.status,
    response_body_exact: responseBodyExact,
    numeric_ids: numericIds,
    distinct_ids: distinctIds,
    no_existing_collision: noExistingCollision,
    lengthOk,
    orderOk,
    names,
    ok,
  }));
  process.exitCode = ok ? 0 : 1;
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
