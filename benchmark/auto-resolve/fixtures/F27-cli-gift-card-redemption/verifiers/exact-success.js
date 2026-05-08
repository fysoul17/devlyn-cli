const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const workdir = process.env.BENCH_WORKDIR || process.cwd();
const input = path.join(os.tmpdir(), `gift-card-success-${process.pid}.json`);

fs.writeFileSync(input, JSON.stringify({
  order_id: 'order-27',
  lines: [
    { sku: 'TEE', qty: 1 },
    { sku: 'SOCKS', qty: 2 },
    { sku: 'TEE', qty: 2 },
    { sku: 'BAG', qty: 1 }
  ],
  redeems: [
    { card_id: 'GC-100', amount_cents: 3000 },
    { card_id: 'GC-200', amount_cents: 1200 },
    { card_id: 'GC-100', amount_cents: 500 }
  ]
}));

const proc = spawnSync('node', ['bin/cli.js', 'gift-card', '--input', input], {
  cwd: workdir,
  encoding: 'utf8'
});

assert.strictEqual(proc.status, 0, proc.stderr || proc.stdout);
assert.strictEqual(proc.stderr, '');
assert.deepStrictEqual(JSON.parse(proc.stdout), {
  order_id: 'order-27',
  subtotal_cents: 12100,
  gift_card_applied_cents: 4700,
  amount_due_cents: 7400,
  items: [
    { sku: 'TEE', qty: 3, line_cents: 7500 },
    { sku: 'SOCKS', qty: 2, line_cents: 1400 },
    { sku: 'BAG', qty: 1, line_cents: 3200 }
  ],
  redemptions: [
    { card_id: 'GC-100', applied_cents: 3500, remaining_balance_cents: 1500 },
    { card_id: 'GC-200', applied_cents: 1200, remaining_balance_cents: 1300 }
  ]
});

process.stdout.write(JSON.stringify({ ok: true }) + '\n');
