'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const orderPath = path.join(os.tmpdir(), `quote-order-${process.pid}.json`);
fs.writeFileSync(orderPath, JSON.stringify({
  state: 'CA',
  coupon: 'SAVE10',
  items: [
    { sku: 'A', qty: 1 },
    { sku: 'B', qty: 3 },
    { sku: 'A', qty: 1 }
  ]
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

const expected = {
  subtotal_cents: 4748,
  discount_cents: 475,
  tax_cents: 290,
  shipping_cents: 499,
  total_cents: 5062,
  items: [
    { sku: 'A', qty: 2, line_cents: 3998 },
    { sku: 'B', qty: 3, line_cents: 750 }
  ]
};

const ok = result.status === 0
  && result.stderr === ''
  && JSON.stringify(quote) === JSON.stringify(expected);

console.log(JSON.stringify({
  ok,
  status: result.status,
  stderr: result.stderr,
  quote
}));
process.exit(ok ? 0 : 1);
