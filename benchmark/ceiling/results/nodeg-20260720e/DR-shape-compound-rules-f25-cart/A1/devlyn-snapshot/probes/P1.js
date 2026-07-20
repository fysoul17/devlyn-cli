#!/usr/bin/env node
'use strict';
// Compound success-path shape_contract probe for the bench-cli `cart` command.
// Exercises: duplicate SKU combining (TEE split across two rows), both line
// promotion types (buy_x_get_y_free on TEE, per_unit_discount_cents on BAG),
// taxable vs exempt tax codes (TEE/BAG standard, MUG exempt), a triggered
// coupon (ORDER10), and shipping math — asserted via full parsed-JSON deep
// equality against data/catalog.json-derived expected values.
const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const repoRoot = path.resolve(__dirname, '..', '..');
const inputPath = path.join(__dirname, 'tmp-p1-input.json');

const input = {
  state: 'CA',
  coupon: 'ORDER10',
  items: [
    { sku: 'TEE', qty: 2 },
    { sku: 'MUG', qty: 1 },
    { sku: 'TEE', qty: 1 },
    { sku: 'BAG', qty: 2 }
  ]
};
fs.writeFileSync(inputPath, JSON.stringify(input));

const result = spawnSync('node', ['bin/cli.js', 'cart', '--input', inputPath], {
  cwd: repoRoot,
  encoding: 'utf8'
});

// Expected math (from data/catalog.json):
// TEE combined qty=3, unit_cents=2500: buy_x_get_y_free(buy=2,free=1) ->
//   discount = floor(3/3)*1*2500 = 2500; line_subtotal=7500; line_total=5000
// MUG combined qty=1, unit_cents=1200, no promotion -> line_subtotal=line_total=1200
// BAG combined qty=2, unit_cents=3200: per_unit_discount_cents(min_qty=2,500) ->
//   discount = 500*2=1000; line_subtotal=6400; line_total=5400
// subtotal_cents = 7500+1200+6400 = 15100
// line_discount_cents = 2500+0+1000 = 3500
// taxable_post_line_discount_cents (standard only: TEE+BAG) = 5000+5400 = 10400
// tax_cents = round(10400*0.0825) = 858
// post-line-discount subtotal = 15100-3500 = 11600 >= ORDER10.min_subtotal_cents(8000)
// coupon_discount_cents = round(11600*10/100) = 1160
// post-coupon amount = 11600-1160 = 10440 >= free_shipping_min_cents(9000) -> shipping_cents=0
// total_cents = 15100-3500-1160+858+0 = 11298
const expected = {
  subtotal_cents: 15100,
  line_discount_cents: 3500,
  coupon_discount_cents: 1160,
  tax_cents: 858,
  shipping_cents: 0,
  total_cents: 11298,
  items: [
    { sku: 'TEE', qty: 3, line_subtotal_cents: 7500, line_discount_cents: 2500, line_total_cents: 5000 },
    { sku: 'MUG', qty: 1, line_subtotal_cents: 1200, line_discount_cents: 0, line_total_cents: 1200 },
    { sku: 'BAG', qty: 2, line_subtotal_cents: 6400, line_discount_cents: 1000, line_total_cents: 5400 }
  ]
};
const expectedTopKeys = ['subtotal_cents', 'line_discount_cents', 'coupon_discount_cents', 'tax_cents', 'shipping_cents', 'total_cents', 'items'].sort();
const expectedItemKeys = ['sku', 'qty', 'line_subtotal_cents', 'line_discount_cents', 'line_total_cents'].sort();

try {
  assert.strictEqual(result.status, 0, `expected exit 0, got ${result.status}`);
  assert.strictEqual(result.stderr, '', `expected empty stderr, got: ${JSON.stringify(result.stderr)}`);
  const parsed = JSON.parse(result.stdout);
  assert.deepStrictEqual(Object.keys(parsed).sort(), expectedTopKeys, 'top-level key set mismatch (no unexpected/missing/aliased keys)');
  for (const row of parsed.items) {
    assert.deepStrictEqual(Object.keys(row).sort(), expectedItemKeys, 'item row key set mismatch');
  }
  assert.deepStrictEqual(parsed, expected, 'full output object deep-equality mismatch');
  console.log('P1 PASS');
  process.exit(0);
} catch (err) {
  console.error('P1 FAIL:', err.message);
  console.error('raw status:', result.status);
  console.error('raw stdout:', JSON.stringify(result.stdout));
  console.error('raw stderr:', JSON.stringify(result.stderr));
  process.exit(1);
}
