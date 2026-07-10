const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const workdir = process.env.BENCH_WORKDIR || process.cwd();
const input = path.join(os.tmpdir(), `cart-stock-${process.pid}.json`);

fs.writeFileSync(input, JSON.stringify({
  state: 'OR',
  coupon: null,
  items: [
    { sku: 'BAG', qty: 2 },
    { sku: 'MUG', qty: 1 },
    { sku: 'BAG', qty: 3 }
  ]
}));

const proc = spawnSync('node', ['bin/cli.js', 'cart', '--input', input], {
  cwd: workdir,
  encoding: 'utf8'
});

assert.strictEqual(proc.status, 2);
assert.strictEqual(proc.stdout, '');
assert.deepStrictEqual(JSON.parse(proc.stderr), {
  error: 'invalid_stock',
  sku: 'BAG',
  available: 4,
  requested: 5
});

process.stdout.write(JSON.stringify({ ok: true }) + '\n');
