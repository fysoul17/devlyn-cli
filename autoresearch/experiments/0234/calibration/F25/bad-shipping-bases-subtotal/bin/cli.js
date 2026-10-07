#!/usr/bin/env node
const fs = require('node:fs');
const path = require('node:path');
function error(value) { process.stderr.write(JSON.stringify(value) + '\n'); process.exit(2); }
function cart(input, catalog) {
  if (!Array.isArray(input.items)) throw { error: 'invalid_items' };
  if (!Object.hasOwn(catalog.tax_rates, input.state)) throw { error: 'invalid_state' };
  if (input.coupon != null && !Object.hasOwn(catalog.coupons, input.coupon)) throw { error: 'invalid_coupon' };
  const quantities = new Map();
  for (const item of input.items) {
    if (!item || !Object.hasOwn(catalog.products, item.sku)) throw { error: 'invalid_sku' };
    if (!Number.isInteger(item.qty) || item.qty <= 0) throw { error: 'invalid_qty' };
    quantities.set(item.sku, (quantities.get(item.sku) || 0) + item.qty);
  }
  const items = [];
  let subtotal = 0, lineDiscount = 0, taxable = 0;
  for (const [sku, qty] of quantities) {
    const product = catalog.products[sku];
    if (qty > product.stock) throw { error: 'invalid_stock', sku, available: product.stock, requested: qty };
    const lineSubtotal = product.unit_cents * qty;
    let discount = 0;
    for (const promotion of catalog.line_promotions.filter(p => p.sku === sku)) {
      if (promotion.type === 'buy_x_get_y_free')
        discount += Math.floor(qty / (promotion.buy_qty + promotion.free_qty)) * promotion.free_qty * product.unit_cents;
      if (promotion.type === 'per_unit_discount_cents' && qty >= promotion.min_qty)
        discount += promotion.per_unit_discount_cents * qty;
    }
    const lineTotal = lineSubtotal - discount;
    items.push({ sku, qty, line_subtotal_cents: lineSubtotal, line_discount_cents: discount, line_total_cents: lineTotal });
    subtotal += lineSubtotal; lineDiscount += discount;
    if (catalog.taxable_codes[product.tax_code]) taxable += lineTotal;
  }
  const coupon = input.coupon == null ? null : catalog.coupons[input.coupon];
  const couponDiscount = coupon && subtotal - lineDiscount >= coupon.min_subtotal_cents
    ? Math.round((subtotal - lineDiscount) * coupon.percent / 100) : 0;
  const tax = Math.round(taxable * catalog.tax_rates[input.state]);
  const shipping = subtotal >= catalog.free_shipping_min_cents ? 0 : catalog.shipping_cents;
  return { subtotal_cents: subtotal, line_discount_cents: lineDiscount, coupon_discount_cents: couponDiscount,
    tax_cents: tax, shipping_cents: shipping, total_cents: subtotal - lineDiscount - couponDiscount + tax + shipping, items };
}
function main(args) {
  const [command, ...rest] = args;
  if (command === 'hello') { const i = rest.indexOf('--name'); console.log(`Hello, ${i < 0 ? 'world' : rest[i + 1]}!`); return; }
  if (command === 'version') { console.log(require('../package.json').version); return; }
  if (command !== 'cart') { console.log('Usage: bench-cli cart --input <path>'); return; }
  try {
    if (rest[0] !== '--input' || !rest[1]) throw { error: 'invalid_input' };
    const input = JSON.parse(fs.readFileSync(rest[1], 'utf8'));
    const catalog = JSON.parse(fs.readFileSync(path.join(__dirname, '../data/catalog.json'), 'utf8'));
    console.log(JSON.stringify(cart(input, catalog)));
  } catch (e) { error(e && e.error ? e : { error: 'invalid_input' }); }
}
main(process.argv.slice(2));
