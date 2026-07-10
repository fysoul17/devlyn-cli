const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const workdir = process.env.BENCH_WORKDIR || process.cwd();
const catalogPath = path.join(workdir, 'data', 'catalog.json');
const original = fs.readFileSync(catalogPath, 'utf8');

try {
  const catalog = JSON.parse(original);
  catalog.products.TEE.unit_cents = 3333;
  catalog.products.TEE.stock = 7;
  catalog.tax_rates.OR = 0;
  catalog.line_promotions = [];
  catalog.coupons = {};
  catalog.shipping_cents = 777;
  catalog.free_shipping_min_cents = 99999;
  fs.writeFileSync(catalogPath, JSON.stringify(catalog, null, 2) + '\n');

  const input = path.join(os.tmpdir(), `cart-source-${process.pid}.json`);
  fs.writeFileSync(input, JSON.stringify({
    state: 'OR',
    coupon: null,
    items: [{ sku: 'TEE', qty: 1 }]
  }));

  const proc = spawnSync('node', ['bin/cli.js', 'cart', '--input', input], {
    cwd: workdir,
    encoding: 'utf8'
  });

  assert.strictEqual(proc.status, 0, proc.stderr || proc.stdout);
  assert.strictEqual(proc.stderr, '');
  assert.deepStrictEqual(JSON.parse(proc.stdout), {
    subtotal_cents: 3333,
    line_discount_cents: 0,
    coupon_discount_cents: 0,
    tax_cents: 0,
    shipping_cents: 777,
    total_cents: 4110,
    items: [
      {
        sku: 'TEE',
        qty: 1,
        line_subtotal_cents: 3333,
        line_discount_cents: 0,
        line_total_cents: 3333
      }
    ]
  });
} finally {
  fs.writeFileSync(catalogPath, original);
}

process.stdout.write(JSON.stringify({ ok: true }) + '\n');
