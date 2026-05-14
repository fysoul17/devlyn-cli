'use strict';

const assert = require('node:assert');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const work = process.env.BENCH_WORKDIR || process.cwd();
const cli = path.join(work, 'bin', 'cli.js');

function runPayload(label, payload) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), `f30-${label}-`));
  const input = path.join(tmp, 'holds.json');
  const original = JSON.stringify(payload, null, 2);
  fs.writeFileSync(input, original, 'utf8');
  const result = spawnSync('node', [cli, 'settle-holds', '--input', input], {
    cwd: work,
    encoding: 'utf8'
  });
  assert.strictEqual(fs.readFileSync(input, 'utf8'), original, `${label}: input mutated`);
  return result;
}

const boundary = runPayload('boundary', {
  accounts: [
    { id: 'acct-a', balance_cents: 1000, credit_limit_cents: 7000 }
  ],
  operations: [
    { id: 'op-auth', account_id: 'acct-a', type: 'authorize', hold_id: 'h-1', amount_cents: 3000 },
    { id: 'op-dupe-hold', account_id: 'acct-a', type: 'authorize', hold_id: 'h-1', amount_cents: 1000 },
    { id: 'op-bad-capture', account_id: 'acct-a', type: 'capture', hold_id: 'h-1', amount_cents: 2000 },
    { id: 'op-release', account_id: 'acct-a', type: 'release', hold_id: 'h-1', amount_cents: 3000 },
    { id: 'op-bad-release', account_id: 'acct-a', type: 'release', hold_id: 'h-1', amount_cents: 3000 },
    { id: 'op-after', account_id: 'acct-a', type: 'authorize', hold_id: 'h-2', amount_cents: 6000 },
    { id: 'op-dupe-reject', account_id: 'acct-a', type: 'authorize', hold_id: 'h-3', amount_cents: 1 },
    { id: 'op-dupe-reject', account_id: 'acct-a', type: 'authorize', hold_id: 'h-4', amount_cents: 1 }
  ]
});

assert.strictEqual(boundary.status, 0);
assert.strictEqual(boundary.stderr, '');
assert.deepStrictEqual(JSON.parse(boundary.stdout), {
  results: [
    { id: 'op-auth', status: 'approved', type: 'authorize', account_id: 'acct-a', hold_id: 'h-1', amount_cents: 3000 },
    { id: 'op-dupe-hold', status: 'rejected', reason: 'duplicate_hold' },
    { id: 'op-bad-capture', status: 'rejected', reason: 'amount_mismatch' },
    { id: 'op-release', status: 'approved', type: 'release', account_id: 'acct-a', hold_id: 'h-1', amount_cents: 3000 },
    { id: 'op-bad-release', status: 'rejected', reason: 'unknown_hold' },
    { id: 'op-after', status: 'approved', type: 'authorize', account_id: 'acct-a', hold_id: 'h-2', amount_cents: 6000 },
    { id: 'op-dupe-reject', status: 'rejected', reason: 'insufficient_credit' },
    { id: 'op-dupe-reject', status: 'duplicate', original_status: 'rejected' }
  ],
  accounts: [
    { id: 'acct-a', balance_cents: 1000, active_hold_cents: 6000, available_cents: 0 }
  ]
});

const invalid = runPayload('invalid', {
  accounts: [
    { id: 'acct-a', balance_cents: 0, credit_limit_cents: 1000 }
  ],
  operations: [
    { id: 'op-missing-account', account_id: 'acct-missing', type: 'authorize', hold_id: 'h-1', amount_cents: 100 }
  ]
});

assert.strictEqual(invalid.status, 2);
assert.strictEqual(invalid.stdout, '');
const err = JSON.parse(invalid.stderr);
assert.strictEqual(typeof err.error, 'string');
assert.notStrictEqual(err.error.length, 0);

console.log(JSON.stringify({ ok: true }));
