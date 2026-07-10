'use strict';

const assert = require('node:assert');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const work = process.env.BENCH_WORKDIR || process.cwd();
const cli = path.join(work, 'bin', 'cli.js');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'f23-contract-'));
let inputIndex = 0;

function parseObject(text, label) {
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch (error) {
    assert.fail(`${label} is not exactly one JSON value: ${error.message}`);
  }
  assert.ok(parsed !== null && typeof parsed === 'object' && !Array.isArray(parsed), `${label} must be a JSON object`);
  return parsed;
}

function invoke(input) {
  inputIndex += 1;
  const inputPath = path.join(tmp, `wave-${inputIndex}.json`);
  const original = JSON.stringify(input);
  fs.writeFileSync(inputPath, original, 'utf8');
  const result = spawnSync('node', [cli, 'fulfill-wave', '--input', inputPath], {
    cwd: work,
    encoding: 'utf8'
  });
  assert.ifError(result.error);
  assert.strictEqual(fs.readFileSync(inputPath, 'utf8'), original, 'fulfill-wave mutated its input file');
  return result;
}

function assertInvalid(input, label) {
  const result = invoke(input);
  assert.strictEqual(result.status, 2, `${label}: expected exit 2; stderr=${result.stderr}`);
  assert.strictEqual(result.stdout, '', `${label}: stdout must be empty`);
  parseObject(result.stderr, `${label}: stderr`);
}

function validInput() {
  return {
    warehouses: [
      {
        id: 'validation-warehouse',
        distance: 1,
        lots: [
          { sku: 'VALIDATION-SKU', lot: 'validation-lot', qty: 1, expires: '2034-01-31' }
        ]
      }
    ],
    orders: [
      {
        id: 'validation-order',
        priority: 1,
        submitted_at: '2033-01-01T00:00:00Z',
        lines: [{ sku: 'VALIDATION-SKU', qty: 1, single_warehouse: false }]
      }
    ]
  };
}

function changed(mutator) {
  const input = validInput();
  mutator(input);
  return input;
}

