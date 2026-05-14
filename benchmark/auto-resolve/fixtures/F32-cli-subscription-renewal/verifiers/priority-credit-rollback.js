#!/usr/bin/env node
const assert = require('node:assert/strict');
const { mkdtempSync, writeFileSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join } = require('node:path');
const { spawnSync } = require('node:child_process');

const workdir = process.env.BENCH_WORKDIR || process.cwd();
const tmp = mkdtempSync(join(tmpdir(), 'f32-renewal-'));

try {
  const inputPath = join(tmp, 'input.json');
  writeFileSync(inputPath, JSON.stringify({
    as_of: '2026-05-15',
    plans: [
      { id: 'starter', monthly_cents: 1000, included_seats: 5, overage_cents: 200 },
      { id: 'pro', monthly_cents: 3000, included_seats: 10, overage_cents: 150 }
    ],
    customers: [
      { id: 'c1', plan: 'starter', active: true },
      { id: 'c2', plan: 'pro', active: true }
    ],
    credits: [
      { id: 'cr-late', customer: 'c1', cents: 500, expires_at: '2026-06-30' },
      { id: 'cr-expired', customer: 'c1', cents: 999, expires_at: '2026-04-01' },
      { id: 'cr-early', customer: 'c1', cents: 400, expires_at: '2026-05-31' },
      { id: 'cr-zero', customer: 'c1', cents: 0, expires_at: '2026-05-20' },
      { id: 'cr-c2', customer: 'c2', cents: 1000, expires_at: '2026-12-31' }
    ],
    renewals: [
      { id: 'r-low', customer: 'c1', seats: 5, months: 1, priority: 1, requested_at: '2026-05-01', max_due_cents: 100 },
      { id: 'r-mid', customer: 'c1', seats: 8, months: 1, priority: 10, requested_at: '2026-05-02', max_due_cents: 0 },
      { id: 'r-high', customer: 'c1', seats: 8, months: 1, priority: 9, requested_at: '2026-05-03', max_due_cents: 800 }
    ]
  }));

  const proc = spawnSync('node', ['bin/cli.js', 'renew-subscriptions', '--input', inputPath], {
    cwd: workdir,
    encoding: 'utf8'
  });

  assert.equal(proc.status, 0, proc.stderr || proc.stdout);
  assert.equal(proc.stderr, '');
  const output = JSON.parse(proc.stdout);
  assert.deepEqual(output, {
    invoices: [
      {
        id: 'r-high',
        customer: 'c1',
        subtotal_cents: 1600,
        credit_applied_cents: 900,
        due_cents: 700,
        credits: [
          { id: 'cr-early', applied_cents: 400 },
          { id: 'cr-late', applied_cents: 500 }
        ]
      }
    ],
    rejected: [
      { id: 'r-low', reason: 'payment_required' },
      { id: 'r-mid', reason: 'payment_required' }
    ],
    remaining_credits: [
      { id: 'cr-c2', customer: 'c2', cents: 1000, expires_at: '2026-12-31' }
    ]
  });
  process.stdout.write(JSON.stringify({ ok: true }) + '\n');
} finally {
  rmSync(tmp, { recursive: true, force: true });
}
