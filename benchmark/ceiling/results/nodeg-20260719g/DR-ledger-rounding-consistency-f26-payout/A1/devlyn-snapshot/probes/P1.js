#!/usr/bin/env node
// Compound probe: valid events file -> exact JSON stdout shape with correct
// integer-cent totals (Verification bullet 2), combined with idempotent
// dedup of an identical-content duplicate `id` (Requirements section).
'use strict';

const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const repoRoot = path.join(__dirname, '..', '..');
const cli = path.join(repoRoot, 'bin', 'cli.js');

function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((k) => `${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

function fail(msg) {
  console.error(`P1 FAIL: ${msg}`);
  process.exit(1);
}

// Duplicate-content pair for id "e1" (byte-identical event repeated) plus a
// refund/dispute on the same merchant and a second merchant, so the run
// exercises full-shape assertions and proves the duplicate was NOT
// double-counted (gross_charge_cents must reflect a single charge).
const events = {
  events: [
    { id: 'e1', merchant_id: 'm1', type: 'charge', amount_cents: 10000 },
    { id: 'e1', merchant_id: 'm1', type: 'charge', amount_cents: 10000 },
    { id: 'e2', merchant_id: 'm1', type: 'refund', amount_cents: 2000 },
    { id: 'e3', merchant_id: 'm1', type: 'dispute', amount_cents: 3000 },
    { id: 'e4', merchant_id: 'm2', type: 'charge', amount_cents: 50000 },
  ],
};

const tmpFile = path.join(os.tmpdir(), `devlyn-p1-${process.pid}.json`);
fs.writeFileSync(tmpFile, JSON.stringify(events));

let result;
try {
  result = spawnSync('node', [cli, 'payout', '--input', tmpFile], { encoding: 'utf8' });
} finally {
  fs.rmSync(tmpFile, { force: true });
}

if (result.status !== 0) {
  fail(`expected exit 0, got ${result.status}; stderr=${JSON.stringify(result.stderr)}; stdout=${JSON.stringify(result.stdout)}`);
}
if (result.stderr !== '') {
  fail(`expected empty stderr, got ${JSON.stringify(result.stderr)}`);
}

let parsed;
try {
  parsed = JSON.parse(result.stdout);
} catch (err) {
  fail(`stdout is not valid JSON: ${JSON.stringify(result.stdout)} (${err.message})`);
}

const expectedTopKeys = ['total_payout_cents', 'total_processing_fee_cents', 'total_dispute_fee_cents', 'total_reserve_cents', 'merchants'];
const actualTopKeys = Object.keys(parsed);
if (canonical(actualTopKeys.slice().sort()) !== canonical(expectedTopKeys.slice().sort())) {
  fail(`top-level keys mismatch: expected ${JSON.stringify(expectedTopKeys)}, got ${JSON.stringify(actualTopKeys)}`);
}

// Expected values computed from data/payout-rules.json's current values
// (processing_fee_percent=2.9, fixed_fee_cents=30, dispute_fee_cents=1500,
// reserve_percent=10, minimum_payout_cents=1000) applying the spec formulas,
// with the duplicate e1 counted exactly once.
const expected = {
  total_payout_cents: 46530,
  total_processing_fee_cents: 1800,
  total_dispute_fee_cents: 1500,
  total_reserve_cents: 5170,
  merchants: [
    {
      merchant_id: 'm1',
      gross_charge_cents: 10000,
      refund_cents: 2000,
      dispute_cents: 3000,
      processing_fee_cents: 320,
      dispute_fee_cents: 1500,
      reserve_cents: 318,
      payout_cents: 2862,
    },
    {
      merchant_id: 'm2',
      gross_charge_cents: 50000,
      refund_cents: 0,
      dispute_cents: 0,
      processing_fee_cents: 1480,
      dispute_fee_cents: 0,
      reserve_cents: 4852,
      payout_cents: 43668,
    },
  ],
};

for (const key of ['total_payout_cents', 'total_processing_fee_cents', 'total_dispute_fee_cents', 'total_reserve_cents']) {
  if (parsed[key] !== expected[key]) {
    fail(`${key} mismatch: expected ${expected[key]}, got ${JSON.stringify(parsed[key])} (full stdout=${JSON.stringify(parsed)})`);
  }
}

if (!Array.isArray(parsed.merchants) || parsed.merchants.length !== expected.merchants.length) {
  fail(`expected ${expected.merchants.length} merchant rows in first-seen order, got ${JSON.stringify(parsed.merchants)}`);
}

const merchantRowKeys = ['merchant_id', 'gross_charge_cents', 'refund_cents', 'dispute_cents', 'processing_fee_cents', 'dispute_fee_cents', 'reserve_cents', 'payout_cents'];
for (let i = 0; i < expected.merchants.length; i += 1) {
  const actualRow = parsed.merchants[i] || {};
  const actualRowKeys = Object.keys(actualRow);
  if (canonical(actualRowKeys.slice().sort()) !== canonical(merchantRowKeys.slice().sort())) {
    fail(`merchant row ${i} keys mismatch: expected ${JSON.stringify(merchantRowKeys)}, got ${JSON.stringify(actualRowKeys)}`);
  }
  if (canonical(actualRow) !== canonical(expected.merchants[i])) {
    fail(`merchant row ${i} value mismatch (dedup/order/totals): expected ${JSON.stringify(expected.merchants[i])}, got ${JSON.stringify(actualRow)}`);
  }
}

console.log('P1 PASS');
process.exit(0);
