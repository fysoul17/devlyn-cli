'use strict';
const assert = require('node:assert');
const { spawnSync } = require('node:child_process');
const path = require('node:path');

const work = process.env.BENCH_WORKDIR || process.cwd();
const cli = path.join(work, 'bin', 'cli.js');

const policies = JSON.stringify({
  apparel: { refund_window_days: 45, restocking_fee_cents: 25 }
});
const orders = JSON.stringify([
  { id: 'ord-a', category: 'apparel', paid_cents: 600, purchased_on: '2026-01-10', fulfilled: true }
]);
const refunds = JSON.stringify([
  { id: 'dup', order: 'ord-a', cents: 100, priority: 2, requested_on: '2026-01-11' },
  { id: 'dup', order: 'ord-a', cents: 100, priority: 1, requested_on: '2026-01-12' }
]);

const result = spawnSync('node', [
  cli,
  'settle-refunds',
  '--policies',
  policies,
  '--orders',
  orders,
  '--refunds',
  refunds
], {
  cwd: work,
  encoding: 'utf8'
});

assert.strictEqual(result.status, 2, result.stdout || result.stderr);
assert.strictEqual(result.stdout, '');
assert.deepStrictEqual(JSON.parse(result.stderr), {
  error: 'duplicate_refund_id',
  id: 'dup'
});

console.log(JSON.stringify({ ok: true }));
