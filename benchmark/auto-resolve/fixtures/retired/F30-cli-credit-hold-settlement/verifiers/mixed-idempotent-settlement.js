'use strict';

const assert = require('node:assert');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const work = process.env.BENCH_WORKDIR || process.cwd();
const cli = path.join(work, 'bin', 'cli.js');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'f30-mixed-'));
const input = path.join(tmp, 'holds.json');

fs.writeFileSync(input, JSON.stringify({
  accounts: [
    { id: 'acct-a', balance_cents: 2000, credit_limit_cents: 10000 },
    { id: 'acct-b', balance_cents: 0, credit_limit_cents: 5000 }
  ],
  operations: [
    { id: 'op-auth-1', account_id: 'acct-a', type: 'authorize', hold_id: 'h-1', amount_cents: 5000 },
    { id: 'op-too-large', account_id: 'acct-a', type: 'authorize', hold_id: 'h-2', amount_cents: 4000 },
    { id: 'op-release', account_id: 'acct-a', type: 'release', hold_id: 'h-1', amount_cents: 5000 },
    { id: 'op-auth-3', account_id: 'acct-a', type: 'authorize', hold_id: 'h-3', amount_cents: 3000 },
    { id: 'op-capture', account_id: 'acct-a', type: 'capture', hold_id: 'h-3', amount_cents: 3000 },
    { id: 'op-capture', account_id: 'acct-a', type: 'capture', hold_id: 'h-3', amount_cents: 3000 },
    { id: 'op-auth-b', account_id: 'acct-b', type: 'authorize', hold_id: 'h-b', amount_cents: 5000 }
  ]
}), 'utf8');

const stdout = execFileSync('node', [cli, 'settle-holds', '--input', input], {
  cwd: work,
  encoding: 'utf8',
  stdio: ['ignore', 'pipe', 'pipe']
});
const parsed = JSON.parse(stdout);

assert.deepStrictEqual(parsed, {
  results: [
    { id: 'op-auth-1', status: 'approved', type: 'authorize', account_id: 'acct-a', hold_id: 'h-1', amount_cents: 5000 },
    { id: 'op-too-large', status: 'rejected', reason: 'insufficient_credit' },
    { id: 'op-release', status: 'approved', type: 'release', account_id: 'acct-a', hold_id: 'h-1', amount_cents: 5000 },
    { id: 'op-auth-3', status: 'approved', type: 'authorize', account_id: 'acct-a', hold_id: 'h-3', amount_cents: 3000 },
    { id: 'op-capture', status: 'approved', type: 'capture', account_id: 'acct-a', hold_id: 'h-3', amount_cents: 3000 },
    { id: 'op-capture', status: 'duplicate', original_status: 'approved' },
    { id: 'op-auth-b', status: 'approved', type: 'authorize', account_id: 'acct-b', hold_id: 'h-b', amount_cents: 5000 }
  ],
  accounts: [
    { id: 'acct-a', balance_cents: 5000, active_hold_cents: 0, available_cents: 5000 },
    { id: 'acct-b', balance_cents: 0, active_hold_cents: 5000, available_cents: 0 }
  ]
});

console.log(JSON.stringify({ ok: true }));
