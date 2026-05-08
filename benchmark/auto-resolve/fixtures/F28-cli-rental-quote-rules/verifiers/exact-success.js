const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const workdir = process.env.BENCH_WORKDIR || process.cwd();
const input = path.join(os.tmpdir(), `rental-success-${process.pid}.json`);

fs.writeFileSync(input, JSON.stringify({
  start_date: '2026-05-08',
  end_date: '2026-05-12',
  coupon: 'LONG3',
  protection: true,
  items: [
    { sku: 'CAM', qty: 1 },
    { sku: 'LIGHT', qty: 1 },
    { sku: 'CAM', qty: 1 }
  ]
}));

const proc = spawnSync('node', ['bin/cli.js', 'rental-quote', '--input', input], {
  cwd: workdir,
  encoding: 'utf8'
});

assert.strictEqual(proc.status, 0, proc.stderr || proc.stdout);
assert.strictEqual(proc.stderr, '');
assert.deepStrictEqual(JSON.parse(proc.stdout), {
  rental_days: 4,
  weekend_days: 2,
  subtotal_cents: 12400,
  weekend_surcharge_cents: 1550,
  discount_cents: 1395,
  protection_cents: 3600,
  deposit_cents: 12000,
  total_cents: 28155,
  items: [
    { sku: 'CAM', qty: 2, rental_cents: 9600, deposit_cents: 10000 },
    { sku: 'LIGHT', qty: 1, rental_cents: 2800, deposit_cents: 2000 }
  ]
});

process.stdout.write(JSON.stringify({ ok: true }) + '\n');
