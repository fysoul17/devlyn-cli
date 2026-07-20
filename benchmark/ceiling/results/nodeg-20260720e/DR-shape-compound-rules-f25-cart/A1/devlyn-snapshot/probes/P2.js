#!/usr/bin/env node
'use strict';
// Stock-error contract probe for the bench-cli `cart` command.
// Proves duplicate SKUs are combined BEFORE the stock check: BAG (stock=4)
// is split into two rows (qty 2 and qty 3), each individually within stock,
// but their combined quantity (5) exceeds it. Asserts the exact invalid_stock
// error object on stderr (deep equality), exit code 2, and empty stdout.
const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const repoRoot = path.resolve(__dirname, '..', '..');
const inputPath = path.join(__dirname, 'tmp-p2-input.json');

const input = {
  state: 'CA',
  coupon: null,
  items: [
    { sku: 'BAG', qty: 2 },
    { sku: 'BAG', qty: 3 }
  ]
};
fs.writeFileSync(inputPath, JSON.stringify(input));

const result = spawnSync('node', ['bin/cli.js', 'cart', '--input', inputPath], {
  cwd: repoRoot,
  encoding: 'utf8'
});

// BAG catalog stock=4; combined requested qty = 2+3 = 5 > 4.
const expectedErr = { error: 'invalid_stock', sku: 'BAG', available: 4, requested: 5 };
const expectedErrKeys = ['error', 'sku', 'available', 'requested'].sort();

try {
  assert.strictEqual(result.status, 2, `expected exit 2, got ${result.status}`);
  assert.strictEqual(result.stdout, '', `expected empty stdout, got: ${JSON.stringify(result.stdout)}`);
  const parsedErr = JSON.parse(result.stderr);
  assert.deepStrictEqual(Object.keys(parsedErr).sort(), expectedErrKeys, 'error object key set mismatch (no unexpected/missing/aliased keys)');
  assert.deepStrictEqual(parsedErr, expectedErr, 'error object deep-equality mismatch (requested must be combined qty, not a raw per-item qty)');
  console.log('P2 PASS');
  process.exit(0);
} catch (err) {
  console.error('P2 FAIL:', err.message);
  console.error('raw status:', result.status);
  console.error('raw stdout:', JSON.stringify(result.stdout));
  console.error('raw stderr:', JSON.stringify(result.stderr));
  process.exit(1);
}
