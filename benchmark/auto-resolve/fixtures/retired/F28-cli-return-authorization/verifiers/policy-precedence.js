'use strict';
const assert = require('node:assert');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const work = process.env.BENCH_WORKDIR || process.cwd();
const cli = path.join(work, 'bin', 'cli.js');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'f28-return-policy-'));
const input = path.join(tmp, 'return.json');

fs.writeFileSync(input, JSON.stringify({
  today: '2026-05-20',
  order: {
    id: 'O-100',
    purchased_at: '2026-05-01',
    items: [
      { sku: 'SHIRT', qty: 2, unit_cents: 2500, return_window_days: 30, restocking_fee_percent: 10 },
      { sku: 'HEADSET', qty: 1, unit_cents: 12500, return_window_days: 30, restocking_fee_percent: 15 },
      { sku: 'CARD', qty: 1, unit_cents: 5000, return_window_days: 1, restocking_fee_percent: 0, nonreturnable: true }
    ]
  },
  request: {
    id: 'R-200',
    lines: [
      { sku: 'SHIRT', qty: 1, reason: 'changed_mind', condition: 'opened', resolution: 'refund' },
      { sku: 'HEADSET', qty: 1, reason: 'defective', condition: 'opened', resolution: 'exchange' },
      { sku: 'CARD', qty: 1, reason: 'changed_mind', condition: 'sealed', resolution: 'refund' }
    ]
  }
}), 'utf8');

const stdout = execFileSync('node', [cli, 'authorize-return', '--input', input], {
  cwd: work,
  encoding: 'utf8',
  stdio: ['ignore', 'pipe', 'pipe']
});
const parsed = JSON.parse(stdout);

assert.deepStrictEqual(parsed, {
  request_id: 'R-200',
  order_id: 'O-100',
  approved: [
    {
      sku: 'SHIRT',
      qty: 1,
      resolution: 'refund',
      gross_cents: 2500,
      restocking_fee_cents: 250,
      refund_cents: 2250,
      exchange_credit_cents: 0
    },
    {
      sku: 'HEADSET',
      qty: 1,
      resolution: 'exchange',
      gross_cents: 12500,
      restocking_fee_cents: 0,
      refund_cents: 0,
      exchange_credit_cents: 12500
    }
  ],
  rejected: [
    { sku: 'CARD', qty: 1, reason: 'nonreturnable' }
  ],
  refund_cents: 2250,
  exchange_credit_cents: 12500,
  restocking_fee_cents: 250
});

console.log(JSON.stringify({ ok: true }));
