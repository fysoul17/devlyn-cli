#!/usr/bin/env node
const assert = require('node:assert/strict');
const { mkdtempSync, writeFileSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join } = require('node:path');
const { spawnSync } = require('node:child_process');

const workdir = process.env.BENCH_WORKDIR || process.cwd();
const tmp = mkdtempSync(join(tmpdir(), 'f32-renewal-dup-'));

try {
  const inputPath = join(tmp, 'input.json');
  writeFileSync(inputPath, JSON.stringify({
    as_of: '2026-05-15',
    plans: [
      { id: 'starter', monthly_cents: 1000, included_seats: 5, overage_cents: 200 }
    ],
    customers: [
      { id: 'c1', plan: 'starter', active: true }
    ],
    credits: [],
    renewals: [
      { id: 'dup-renewal', customer: 'c1', seats: 5, months: 1, priority: 1, requested_at: '2026-05-01', max_due_cents: 1000 },
      { id: 'dup-renewal', customer: 'missing', seats: 5, months: 1, priority: 9, requested_at: '2026-05-02', max_due_cents: 1000 }
    ]
  }));

  const proc = spawnSync('node', ['bin/cli.js', 'renew-subscriptions', '--input', inputPath], {
    cwd: workdir,
    encoding: 'utf8'
  });

  assert.equal(proc.status, 2, proc.stderr || proc.stdout);
  assert.equal(proc.stdout, '');
  assert.deepEqual(JSON.parse(proc.stderr), {
    error: 'duplicate_renewal_id',
    id: 'dup-renewal'
  });
  process.stdout.write(JSON.stringify({ ok: true }) + '\n');
} finally {
  rmSync(tmp, { recursive: true, force: true });
}