function main() {
  const successInput = {
    warehouses: [
      {
        id: 'wh-zulu',
        distance: 4,
        lots: [
          { sku: 'SKU-SINGLE', lot: 'single-zulu', qty: 2, expires: '2032-01-01' },
          { sku: 'REM-B', lot: 'rem-b', qty: 1, expires: '2030-01-01' }
        ]
      },
      {
        id: 'wh-bravo',
        distance: 1,
        lots: [
          { sku: 'SKU-TIE', lot: 'tie-bravo', qty: 1, expires: '2029-01-01' }
        ]
      },
      {
        id: 'wh-alpha',
        distance: 1,
        lots: [
          { sku: 'SKU-TIE', lot: 'tie-beta', qty: 1, expires: '2028-01-01' },
          { sku: 'SKU-TIE', lot: 'tie-alpha', qty: 1, expires: '2028-01-01' },
          { sku: 'SKU-PRIORITY', lot: 'priority-one', qty: 1, expires: '2027-01-01' },
          { sku: 'SKU-SINGLE', lot: 'single-alpha', qty: 2, expires: '2032-01-01' },
          { sku: 'REM-A', lot: 'late-beta', qty: 1, expires: '2031-01-01' },
          { sku: 'REM-A', lot: 'early-zulu', qty: 1, expires: '2030-01-01' },
          { sku: 'REM-A', lot: 'late-alpha', qty: 1, expires: '2031-01-01' }
        ]
      }
    ],
    orders: [
      { id: 'single-combined-only', priority: 8, submitted_at: '2033-01-01T00:00:00Z', lines: [{ sku: 'SKU-SINGLE', qty: 3, single_warehouse: true }] },
      { id: 'priority-low-input-first', priority: 1, submitted_at: '2033-01-01T00:04:00Z', lines: [{ sku: 'SKU-PRIORITY', qty: 1, single_warehouse: false }] },
      { id: 'order-tie-zulu', priority: 5, submitted_at: '2033-01-01T00:02:00Z', lines: [{ sku: 'SKU-TIE', qty: 1, single_warehouse: false }] },
      { id: 'priority-high-input-later', priority: 10, submitted_at: '2033-01-01T00:03:00Z', lines: [{ sku: 'SKU-PRIORITY', qty: 1, single_warehouse: false }] },
      { id: 'order-tie-alpha', priority: 5, submitted_at: '2033-01-01T00:02:00Z', lines: [{ sku: 'SKU-TIE', qty: 2, single_warehouse: false }] }
    ]
  };

  const success = invoke(successInput);
  assert.strictEqual(success.status, 0, success.stderr || success.stdout);
  assert.strictEqual(success.stderr, '');
  assert.deepStrictEqual(parseObject(success.stdout, 'success stdout'), {
    accepted: [
      {
        id: 'priority-high-input-later',
        allocations: [
          { sku: 'SKU-PRIORITY', warehouse: 'wh-alpha', lot: 'priority-one', qty: 1 }
        ]
      },
      {
        id: 'order-tie-alpha',
        allocations: [
          { sku: 'SKU-TIE', warehouse: 'wh-alpha', lot: 'tie-alpha', qty: 1 },
          { sku: 'SKU-TIE', warehouse: 'wh-alpha', lot: 'tie-beta', qty: 1 }
        ]
      },
      {
        id: 'order-tie-zulu',
        allocations: [
          { sku: 'SKU-TIE', warehouse: 'wh-bravo', lot: 'tie-bravo', qty: 1 }
        ]
      }
    ],
    rejected: [
      { id: 'single-combined-only', reason: 'insufficient_stock' },
      { id: 'priority-low-input-first', reason: 'insufficient_stock' }
    ],
    remaining: [
      { warehouse: 'wh-alpha', sku: 'REM-A', lot: 'early-zulu', qty: 1, expires: '2030-01-01' },
      { warehouse: 'wh-alpha', sku: 'REM-A', lot: 'late-alpha', qty: 1, expires: '2031-01-01' },
      { warehouse: 'wh-alpha', sku: 'REM-A', lot: 'late-beta', qty: 1, expires: '2031-01-01' },
      { warehouse: 'wh-alpha', sku: 'SKU-SINGLE', lot: 'single-alpha', qty: 2, expires: '2032-01-01' },
      { warehouse: 'wh-zulu', sku: 'REM-B', lot: 'rem-b', qty: 1, expires: '2030-01-01' },
      { warehouse: 'wh-zulu', sku: 'SKU-SINGLE', lot: 'single-zulu', qty: 2, expires: '2032-01-01' }
    ]
  });

  assertInvalid(null, 'null top-level input');
  assertInvalid({ warehouses: [], orders: {} }, 'orders collection');
  assertInvalid(changed((input) => { input.warehouses[0].id = ''; }), 'warehouse id');
  assertInvalid(changed((input) => { input.warehouses[0].distance = 'near'; }), 'warehouse distance');
  assertInvalid(changed((input) => { input.warehouses[0].lots = {}; }), 'lots collection');
  assertInvalid(changed((input) => { input.warehouses[0].lots[0].sku = ''; }), 'lot sku');
  assertInvalid(changed((input) => { input.warehouses[0].lots[0].lot = ''; }), 'lot id');
  assertInvalid(changed((input) => { input.warehouses[0].lots[0].qty = 0; }), 'zero lot quantity');
  assertInvalid(changed((input) => { input.warehouses[0].lots[0].qty = 1.5; }), 'fractional lot quantity');
  assertInvalid(changed((input) => { input.warehouses[0].lots[0].expires = '2034-02-30'; }), 'lot expiry');
  assertInvalid(changed((input) => { input.orders[0].id = ''; }), 'order id');
  assertInvalid(changed((input) => { input.orders[0].priority = 'urgent'; }), 'order priority');
  assertInvalid(changed((input) => { input.orders[0].submitted_at = 'not-an-iso-date'; }), 'submitted date');
  assertInvalid(changed((input) => { input.orders[0].lines = {}; }), 'lines collection');
  assertInvalid(changed((input) => { input.orders[0].lines[0].sku = ''; }), 'line sku');
  assertInvalid(changed((input) => { input.orders[0].lines[0].qty = -1; }), 'line quantity');
  assertInvalid(changed((input) => { input.orders[0].lines[0].single_warehouse = 'false'; }), 'single_warehouse type');
  assertInvalid(changed((input) => { input.orders.push(JSON.parse(JSON.stringify(input.orders[0]))); }), 'duplicate order ids');

  const missing = spawnSync('node', [cli, 'fulfill-wave', '--input', path.join(tmp, 'missing-wave.json')], {
    cwd: work,
    encoding: 'utf8'
  });
  assert.ifError(missing.error);
  assert.strictEqual(missing.status, 2);
  assert.strictEqual(missing.stdout, '');
  parseObject(missing.stderr, 'file-read stderr');

  process.stdout.write(JSON.stringify({ ok: true }) + '\n');
}

try {
  main();
} catch (error) {
  if (error instanceof assert.AssertionError) {
    process.stderr.write(`${error.stack || error.message}\n`);
    process.exit(1);
  }
  process.stderr.write(`${error.stack || error.message}\n`);
  process.exit(2);
} finally {
  fs.rmSync(tmp, { recursive: true, force: true });
}
