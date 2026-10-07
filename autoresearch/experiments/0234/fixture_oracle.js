'use strict';
// Independent fixture probes. The caller supplies a fresh writable copy for every row.
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { isDeepStrictEqual: same } = require('node:util');
function assert(ok, message) { if (!ok) throw new Error(message); }
function run(root, command, input) {
  const file = path.join(root, 'probe.json');
  fs.writeFileSync(file, JSON.stringify(input));
  const result = spawnSync(process.execPath, [path.join(root, 'bin/cli.js'), command, '--input', file], { cwd: root, encoding: 'utf8' });
  let value;
  try { value = JSON.parse(result.status === 0 ? result.stdout : result.stderr); }
  catch { throw new Error(`non-JSON ${command}: ${result.stdout} ${result.stderr}`); }
  return { status: result.status, stdout: result.stdout, stderr: result.stderr, value };
}
function success(result, expected) {
  assert(result.status === 0 && result.stderr === '' && same(result.value, expected),
    `success differs: ${JSON.stringify(result)}`);
}
function failure(result, expected) {
  assert(result.status === 2 && result.stdout === '' && same(result.value, expected),
    `failure differs: ${JSON.stringify(result)}`);
}
function remainingMatches(rows, expected, warehouses) {
  if (!Array.isArray(rows)) return false;
  const lots = new Map(warehouses.flatMap(w => w.lots.map(l =>
    [`${w.id}\0${l.sku}\0${l.lot}`, { warehouse: w.id, sku: l.sku, lot: l.lot, expires: l.expires }])));
  const positive = rows.filter(row => row && row.qty > 0);
  const ordered = [...rows].sort((a, b) => a.warehouse.localeCompare(b.warehouse) ||
    a.sku.localeCompare(b.sku) || a.expires.localeCompare(b.expires) || a.lot.localeCompare(b.lot));
  const keys = rows.map(row => `${row.warehouse}\0${row.sku}\0${row.lot}`);
  return same(positive, expected) && same(rows, ordered) && new Set(keys).size === keys.length &&
    rows.every(row => Number.isInteger(row.qty) && row.qty >= 0 &&
      same(Object.keys(row).sort(), ['expires', 'lot', 'qty', 'sku', 'warehouse'])) &&
    rows.every(row => {
      const { qty, ...identity } = row;
      return same(identity, lots.get(`${row.warehouse}\0${row.sku}\0${row.lot}`));
    });
}
function f16(root, row) {
  const input = { state: 'CA', coupon: 'SAVE10', items: [{ sku: 'A', qty: 1 }, { sku: 'B', qty: 3 }, { sku: 'A', qty: 1 }] };
  if (row === 'exact-success') {
    success(run(root, 'quote', input), { subtotal_cents: 4748, discount_cents: 475, tax_cents: 290,
      shipping_cents: 499, total_cents: 5062, items: [{ sku: 'A', qty: 2, line_cents: 3998 }, { sku: 'B', qty: 3, line_cents: 750 }] });
  } else if (row === 'stock-error') {
    failure(run(root, 'quote', { state: 'NY', coupon: null, items: [{ sku: 'A', qty: 2 }, { sku: 'A', qty: 2 }] }),
      { error: 'invalid_stock', sku: 'A', available: 3, requested: 4 });
  } else if (row === 'pricing-source') {
    const file = path.join(root, 'data/pricing.json'), pricing = JSON.parse(fs.readFileSync(file));
    pricing.products.A.unit_cents = 2111; pricing.products.A.stock = 5; pricing.shipping_cents = 123;
    fs.writeFileSync(file, JSON.stringify(pricing));
    success(run(root, 'quote', { state: 'OR', coupon: null, items: [{ sku: 'A', qty: 2 }] }),
      { subtotal_cents: 4222, discount_cents: 0, tax_cents: 0, shipping_cents: 123,
        total_cents: 4345, items: [{ sku: 'A', qty: 2, line_cents: 4222 }] });
  } else if (row === 'shipping-base') {
    success(run(root, 'quote', { state: 'OR', coupon: 'SAVE10', items: [{ sku: 'C', qty: 1 }] }),
      { subtotal_cents: 5000, discount_cents: 500, tax_cents: 0, shipping_cents: 499,
        total_cents: 4999, items: [{ sku: 'C', qty: 1, line_cents: 5000 }] });
  } else if (row === 'coupon-min') {
    success(run(root, 'quote', { state: 'OR', coupon: 'SAVE10', items: [{ sku: 'A', qty: 1 }] }),
      { subtotal_cents: 1999, discount_cents: 0, tax_cents: 0, shipping_cents: 499,
        total_cents: 2498, items: [{ sku: 'A', qty: 1, line_cents: 1999 }] });
  } else throw new Error(`unknown F16 row ${row}`);
}
function f25(root, row) {
  if (row === 'exact-success') {
    success(run(root, 'cart', { state: 'CA', coupon: 'ORDER10', items: [
      { sku: 'TEE', qty: 2 }, { sku: 'BAG', qty: 1 }, { sku: 'TEE', qty: 1 }, { sku: 'MUG', qty: 2 }, { sku: 'BAG', qty: 1 }] }),
    { subtotal_cents: 16300, line_discount_cents: 3500, coupon_discount_cents: 1280, tax_cents: 858,
      shipping_cents: 0, total_cents: 12378, items: [
        { sku: 'TEE', qty: 3, line_subtotal_cents: 7500, line_discount_cents: 2500, line_total_cents: 5000 },
        { sku: 'BAG', qty: 2, line_subtotal_cents: 6400, line_discount_cents: 1000, line_total_cents: 5400 },
        { sku: 'MUG', qty: 2, line_subtotal_cents: 2400, line_discount_cents: 0, line_total_cents: 2400 }] });
  } else if (row === 'stock-error') {
    failure(run(root, 'cart', { state: 'OR', coupon: null, items: [
      { sku: 'BAG', qty: 2 }, { sku: 'MUG', qty: 1 }, { sku: 'BAG', qty: 3 }] }),
      { error: 'invalid_stock', sku: 'BAG', available: 4, requested: 5 });
  } else if (row === 'catalog-source') {
    const file = path.join(root, 'data/catalog.json'), catalog = JSON.parse(fs.readFileSync(file));
    catalog.products.TEE.unit_cents = 3333; catalog.products.TEE.stock = 7; catalog.line_promotions = [];
    catalog.coupons = {}; catalog.tax_rates.OR = 0; catalog.shipping_cents = 777;
    catalog.free_shipping_min_cents = 99999; fs.writeFileSync(file, JSON.stringify(catalog));
    success(run(root, 'cart', { state: 'OR', coupon: null, items: [{ sku: 'TEE', qty: 1 }] }),
      { subtotal_cents: 3333, line_discount_cents: 0, coupon_discount_cents: 0, tax_cents: 0,
        shipping_cents: 777, total_cents: 4110, items: [
          { sku: 'TEE', qty: 1, line_subtotal_cents: 3333, line_discount_cents: 0, line_total_cents: 3333 }] });
  } else if (row === 'shipping-bases') {
    success(run(root, 'cart', { state: 'OR', coupon: 'ORDER10', items: [{ sku: 'MUG', qty: 8 }] }),
      { subtotal_cents: 9600, line_discount_cents: 0, coupon_discount_cents: 960, tax_cents: 0,
        shipping_cents: 699, total_cents: 9339, items: [
          { sku: 'MUG', qty: 8, line_subtotal_cents: 9600, line_discount_cents: 0, line_total_cents: 9600 }] });
    success(run(root, 'cart', { state: 'OR', coupon: null, items: [
      { sku: 'TEE', qty: 3 }, { sku: 'BAG', qty: 1 }] }),
      { subtotal_cents: 10700, line_discount_cents: 2500, coupon_discount_cents: 0, tax_cents: 0,
        shipping_cents: 699, total_cents: 8899, items: [
          { sku: 'TEE', qty: 3, line_subtotal_cents: 7500, line_discount_cents: 2500, line_total_cents: 5000 },
          { sku: 'BAG', qty: 1, line_subtotal_cents: 3200, line_discount_cents: 0, line_total_cents: 3200 }] });
  } else if (row === 'coupon-min') {
    success(run(root, 'cart', { state: 'OR', coupon: 'ORDER10', items: [
      { sku: 'TEE', qty: 3 }, { sku: 'MUG', qty: 1 }] }),
      { subtotal_cents: 8700, line_discount_cents: 2500, coupon_discount_cents: 0, tax_cents: 0,
        shipping_cents: 699, total_cents: 6899, items: [
          { sku: 'TEE', qty: 3, line_subtotal_cents: 7500, line_discount_cents: 2500, line_total_cents: 5000 },
          { sku: 'MUG', qty: 1, line_subtotal_cents: 1200, line_discount_cents: 0, line_total_cents: 1200 }] });
  } else throw new Error(`unknown F25 row ${row}`);
}
function f23(root, row) {
  let input, expected;
  if (row === 'priority-rollback') {
    input = { warehouses: [
      { id: 'near', distance: 1, lots: [{ sku: 'A', lot: 'n-old', qty: 2, expires: '2026-02-01' }, { sku: 'B', lot: 'n-b', qty: 1, expires: '2026-02-01' }] },
      { id: 'far', distance: 9, lots: [{ sku: 'A', lot: 'f-a', qty: 3, expires: '2026-01-15' }] }],
      orders: [
        { id: 'low-first', priority: 1, submitted_at: '2026-01-01T09:00:00Z', lines: [{ sku: 'A', qty: 2, single_warehouse: false }] },
        { id: 'bad-middle', priority: 5, submitted_at: '2026-01-01T09:01:00Z', lines: [{ sku: 'B', qty: 1, single_warehouse: false }, { sku: 'C', qty: 1, single_warehouse: false }] },
        { id: 'high-second', priority: 10, submitted_at: '2026-01-01T09:02:00Z', lines: [{ sku: 'A', qty: 5, single_warehouse: false }] },
        { id: 'after-bad', priority: 4, submitted_at: '2026-01-01T09:03:00Z', lines: [{ sku: 'B', qty: 1, single_warehouse: false }] }] };
    expected = { accepted: [
      { id: 'high-second', allocations: [{ sku: 'A', warehouse: 'near', lot: 'n-old', qty: 2 }, { sku: 'A', warehouse: 'far', lot: 'f-a', qty: 3 }] },
      { id: 'after-bad', allocations: [{ sku: 'B', warehouse: 'near', lot: 'n-b', qty: 1 }] }],
      rejected: [{ id: 'low-first', reason: 'insufficient_stock' }, { id: 'bad-middle', reason: 'insufficient_stock' }], remaining: [] };
  } else if (row === 'single-warehouse-fefo') {
    input = { warehouses: [
      { id: 'east', distance: 2, lots: [{ sku: 'K', lot: 'e-late', qty: 2, expires: '2026-04-01' }, { sku: 'K', lot: 'e-early', qty: 1, expires: '2026-03-01' }] },
      { id: 'west', distance: 1, lots: [{ sku: 'K', lot: 'w-only', qty: 2, expires: '2026-02-01' }, { sku: 'Z', lot: 'w-z', qty: 1, expires: '2026-02-01' }] }],
      orders: [
        { id: 'single-ok', priority: 10, submitted_at: '2026-01-01T09:00:00Z', lines: [{ sku: 'K', qty: 3, single_warehouse: true }] },
        { id: 'single-reject', priority: 9, submitted_at: '2026-01-01T09:01:00Z', lines: [{ sku: 'K', qty: 3, single_warehouse: true }] },
        { id: 'normal-z', priority: 8, submitted_at: '2026-01-01T09:02:00Z', lines: [{ sku: 'Z', qty: 1, single_warehouse: false }] }] };
    expected = { accepted: [
      { id: 'single-ok', allocations: [{ sku: 'K', warehouse: 'east', lot: 'e-early', qty: 1 }, { sku: 'K', warehouse: 'east', lot: 'e-late', qty: 2 }] },
      { id: 'normal-z', allocations: [{ sku: 'Z', warehouse: 'west', lot: 'w-z', qty: 1 }] }],
      rejected: [{ id: 'single-reject', reason: 'insufficient_stock' }],
      remaining: [{ warehouse: 'west', sku: 'K', lot: 'w-only', qty: 2, expires: '2026-02-01' }] };
  } else throw new Error(`unknown F23 row ${row}`);
  const result = run(root, 'fulfill-wave', input);
  assert(result.status === 0 && result.stderr === '' && result.value &&
    same(Object.keys(result.value).sort(), ['accepted', 'rejected', 'remaining']) &&
    same(result.value.accepted, expected.accepted) && same(result.value.rejected, expected.rejected),
    `fulfillment differs: ${JSON.stringify(result)}`);
  if (row !== 'priority-rollback')
    assert(remainingMatches(result.value.remaining, expected.remaining, input.warehouses),
      `remaining differs: ${JSON.stringify(result.value.remaining)}`);
}
module.exports = (task, row, root) => {
  if (task === 'F16') return f16(root, row);
  if (task === 'F23') return f23(root, row);
  if (task === 'F25') return f25(root, row);
  throw new Error(`unknown fixture ${task}`);
};
