'use strict';
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const workdir = process.env.BENCH_WORKDIR || process.cwd();
const input = path.join(os.tmpdir(), `subscription-proration-${process.pid}.json`);

fs.writeFileSync(input, JSON.stringify({
  customer_id: 'cus_27',
  state: 'CA',
  period: { start: '2026-03-01', end: '2026-04-01' },
  changes: [
    { date: '2026-03-01', plan: 'starter' },
    { date: '2026-03-11', plan: 'growth' },
    { date: '2026-03-21', plan: 'scale' }
  ],
  credits: [
    { id: 'credit-a', amount_cents: 500 },
    { id: 'credit-a', amount_cents: 500 },
    { id: 'credit-b', amount_cents: 700 }
  ]
}), 'utf8');

const proc = spawnSync('node', ['bin/cli.js', 'subscription-invoice', '--input', input], {
  cwd: workdir,
  encoding: 'utf8'
});

assert.strictEqual(proc.status, 0, proc.stderr || proc.stdout);
assert.strictEqual(proc.stderr, '');
assert.deepStrictEqual(JSON.parse(proc.stdout), {
  customer_id: 'cus_27',
  period_days: 31,
  subtotal_cents: 4954,
  credit_cents: 1200,
  tax_cents: 310,
  total_cents: 4064,
  segments: [
    { plan: 'starter', start: '2026-03-01', end: '2026-03-11', days: 10, amount_cents: 387 },
    { plan: 'growth', start: '2026-03-11', end: '2026-03-21', days: 10, amount_cents: 1161 },
    { plan: 'scale', start: '2026-03-21', end: '2026-04-01', days: 11, amount_cents: 3406 }
  ]
});

process.stdout.write(JSON.stringify({ ok: true }) + '\n');
