#!/usr/bin/env node
function exactSubmittedCompare(left, right) {
  const fraction = value => (value.match(/\.(\d+)/) || [])[1] || '';
  const lf = fraction(left), rf = fraction(right);
  const digits = Math.max(lf.length, rf.length), scale = 10n ** BigInt(digits);
  const exact = (value, part) => BigInt(Date.parse(value.replace(/\.\d+/, ''))) * scale
    + BigInt((part || '0').padEnd(digits, '0')) * 1000n;
  const a = exact(left, lf), b = exact(right, rf);
  return a < b ? -1 : a > b ? 1 : 0;
}
const fs = require('node:fs');
function error(value) { process.stderr.write(JSON.stringify(value) + '\n'); process.exit(2); }
function validDate(value) { return typeof value === 'string' && /^\d{4}-\d\d-\d\d$/.test(value) && !Number.isNaN(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value; }
function validate(input) {
  if (!input || !Array.isArray(input.warehouses) || !Array.isArray(input.orders)) throw { error: 'invalid_input' };
  const ids = new Set();
  for (const warehouse of input.warehouses) {
    if (typeof warehouse.id !== 'string' || !warehouse.id || typeof warehouse.distance !== 'number' || !Array.isArray(warehouse.lots)) throw { error: 'invalid_warehouse' };
    for (const lot of warehouse.lots) {
      if (typeof lot.sku !== 'string' || !lot.sku || typeof lot.lot !== 'string' || !lot.lot || !Number.isInteger(lot.qty) || lot.qty <= 0 || !validDate(lot.expires)) throw { error: 'invalid_lot' };
    }
  }
  for (const order of input.orders) {
    if (typeof order.id !== 'string' || !order.id || ids.has(order.id) || typeof order.priority !== 'number' || !Number.isFinite(order.priority) || !Date.parse(order.submitted_at) || !Array.isArray(order.lines)) throw { error: 'invalid_order' };
    ids.add(order.id);
    for (const line of order.lines) {
      if (typeof line.sku !== 'string' || !line.sku || !Number.isInteger(line.qty) || line.qty <= 0 || typeof line.single_warehouse !== 'boolean') throw { error: 'invalid_line' };
    }
  }
}
function fulfill(input) {
  validate(input);
  let stock = structuredClone(input.warehouses).sort((a, b) => a.distance - b.distance || a.id.localeCompare(b.id));
  for (const warehouse of stock) warehouse.lots.sort((a, b) => a.expires.localeCompare(b.expires) || a.lot.localeCompare(b.lot));
  const accepted = [], rejected = [];
  const orders = [...input.orders].sort((a, b) => b.priority - a.priority || exactSubmittedCompare(a.submitted_at, b.submitted_at) || a.id.localeCompare(b.id));
  for (const order of orders) {
    const tentative = structuredClone(stock), allocations = [];
    let possible = true;
    for (const line of order.lines) {
      let remaining = line.qty;
      const candidates = line.single_warehouse
        ? tentative.filter(w => w.lots.filter(l => l.sku === line.sku).reduce((n, l) => n + l.qty, 0) >= line.qty).slice(0, 1)
        : tentative;
      for (const warehouse of candidates) {
        for (const lot of warehouse.lots) {
          if (lot.sku !== line.sku || remaining === 0) continue;
          const taken = Math.min(lot.qty, remaining);
          if (taken) { lot.qty -= taken; remaining -= taken; allocations.push({ sku: line.sku, warehouse: warehouse.id, lot: lot.lot, qty: taken }); }
        }
      }
      if (remaining) { possible = false; break; }
    }
    if (possible) { stock = tentative; accepted.push({ id: order.id, allocations }); }
    else rejected.push({ id: order.id, reason: 'insufficient_stock' });
  }
  const rejectedOrder = new Map(input.orders.map((o, i) => [o.id, i]));
  rejected.sort((a, b) => rejectedOrder.get(a.id) - rejectedOrder.get(b.id));
  const remaining = stock.flatMap(w => w.lots.filter(l => l.qty).map(l => ({ warehouse: w.id, sku: l.sku, lot: l.lot, qty: l.qty, expires: l.expires })));
  remaining.sort((a, b) => a.warehouse.localeCompare(b.warehouse) || a.sku.localeCompare(b.sku) || a.expires.localeCompare(b.expires) || a.lot.localeCompare(b.lot));
  return { accepted, rejected, remaining };
}
function main(args) {
  const [command, ...rest] = args;
  if (command === 'hello') { const i = rest.indexOf('--name'); console.log(`Hello, ${i < 0 ? 'world' : rest[i + 1]}!`); return; }
  if (command === 'version') { console.log(require('../package.json').version); return; }
  if (command !== 'fulfill-wave') { console.log('Usage: bench-cli fulfill-wave --input <path>'); return; }
  try {
    if (rest[0] !== '--input' || !rest[1]) throw { error: 'invalid_input' };
    console.log(JSON.stringify(fulfill(JSON.parse(fs.readFileSync(rest[1], 'utf8')))));
  } catch (e) { error(e && e.error ? e : { error: 'invalid_input' }); }
}
main(process.argv.slice(2));
