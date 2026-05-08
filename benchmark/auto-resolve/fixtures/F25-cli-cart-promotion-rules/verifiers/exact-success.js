const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const workdir = process.env.BENCH_WORKDIR || process.cwd();
const input = path.join(os.tmpdir(), `cart-success-${process.pid}.json`);

fs.writeFileSync(input, JSON.stringify({
  state: 'CA',
  coupon: 'ORDER10',
  items: [
    { sku: 'TEE', qty: 2 },
    { sku: 'BAG', qty: 1 },
    { sku: 'TEE', qty: 1 },
    { sku: 'MUG', qty: 2 },
    { sku: 'BAG', qty: 1 }
  ]
}));

const proc = spawnSync('node', ['bin/cli.js', 'cart', '--input', input], {
  cwd: workdir,
  encoding: 'utf8'
});

assert.strictEqual(proc.status, 0, proc.stderr || proc.stdout);
assert.strictEqual(proc.stderr, '');

const actual = JSON.parse(proc.stdout);
assert.deepStrictEqual(actual, {
  subtotal_cents: 16300,
  line_discount_cents: 3500,
  coupon_discount_cents: 1280,
  tax_cents: 858,
  shipping_cents: 0,
  total_cents: 12378,
  items: [
    {
      sku: 'TEE',
      qty: 3,
      line_subtotal_cents: 7500,
      line_discount_cents: 2500,
      line_total_cents: 5000
    },
    {
      sku: 'BAG',
      qty: 2,
      line_subtotal_cents: 6400,
      line_discount_cents: 1000,
      line_total_cents: 5400
    },
    {
      sku: 'MUG',
      qty: 2,
      line_subtotal_cents: 2400,
      line_discount_cents: 0,
      line_total_cents: 2400
    }
  ]
});

process.stdout.write(JSON.stringify({ ok: true }) + '\n');
