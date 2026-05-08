const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const workdir = process.env.BENCH_WORKDIR || process.cwd();
const rulesPath = path.join(workdir, 'data', 'rental-rules.json');
const original = fs.readFileSync(rulesPath, 'utf8');

try {
  fs.writeFileSync(rulesPath, JSON.stringify({
    items: {
      CAM: { daily_cents: 1000, stock: 3, deposit_cents: 3000 }
    },
    weekend_surcharge_percent: 50,
    protection_daily_cents: 100,
    coupons: {
      HALF: { percent: 50, min_rental_days: 1 }
    }
  }, null, 2) + '\n');

  const input = path.join(os.tmpdir(), `rental-source-${process.pid}.json`);
  fs.writeFileSync(input, JSON.stringify({
    start_date: '2026-05-09',
    end_date: '2026-05-11',
    coupon: 'HALF',
    protection: true,
    items: [
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
    rental_days: 2,
    weekend_days: 2,
    subtotal_cents: 2000,
    weekend_surcharge_cents: 1000,
    discount_cents: 1500,
    protection_cents: 200,
    deposit_cents: 3000,
    total_cents: 4700,
    items: [
      { sku: 'CAM', qty: 1, rental_cents: 2000, deposit_cents: 3000 }
    ]
  });
} finally {
  fs.writeFileSync(rulesPath, original);
}

process.stdout.write(JSON.stringify({ ok: true }) + '\n');
