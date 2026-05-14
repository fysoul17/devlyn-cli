'use strict';
const assert = require('node:assert');
const { spawnSync } = require('node:child_process');
const path = require('node:path');

const work = process.env.BENCH_WORKDIR || process.cwd();
const cli = path.join(work, 'bin', 'cli.js');

const grants = JSON.stringify([
  { id: 'g-late', account: 'acct-1', cents: 700, expires_on: '2026-03-31' },
  { id: 'g-early-b', account: 'acct-1', cents: 300, expires_on: '2026-01-31' },
  { id: 'g-early-a', account: 'acct-1', cents: 500, expires_on: '2026-01-31' },
  { id: 'g-other', account: 'acct-2', cents: 400, expires_on: '2026-01-31' },
  { id: 'g-expired-unused', account: 'acct-1', cents: 250, expires_on: '2026-01-05' }
]);
const charges = JSON.stringify([
  { id: 'late-low', account: 'acct-1', cents: 500, occurred_on: '2026-01-20', priority: 1 },
  { id: 'early', account: 'acct-1', cents: 450, occurred_on: '2026-01-10', priority: 1 },
  { id: 'same-day-high', account: 'acct-1', cents: 600, occurred_on: '2026-01-20', priority: 9 },
  { id: 'other-account', account: 'acct-2', cents: 350, occurred_on: '2026-01-20', priority: 10 },
  { id: 'after-expiry', account: 'acct-1', cents: 500, occurred_on: '2026-02-02', priority: 10 }
]);

const result = spawnSync('node', [
  cli,
  'settle-credits',
  '--grants',
  grants,
  '--charges',
  charges,
  '--as-of',
  '2026-04-01'
], {
  cwd: work,
  encoding: 'utf8'
});

assert.strictEqual(result.status, 0, result.stderr || result.stdout);
assert.strictEqual(result.stderr, '');
const parsed = JSON.parse(result.stdout);

assert.deepStrictEqual(parsed, {
  settled: [
    {
      id: 'early',
      covered_cents: 450,
      uncovered_cents: 0,
      grants: [
        { id: 'g-early-a', cents: 450 }
      ]
    },
    {
      id: 'other-account',
      covered_cents: 350,
      uncovered_cents: 0,
      grants: [
        { id: 'g-other', cents: 350 }
      ]
    },
    {
      id: 'same-day-high',
      covered_cents: 600,
      uncovered_cents: 0,
      grants: [
        { id: 'g-early-a', cents: 50 },
        { id: 'g-early-b', cents: 300 },
        { id: 'g-late', cents: 250 }
      ]
    },
    {
      id: 'late-low',
      covered_cents: 450,
      uncovered_cents: 50,
      grants: [
        { id: 'g-late', cents: 450 }
      ]
    },
    {
      id: 'after-expiry',
      covered_cents: 0,
      uncovered_cents: 500,
      grants: []
    }
  ],
  balances: [
    { id: 'g-early-a', remaining_cents: 0 },
    { id: 'g-early-b', remaining_cents: 0 },
    { id: 'g-expired-unused', remaining_cents: 250 },
    { id: 'g-late', remaining_cents: 0 },
    { id: 'g-other', remaining_cents: 50 }
  ],
  expired: [
    { id: 'g-expired-unused', remaining_cents: 250 },
    { id: 'g-other', remaining_cents: 50 }
  ]
});

console.log(JSON.stringify({ ok: true }));
