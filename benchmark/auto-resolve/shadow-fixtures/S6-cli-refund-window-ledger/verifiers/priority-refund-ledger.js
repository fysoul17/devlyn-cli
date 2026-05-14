'use strict';
const assert = require('node:assert');
const { spawnSync } = require('node:child_process');
const path = require('node:path');

const work = process.env.BENCH_WORKDIR || process.cwd();
const cli = path.join(work, 'bin', 'cli.js');

const policies = JSON.stringify({
  electronics: { refund_window_days: 30, restocking_fee_cents: 150 },
  apparel: { refund_window_days: 45, restocking_fee_cents: 25 }
});
const orders = JSON.stringify([
  { id: 'ord-a', category: 'electronics', paid_cents: 1000, purchased_on: '2026-01-01', fulfilled: true },
  { id: 'ord-b', category: 'apparel', paid_cents: 600, purchased_on: '2026-01-10', fulfilled: true },
  { id: 'ord-c', category: 'electronics', paid_cents: 400, purchased_on: '2025-12-01', fulfilled: true },
  { id: 'ord-d', category: 'apparel', paid_cents: 500, purchased_on: '2026-01-15', fulfilled: false }
]);
const refunds = JSON.stringify([
  { id: 'low-a', order: 'ord-a', cents: 500, priority: 1, requested_on: '2026-01-08' },
  { id: 'expired-c', order: 'ord-c', cents: 100, priority: 9, requested_on: '2026-02-01' },
  { id: 'high-a', order: 'ord-a', cents: 800, priority: 10, requested_on: '2026-01-09' },
  { id: 'unknown', order: 'missing', cents: 50, priority: 8, requested_on: '2026-01-09' },
  { id: 'unfulfilled', order: 'ord-d', cents: 50, priority: 7, requested_on: '2026-01-20' },
  { id: 'apparel-ok', order: 'ord-b', cents: 300, priority: 6, requested_on: '2026-01-20' }
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

assert.strictEqual(result.status, 0, result.stderr || result.stdout);
assert.strictEqual(result.stderr, '');
const parsed = JSON.parse(result.stdout);

assert.deepStrictEqual(parsed, {
  approved: [
    { id: 'high-a', order: 'ord-a', refund_cents: 800, fee_cents: 150, net_cents: 650 },
    { id: 'apparel-ok', order: 'ord-b', refund_cents: 300, fee_cents: 25, net_cents: 275 }
  ],
  rejected: [
    { id: 'low-a', reason: 'over_refund' },
    { id: 'expired-c', reason: 'window_expired' },
    { id: 'unknown', reason: 'unknown_order' },
    { id: 'unfulfilled', reason: 'unfulfilled_order' }
  ],
  orders: [
    { id: 'ord-a', remaining_refundable_cents: 200 },
    { id: 'ord-b', remaining_refundable_cents: 300 },
    { id: 'ord-c', remaining_refundable_cents: 400 },
    { id: 'ord-d', remaining_refundable_cents: 500 }
  ]
});

console.log(JSON.stringify({ ok: true }));
