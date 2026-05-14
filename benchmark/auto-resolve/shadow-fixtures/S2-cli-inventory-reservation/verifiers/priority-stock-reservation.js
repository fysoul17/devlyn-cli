'use strict';
const assert = require('node:assert');
const { spawnSync } = require('node:child_process');
const path = require('node:path');

const work = process.env.BENCH_WORKDIR || process.cwd();
const cli = path.join(work, 'bin', 'cli.js');

const stock = JSON.stringify({
  cable: 1,
  widget: 3
});
const orders = JSON.stringify([
  { id: 'low-widget', sku: 'widget', qty: 2, priority: 1 },
  { id: 'vip-widget', sku: 'widget', qty: 2, priority: 10 },
  { id: 'vip-cable', sku: 'cable', qty: 2, priority: 9 },
  { id: 'std-widget', sku: 'widget', qty: 1, priority: 5 }
]);

const result = spawnSync('node', [cli, 'reserve-stock', '--stock', stock, '--orders', orders], {
  cwd: work,
  encoding: 'utf8'
});

assert.strictEqual(result.status, 0, result.stderr || result.stdout);
assert.strictEqual(result.stderr, '');
const parsed = JSON.parse(result.stdout);

assert.deepStrictEqual(parsed, {
  reserved: [
    { id: 'vip-widget', sku: 'widget', qty: 2 },
    { id: 'std-widget', sku: 'widget', qty: 1 }
  ],
  rejected: [
    { id: 'low-widget', reason: 'insufficient_stock' },
    { id: 'vip-cable', reason: 'insufficient_stock' }
  ],
  stock: {
    cable: 1,
    widget: 0
  }
});

console.log(JSON.stringify({ ok: true }));
