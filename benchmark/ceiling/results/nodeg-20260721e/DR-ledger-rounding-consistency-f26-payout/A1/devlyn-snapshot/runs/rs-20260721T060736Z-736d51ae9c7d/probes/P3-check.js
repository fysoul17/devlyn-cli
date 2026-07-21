// P3: exact shape contract on successful stdout — top-level keys, merchant
// row keys, integer amounts, and totals == sum of the corresponding final
// merchant field. Reads the CLI's stdout from argv[2] (a file path).
const fs = require('fs');

const raw = fs.readFileSync(process.argv[2], 'utf8');
let parsed;
try {
  parsed = JSON.parse(raw);
} catch (e) {
  console.error('FAIL: stdout is not valid JSON: ' + e.message);
  process.exit(1);
}

const TOP_KEYS = [
  'total_payout_cents',
  'total_processing_fee_cents',
  'total_dispute_fee_cents',
  'total_reserve_cents',
  'merchants'
].sort();
const ROW_KEYS = [
  'merchant_id',
  'gross_charge_cents',
  'refund_cents',
  'dispute_cents',
  'processing_fee_cents',
  'dispute_fee_cents',
  'reserve_cents',
  'payout_cents'
].sort();

function fail(msg) {
  console.error('FAIL: ' + msg);
  process.exit(1);
}

const actualTop = Object.keys(parsed).sort();
if (JSON.stringify(actualTop) !== JSON.stringify(TOP_KEYS)) {
  fail(`top-level keys mismatch: expected ${JSON.stringify(TOP_KEYS)}, got ${JSON.stringify(actualTop)}`);
}

if (!Array.isArray(parsed.merchants) || parsed.merchants.length !== 1) {
  fail(`expected exactly 1 merchant row, got ${JSON.stringify(parsed.merchants)}`);
}

const row = parsed.merchants[0];
const actualRow = Object.keys(row).sort();
if (JSON.stringify(actualRow) !== JSON.stringify(ROW_KEYS)) {
  fail(`merchant row keys mismatch: expected ${JSON.stringify(ROW_KEYS)}, got ${JSON.stringify(actualRow)}`);
}

for (const key of TOP_KEYS.filter((k) => k !== 'merchants')) {
  if (!Number.isInteger(parsed[key])) {
    fail(`top-level ${key} must be an integer, got ${JSON.stringify(parsed[key])}`);
  }
}
for (const key of ROW_KEYS.filter((k) => k !== 'merchant_id')) {
  if (!Number.isInteger(row[key])) {
    fail(`merchant.${key} must be an integer, got ${JSON.stringify(row[key])}`);
  }
}

const sumChecks = [
  ['total_payout_cents', 'payout_cents'],
  ['total_processing_fee_cents', 'processing_fee_cents'],
  ['total_dispute_fee_cents', 'dispute_fee_cents'],
  ['total_reserve_cents', 'reserve_cents']
];
for (const [totalKey, rowKey] of sumChecks) {
  const expectedSum = parsed.merchants.reduce((acc, m) => acc + m[rowKey], 0);
  if (parsed[totalKey] !== expectedSum) {
    fail(`${totalKey} (${parsed[totalKey]}) must equal sum of merchants[].${rowKey} (${expectedSum})`);
  }
}

console.log('PASS: shape contract holds');
