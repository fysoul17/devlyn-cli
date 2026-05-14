'use strict';
const assert = require('node:assert');
const { spawnSync } = require('node:child_process');
const path = require('node:path');

const work = process.env.BENCH_WORKDIR || process.cwd();
const cli = path.join(work, 'bin', 'cli.js');

const stock = JSON.stringify({ widget: 5 });
const orders = JSON.stringify([
  { id: 'dup', sku: 'widget', qty: 1, priority: 2 },
  { id: 'dup', sku: 'widget', qty: 1, priority: 1 }
]);

const result = spawnSync('node', [cli, 'reserve-stock', '--stock', stock, '--orders', orders], {
  cwd: work,
  encoding: 'utf8'
});

assert.strictEqual(result.status, 2);
assert.strictEqual(result.stdout, '');
assert.deepStrictEqual(JSON.parse(result.stderr), {
  error: 'duplicate_order_id',
  id: 'dup'
});

console.log(JSON.stringify({ ok: true }));
