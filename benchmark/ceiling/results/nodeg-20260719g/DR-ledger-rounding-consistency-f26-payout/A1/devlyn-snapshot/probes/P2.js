#!/usr/bin/env node
// Idempotency probe: proves the full duplicate-id contract in one run —
// (A) an identical-content duplicate `id` is silently deduped (single count),
// (B) a same-`id`-different-content duplicate is a conflicting duplicate:
// exit 2, empty stdout, exact `{"error":"conflicting_duplicate","id":...}`
// on stderr (Verification bullet 3).
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
  console.error(`P2 FAIL: ${msg}`);
  process.exit(1);
}

function runCli(events) {
  const tmpFile = path.join(os.tmpdir(), `devlyn-p2-${process.pid}-${Math.random().toString(36).slice(2)}.json`);
  fs.writeFileSync(tmpFile, JSON.stringify(events));
  try {
    return spawnSync('node', [cli, 'payout', '--input', tmpFile], { encoding: 'utf8' });
  } finally {
    fs.rmSync(tmpFile, { force: true });
  }
}

// --- Check A: first delivery then an identical duplicate is deduped -------
// (idempotency_replay: first_delivery_then_duplicate)
const dedupEvents = {
  events: [
    { id: 'd1', merchant_id: 'dm1', type: 'charge', amount_cents: 4000 },
    { id: 'd1', merchant_id: 'dm1', type: 'charge', amount_cents: 4000 },
  ],
};
const dedupResult = runCli(dedupEvents);

if (dedupResult.status !== 0) {
  fail(`Check A: expected exit 0 for identical duplicate, got ${dedupResult.status}; stderr=${JSON.stringify(dedupResult.stderr)}`);
}
if (dedupResult.stderr !== '') {
  fail(`Check A: expected empty stderr, got ${JSON.stringify(dedupResult.stderr)}`);
}
let dedupParsed;
try {
  dedupParsed = JSON.parse(dedupResult.stdout);
} catch (err) {
  fail(`Check A: stdout is not valid JSON: ${JSON.stringify(dedupResult.stdout)} (${err.message})`);
}
// Expected from data/payout-rules.json (processing_fee_percent=2.9,
// fixed_fee_cents=30, reserve_percent=10) for a single 4000-cent charge:
// processing_fee = round(4000*0.029)+30 = 146; net = 3854; reserve =
// round(385.4) = 385; payout = 3469. If the duplicate were double-counted,
// gross_charge_cents would be 8000 instead of 4000.
if (!dedupParsed.merchants || dedupParsed.merchants[0]?.gross_charge_cents !== 4000) {
  fail(`Check A: expected single-counted gross_charge_cents 4000 (duplicate deduped), got ${JSON.stringify(dedupParsed.merchants)}`);
}
if (dedupParsed.total_payout_cents !== 3469) {
  fail(`Check A: expected total_payout_cents 3469 (single count), got ${JSON.stringify(dedupParsed.total_payout_cents)}`);
}

// --- Check B: same id, different content is a conflicting duplicate -------
// (idempotency_replay: duplicate_id_rejected_regardless_of_body; error_contract; shape_contract)
const conflictEvents = {
  events: [
    { id: 'e1', merchant_id: 'm-x', type: 'charge', amount_cents: 7000 },
    { id: 'e1', merchant_id: 'm-x', type: 'charge', amount_cents: 7001 },
  ],
};
const conflictResult = runCli(conflictEvents);

if (conflictResult.status !== 2) {
  fail(`Check B: expected exit 2 for conflicting duplicate, got ${conflictResult.status}; stderr=${JSON.stringify(conflictResult.stderr)}; stdout=${JSON.stringify(conflictResult.stdout)}`);
}
if (conflictResult.stdout !== '') {
  fail(`Check B: expected empty stdout, got ${JSON.stringify(conflictResult.stdout)}`);
}
let conflictParsed;
try {
  conflictParsed = JSON.parse(conflictResult.stderr);
} catch (err) {
  fail(`Check B: stderr is not valid JSON: ${JSON.stringify(conflictResult.stderr)} (${err.message})`);
}
const expectedError = { error: 'conflicting_duplicate', id: 'e1' };
if (canonical(Object.keys(conflictParsed).sort()) !== canonical(Object.keys(expectedError).sort())) {
  fail(`Check B: error object keys mismatch: expected ${JSON.stringify(Object.keys(expectedError))}, got ${JSON.stringify(Object.keys(conflictParsed))}`);
}
if (canonical(conflictParsed) !== canonical(expectedError)) {
  fail(`Check B: error object mismatch: expected ${JSON.stringify(expectedError)}, got ${JSON.stringify(conflictParsed)}`);
}

console.log('P2 PASS');
process.exit(0);
