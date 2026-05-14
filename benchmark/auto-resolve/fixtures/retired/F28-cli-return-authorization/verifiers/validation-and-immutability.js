'use strict';
const assert = require('node:assert');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const work = process.env.BENCH_WORKDIR || process.cwd();
const cli = path.join(work, 'bin', 'cli.js');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'f28-return-validation-'));
const input = path.join(tmp, 'return.json');
const payload = {
  today: '2026-05-20',
  order: {
    id: 'O-101',
    purchased_at: '2026-05-01',
    items: [
      { sku: 'COAT', qty: 1, unit_cents: 9900, return_window_days: 30, restocking_fee_percent: 12 }
    ]
  },
  request: {
    id: 'R-201',
    lines: [
      { sku: 'COAT', qty: 2, reason: 'changed_mind', condition: 'opened', resolution: 'refund' }
    ]
  }
};
const original = JSON.stringify(payload, null, 2);
fs.writeFileSync(input, original, 'utf8');

const result = spawnSync('node', [cli, 'authorize-return', '--input', input], {
  cwd: work,
  encoding: 'utf8'
});

assert.strictEqual(result.status, 2);
assert.strictEqual(result.stdout, '');
const err = JSON.parse(result.stderr);
assert.strictEqual(typeof err.error, 'string');
assert.notStrictEqual(err.error.length, 0);
assert.strictEqual(fs.readFileSync(input, 'utf8'), original);

console.log(JSON.stringify({ ok: true }));
