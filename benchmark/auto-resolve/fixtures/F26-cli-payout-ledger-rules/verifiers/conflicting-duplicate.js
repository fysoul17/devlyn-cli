const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const workdir = process.env.BENCH_WORKDIR || process.cwd();
const input = path.join(os.tmpdir(), `payout-conflict-${process.pid}.json`);

fs.writeFileSync(input, JSON.stringify({
  events: [
    { id: 'evt-conflict', merchant_id: 'm_1', type: 'charge', amount_cents: 1000 },
    { id: 'evt-conflict', merchant_id: 'm_1', type: 'charge', amount_cents: 1001 }
  ]
}));

const proc = spawnSync('node', ['bin/cli.js', 'payout', '--input', input], {
  cwd: workdir,
  encoding: 'utf8'
});

assert.strictEqual(proc.status, 2);
assert.strictEqual(proc.stdout, '');
assert.deepStrictEqual(JSON.parse(proc.stderr), {
  error: 'conflicting_duplicate',
  id: 'evt-conflict'
});

process.stdout.write(JSON.stringify({ ok: true }) + '\n');
