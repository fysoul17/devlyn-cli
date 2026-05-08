'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const pricingPath = path.join(process.env.BENCH_WORKDIR, 'data', 'pricing.json');
const pricing = JSON.parse(fs.readFileSync(pricingPath, 'utf8'));
pricing.products.A.unit_cents = 2111;
pricing.products.A.stock = 5;
pricing.shipping_cents = 123;
fs.writeFileSync(pricingPath, JSON.stringify(pricing, null, 2));

const orderPath = path.join(os.tmpdir(), `quote-pricing-${process.pid}.json`);
fs.writeFileSync(orderPath, JSON.stringify({
  state: 'OR',
  coupon: null,
  items: [{ sku: 'A', qty: 2 }]
}));

const cli = path.join(process.env.BENCH_WORKDIR, 'bin', 'cli.js');
const result = spawnSync('node', [cli, 'quote', '--input', orderPath], {
  cwd: process.env.BENCH_WORKDIR,
  encoding: 'utf8'
});

let quote;
try {
  quote = JSON.parse(result.stdout);
} catch {
  quote = null;
}

const ok = result.status === 0
  && result.stderr === ''
  && quote
  && quote.subtotal_cents === 4222
  && quote.shipping_cents === 123
  && quote.total_cents === 4345;

console.log(JSON.stringify({
  ok,
  status: result.status,
  quote
}));
process.exit(ok ? 0 : 1);
