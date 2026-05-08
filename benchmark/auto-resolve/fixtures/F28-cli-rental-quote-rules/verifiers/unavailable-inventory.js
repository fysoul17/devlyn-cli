const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const workdir = process.env.BENCH_WORKDIR || process.cwd();
const input = path.join(os.tmpdir(), `rental-stock-${process.pid}.json`);

fs.writeFileSync(input, JSON.stringify({
  start_date: '2026-05-08',
  end_date: '2026-05-10',
  coupon: null,
  protection: false,
  items: [
    { sku: 'CAM', qty: 1 },
    { sku: 'CAM', qty: 2 }
  ]
}));

const proc = spawnSync('node', ['bin/cli.js', 'rental-quote', '--input', input], {
  cwd: workdir,
  encoding: 'utf8'
});

assert.strictEqual(proc.status, 2);
assert.strictEqual(proc.stdout, '');
assert.deepStrictEqual(JSON.parse(proc.stderr), {
  error: 'unavailable_inventory',
  sku: 'CAM',
  available: 2,
  requested: 3
});

process.stdout.write(JSON.stringify({ ok: true }) + '\n');
