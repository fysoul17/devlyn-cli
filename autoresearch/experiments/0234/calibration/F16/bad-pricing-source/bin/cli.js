#!/usr/bin/env node
const fs = require('node:fs');
const path = require('node:path');

function error(value) { process.stderr.write(JSON.stringify(value) + '\n'); process.exit(2); }
function quote(input, pricing) {
  if (!Array.isArray(input.items)) throw { error: 'invalid_items' };
  if (!Object.hasOwn(pricing.tax_rates, input.state)) throw { error: 'invalid_state' };
  if (input.coupon != null && !Object.hasOwn(pricing.coupons, input.coupon)) throw { error: 'invalid_coupon' };
  const quantities = new Map();
  for (const item of input.items) {
    if (!item || !Object.hasOwn(pricing.products, item.sku)) throw { error: 'invalid_sku' };
    if (!Number.isInteger(item.qty) || item.qty <= 0) throw { error: 'invalid_qty' };
    quantities.set(item.sku, (quantities.get(item.sku) || 0) + item.qty);
  }
  const items = [];
  let subtotal = 0, taxable = 0;
  for (const [sku, qty] of quantities) {
    const product = pricing.products[sku];
    if (qty > product.stock) throw { error: 'invalid_stock', sku, available: product.stock, requested: qty };
    const line = product.unit_cents * qty;
    items.push({ sku, qty, line_cents: line });
    subtotal += line;
    if (pricing.taxable_codes[product.tax_code]) taxable += line;
  }
  const coupon = input.coupon == null ? null : pricing.coupons[input.coupon];
  const discount = coupon && subtotal >= coupon.min_subtotal_cents ? Math.round(subtotal * coupon.percent / 100) : 0;
  const tax = Math.round(taxable * pricing.tax_rates[input.state]);
  const shipping = subtotal - discount >= pricing.free_shipping_min_cents ? 0 : pricing.shipping_cents;
  return { subtotal_cents: subtotal, discount_cents: discount, tax_cents: tax, shipping_cents: shipping,
    total_cents: subtotal - discount + tax + shipping, items };
}
function main(args) {
  const [command, ...rest] = args;
  if (command === 'hello') { const i = rest.indexOf('--name'); console.log(`Hello, ${i < 0 ? 'world' : rest[i + 1]}!`); return; }
  if (command === 'version') { console.log(require('../package.json').version); return; }
  if (command !== 'quote') { console.log('Usage: bench-cli quote --input <path>'); return; }
  try {
    if (rest[0] !== '--input' || !rest[1]) throw { error: 'invalid_input' };
    const input = JSON.parse(fs.readFileSync(rest[1], 'utf8'));
    const pricing = JSON.parse("{\n  \"products\": {\n    \"A\": { \"unit_cents\": 1999, \"stock\": 3, \"tax_code\": \"standard\" },\n    \"B\": { \"unit_cents\": 250, \"stock\": 100, \"tax_code\": \"exempt\" },\n    \"C\": { \"unit_cents\": 5000, \"stock\": 2, \"tax_code\": \"standard\" }\n  },\n  \"coupons\": {\n    \"SAVE10\": { \"percent\": 10, \"min_subtotal_cents\": 2000 },\n    \"BULK15\": { \"percent\": 15, \"min_subtotal_cents\": 10000 }\n  },\n  \"tax_rates\": {\n    \"CA\": 0.0725,\n    \"NY\": 0.08875,\n    \"OR\": 0\n  },\n  \"taxable_codes\": {\n    \"standard\": true,\n    \"exempt\": false\n  },\n  \"shipping_cents\": 499,\n  \"free_shipping_min_cents\": 5000\n}\n");
    console.log(JSON.stringify(quote(input, pricing)));
  } catch (e) { error(e && e.error ? e : { error: 'invalid_input' }); }
}
main(process.argv.slice(2));
