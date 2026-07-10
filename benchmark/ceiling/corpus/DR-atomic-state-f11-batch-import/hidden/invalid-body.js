'use strict';
const path = require('node:path');
const { invokeApp } = require('./invoke-app');

const work = process.env.BENCH_WORKDIR || process.cwd();
const { app } = require(path.join(work, 'server'));

async function main() {
  const before = await invokeApp(app, { path: '/items' });
  const cases = [
    { label: 'empty', body: undefined },
    { label: 'missing_items', body: JSON.stringify({ wrong: 'shape' }) },
    { label: 'non_array_items', body: JSON.stringify({ items: {} }) },
  ];
  const results = [];

  for (const testCase of cases) {
    const response = await invokeApp(app, {
      method: 'POST',
      path: '/items/import',
      headers: { 'Content-Type': 'application/json' },
      body: testCase.body,
    });
    const after = await invokeApp(app, { path: '/items' });
    results.push({
      label: testCase.label,
      status: response.status,
      // Public contract (task.txt): "An empty body, missing `items`, or a non-array `items` value must return `400` with `{ error: 'invalid_body' }`; `GET /items` must likewise be unchanged."
      bodyExact: JSON.stringify(response.body) === JSON.stringify({ error: 'invalid_body' }),
      unchanged: JSON.stringify(before.body) === JSON.stringify(after.body),
    });
  }

  const ok = results.every((result) => result.status === 400 && result.bodyExact && result.unchanged);
  console.log(JSON.stringify({ results, ok }));
  process.exitCode = ok ? 0 : 1;
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
