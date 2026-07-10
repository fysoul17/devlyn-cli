'use strict';
const path = require('node:path');
const { isDeepStrictEqual } = require('node:util');
const { invokeApp } = require('./invoke-app');

const work = process.env.BENCH_WORKDIR || process.cwd();
const { app } = require(path.join(work, 'server'));

async function main() {
  const before = await invokeApp(app, { path: '/items' });
  const invalidName = await invokeApp(app, {
    method: 'POST',
    path: '/items/import',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      items: [
        { name: 'good1', qty: 1 },
        { name: '', qty: 2 },
        { name: 'good2', qty: 0 },
      ],
    }),
  });
  const afterInvalidName = await invokeApp(app, { path: '/items' });

  const invalidQty = await invokeApp(app, {
    method: 'POST',
    path: '/items/import',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      items: [
        { name: 'good1', qty: 1 },
        { name: 'bad-qty', qty: 0 },
        { name: '', qty: 3 },
      ],
    }),
  });
  const afterInvalidQty = await invokeApp(app, { path: '/items' });

  // Public contract (task.txt): "If an item is invalid, respond `400` with `{ error: 'invalid_batch', index, field }`, where `index` identifies the first invalid item and `field` is `name` or `qty`."
  const nameErrorExact = isDeepStrictEqual(
    invalidName.body,
    { error: 'invalid_batch', index: 1, field: 'name' }
  );
  const qtyErrorExact = isDeepStrictEqual(
    invalidQty.body,
    { error: 'invalid_batch', index: 1, field: 'qty' }
  );
  const unchangedAfterName = JSON.stringify(before.body) === JSON.stringify(afterInvalidName.body);
  const unchangedAfterQty = JSON.stringify(before.body) === JSON.stringify(afterInvalidQty.body);
  const ok = invalidName.status === 400
    && invalidQty.status === 400
    && nameErrorExact
    && qtyErrorExact
    && unchangedAfterName
    && unchangedAfterQty;
  console.log(JSON.stringify({
    invalid_name_status: invalidName.status,
    invalid_qty_status: invalidQty.status,
    name_error_exact: nameErrorExact,
    qty_error_exact: qtyErrorExact,
    unchanged_after_name: unchangedAfterName,
    unchanged_after_qty: unchangedAfterQty,
    ok,
  }));
  process.exitCode = ok ? 0 : 1;
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
