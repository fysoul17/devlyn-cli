'use strict';
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const workdir = process.env.BENCH_WORKDIR || process.cwd();
const rulesPath = path.join(workdir, 'data', 'subscription-plans.json');
const originalRules = fs.readFileSync(rulesPath, 'utf8');
let inputCounter = 0;

function runInvoice(inputBody) {
  inputCounter += 1;
  const input = path.join(os.tmpdir(), `subscription-rules-${process.pid}-${inputCounter}.json`);
  fs.writeFileSync(input, JSON.stringify(inputBody), 'utf8');
  return spawnSync('node', ['bin/cli.js', 'subscription-invoice', '--input', input], {
    cwd: workdir,
    encoding: 'utf8'
  });
}

try {
  fs.writeFileSync(rulesPath, JSON.stringify({
    plans: {
      starter: { monthly_cents: 3100 },
      growth: { monthly_cents: 6200 }
    },
    tax_rates: {
      CA: 0.1
    }
  }, null, 2) + '\n');

  const sourceProc = runInvoice({
    customer_id: 'cus_source',
    state: 'CA',
    period: { start: '2026-02-01', end: '2026-03-01' },
    changes: [
      { date: '2026-02-01', plan: 'starter' },
      { date: '2026-02-15', plan: 'growth' }
    ],
    credits: []
  });
  assert.strictEqual(sourceProc.status, 0, sourceProc.stderr || sourceProc.stdout);
  assert.strictEqual(sourceProc.stderr, '');
  assert.deepStrictEqual(JSON.parse(sourceProc.stdout), {
    customer_id: 'cus_source',
    period_days: 28,
    subtotal_cents: 4650,
    credit_cents: 0,
    tax_cents: 465,
    total_cents: 5115,
    segments: [
      { plan: 'starter', start: '2026-02-01', end: '2026-02-15', days: 14, amount_cents: 1550 },
      { plan: 'growth', start: '2026-02-15', end: '2026-03-01', days: 14, amount_cents: 3100 }
    ]
  });

  const conflictProc = runInvoice({
    customer_id: 'cus_conflict',
    state: 'CA',
    period: { start: '2026-02-01', end: '2026-03-01' },
    changes: [{ date: '2026-02-01', plan: 'starter' }],
    credits: [
      { id: 'credit-conflict', amount_cents: 100 },
      { id: 'credit-conflict', amount_cents: 101 }
    ]
  });
  assert.strictEqual(conflictProc.status, 2);
  assert.strictEqual(conflictProc.stdout, '');
  assert.deepStrictEqual(JSON.parse(conflictProc.stderr), {
    error: 'conflicting_credit',
    id: 'credit-conflict'
  });
} finally {
  fs.writeFileSync(rulesPath, originalRules);
}

process.stdout.write(JSON.stringify({ ok: true }) + '\n');
