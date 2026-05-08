'use strict';
const assert = require('node:assert');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const work = process.env.BENCH_WORKDIR || process.cwd();
const cli = path.join(work, 'bin', 'cli.js');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'f22-conflict-'));
const input = path.join(tmp, 'ledger.json');

fs.writeFileSync(input, JSON.stringify({
  accounts: [
    { id: 'cash', currency: 'USD', opening_cents: 1000 }
  ],
  transactions: [
    { id: 'same-id', account: 'cash', currency: 'USD', kind: 'credit', amount_cents: 100, occurred_at: '2026-01-01T00:00:00Z' },
    { id: 'same-id', account: 'cash', currency: 'USD', kind: 'credit', amount_cents: 101, occurred_at: '2026-01-01T00:00:00Z' }
  ]
}), 'utf8');

const proc = spawnSync('node', [cli, 'ledger-close', '--input', input], {
  cwd: work,
  encoding: 'utf8'
});
assert.strictEqual(proc.status, 2);
assert.strictEqual(proc.stdout, '');
const parsed = JSON.parse(proc.stderr);
assert.deepStrictEqual(parsed, {
  error: 'conflicting_duplicate',
  id: 'same-id'
});
console.log(JSON.stringify({ ok: true }));
