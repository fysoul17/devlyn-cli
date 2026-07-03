'use strict';
// F37 hidden verifier — validation happens before any pricing decision:
// malformed event fields use `invalid_input`, duplicate event ids use the
// distinct `duplicate_event_id` shape, and nothing is priced or printed to
// stdout in either case. Resets the seed so this verifier is
// order-independent from other verifier commands.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const work = process.env.BENCH_WORKDIR;
const revPath = path.join(work, 'data', 'rule-revisions.json');
const cli = path.join(work, 'bin', 'cli.js');

const revisions = [
  { id: 'rev-a1', categoryId: 'cat-A', effectiveAt: 100, discountPct: 10, minPrice: 10 },
];

let callCount = 0;
function runPriceEvents(payload) {
  fs.writeFileSync(revPath, JSON.stringify(revisions, null, 2) + '\n');
  callCount += 1;
  const inputPath = path.join(os.tmpdir(), `price-events-validate-${process.pid}-${callCount}.json`);
  fs.writeFileSync(inputPath, JSON.stringify(payload));
  const result = spawnSync('node', [cli, 'price-events', '--input', inputPath], {
    cwd: work,
    encoding: 'utf8',
    maxBuffer: 16 * 1024 * 1024,
  });
  let err = null;
  try {
    err = JSON.parse(result.stderr);
  } catch {
    err = null;
  }
  return { result, err };
}

const failures = [];

function expectInvalidInput(label, payload) {
  const { result, err } = runPriceEvents(payload);
  const ok = result.status === 2 && result.stdout === '' && err !== null && err.error === 'invalid_input' && typeof err.reason === 'string';
  if (!ok) {
    failures.push({ test: label, status: result.status, stdout: result.stdout, stderr: result.stderr, err });
  }
}

expectInvalidInput('events-not-array', { events: 'nope' });
expectInvalidInput('missing-id', { events: [{ categoryId: 'cat-A', timestamp: 100, basePrice: 10 }] });
expectInvalidInput('non-integer-timestamp', { events: [{ id: 'e1', categoryId: 'cat-A', timestamp: 1.5, basePrice: 10 }] });
expectInvalidInput('negative-base-price', { events: [{ id: 'e1', categoryId: 'cat-A', timestamp: 100, basePrice: -1 }] });
expectInvalidInput('non-string-category', { events: [{ id: 'e1', categoryId: 42, timestamp: 100, basePrice: 10 }] });

// Duplicate event id — distinct error shape.
{
  const payload = {
    events: [
      { id: 'dup', categoryId: 'cat-A', timestamp: 100, basePrice: 10 },
      { id: 'dup', categoryId: 'cat-A', timestamp: 200, basePrice: 20 },
    ],
  };
  const { result, err } = runPriceEvents(payload);
  const ok = result.status === 2 && result.stdout === '' && err !== null && err.error === 'duplicate_event_id' && err.id === 'dup';
  if (!ok) {
    failures.push({ test: 'duplicate-event-id', status: result.status, stdout: result.stdout, stderr: result.stderr, err });
  }
}

const ok = failures.length === 0;
console.log(JSON.stringify({ ok, failures }));
process.exit(ok ? 0 : 1);
