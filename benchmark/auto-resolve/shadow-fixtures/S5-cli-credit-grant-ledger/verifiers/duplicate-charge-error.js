'use strict';
const assert = require('node:assert');
const { spawnSync } = require('node:child_process');
const path = require('node:path');

const work = process.env.BENCH_WORKDIR || process.cwd();
const cli = path.join(work, 'bin', 'cli.js');

const grants = JSON.stringify([
  { id: 'g1', account: 'acct-1', cents: 100, expires_on: '2026-01-31' }
]);
const charges = JSON.stringify([
  { id: 'dup', account: 'acct-1', cents: 50, occurred_on: '2026-01-10', priority: 1 },
  { id: 'dup', account: 'acct-1', cents: 50, occurred_on: '2026-01-11', priority: 2 }
]);

const result = spawnSync('node', [
  cli,
  'settle-credits',
  '--grants',
  grants,
  '--charges',
  charges,
  '--as-of',
  '2026-02-01'
], {
  cwd: work,
  encoding: 'utf8'
});

assert.strictEqual(result.status, 2);
assert.strictEqual(result.stdout, '');
assert.deepStrictEqual(JSON.parse(result.stderr), {
  error: 'duplicate_charge_id',
  id: 'dup'
});

console.log(JSON.stringify({ ok: true }));
