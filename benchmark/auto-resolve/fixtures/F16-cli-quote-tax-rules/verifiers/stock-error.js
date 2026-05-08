'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const orderPath = path.join(os.tmpdir(), `quote-stock-${process.pid}.json`);
fs.writeFileSync(orderPath, JSON.stringify({
  state: 'NY',
  coupon: null,
  items: [
    { sku: 'A', qty: 2 },
    { sku: 'A', qty: 2 }
  ]
}));

const cli = path.join(process.env.BENCH_WORKDIR, 'bin', 'cli.js');
const result = spawnSync('node', [cli, 'quote', '--input', orderPath], {
  cwd: process.env.BENCH_WORKDIR,
  encoding: 'utf8'
});

let err;
try {
  err = JSON.parse(result.stderr);
} catch {
  err = null;
}

const ok = result.status === 2
  && result.stdout === ''
  && err
  && err.error === 'invalid_stock'
  && err.sku === 'A'
  && err.available === 3
  && err.requested === 4;

console.log(JSON.stringify({
  ok,
  status: result.status,
  stdout: result.stdout,
  err
}));
process.exit(ok ? 0 : 1);
