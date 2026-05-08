const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const workdir = process.env.BENCH_WORKDIR || process.cwd();
const input = path.join(os.tmpdir(), `gift-card-balance-${process.pid}.json`);

fs.writeFileSync(input, JSON.stringify({
  order_id: 'order-balance',
  lines: [
    { sku: 'TEE', qty: 3 },
    { sku: 'BAG', qty: 1 }
  ],
  redeems: [
    { card_id: 'GC-100', amount_cents: 3000 },
    { card_id: 'GC-100', amount_cents: 2500 }
  ]
}));

const proc = spawnSync('node', ['bin/cli.js', 'gift-card', '--input', input], {
  cwd: workdir,
  encoding: 'utf8'
});

assert.strictEqual(proc.status, 2);
assert.strictEqual(proc.stdout, '');
assert.deepStrictEqual(JSON.parse(proc.stderr), {
  error: 'insufficient_balance',
  card_id: 'GC-100',
  available_cents: 5000,
  requested_cents: 5500
});

process.stdout.write(JSON.stringify({ ok: true }) + '\n');
