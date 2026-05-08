'use strict';
const assert = require('node:assert');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const work = process.env.BENCH_WORKDIR || process.cwd();
const cli = path.join(work, 'bin', 'cli.js');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'f22-ledger-'));
const input = path.join(tmp, 'ledger.json');

const tx = { id: 't-dup', account: 'cash', currency: 'USD', kind: 'debit', amount_cents: 1200, occurred_at: '2026-01-03T00:00:00Z' };
fs.writeFileSync(input, JSON.stringify({
  accounts: [
    { id: 'cash', currency: 'USD', opening_cents: 1000 },
    { id: 'receivable', currency: 'USD', opening_cents: 200 }
  ],
  transactions: [
    { id: 't-late', account: 'receivable', currency: 'USD', kind: 'credit', amount_cents: 50, occurred_at: '2026-01-05T00:00:00Z' },
    tx,
    { ...tx },
    { id: 't-early', account: 'cash', currency: 'USD', kind: 'credit', amount_cents: 300, occurred_at: '2026-01-01T00:00:00Z' }
  ]
}), 'utf8');

const stdout = execFileSync('node', [cli, 'ledger-close', '--input', input], {
  cwd: work,
  encoding: 'utf8',
  stdio: ['ignore', 'pipe', 'pipe']
});
const parsed = JSON.parse(stdout);
assert.deepStrictEqual(parsed, {
  accounts: [
    { id: 'cash', currency: 'USD', closing_cents: 100 },
    { id: 'receivable', currency: 'USD', closing_cents: 250 }
  ],
  applied_count: 3,
  duplicates_ignored: 1
});
console.log(JSON.stringify({ ok: true }));
