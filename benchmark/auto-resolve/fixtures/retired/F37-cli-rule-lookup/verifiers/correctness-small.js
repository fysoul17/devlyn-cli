'use strict';
// F37 hidden verifier — one bundled scenario exercising: (1) different
// events in the same category resolving to different revisions by their
// own timestamp, (2) the inclusive effectiveAt<=timestamp boundary (an
// exact match is eligible), (3) the same-effectiveAt tie-break (greatest
// id wins), (4) unknown_category vs no_effective_rule are distinct and
// correctly assigned. Resets the seed so this verifier is order-independent
// from other verifier commands (F35 pattern).
//
// Structural equality: object key order is not part of the visible
// contract; array order is.
function deepEqual(a, b) {
  if (a === b) return true;
  if (Array.isArray(a) && Array.isArray(b)) {
    return a.length === b.length && a.every((v, i) => deepEqual(v, b[i]));
  }
  if (a && b && typeof a === 'object' && typeof b === 'object' && !Array.isArray(a) && !Array.isArray(b)) {
    const ka = Object.keys(a).sort();
    const kb = Object.keys(b).sort();
    return deepEqual(ka, kb) && ka.every((k) => deepEqual(a[k], b[k]));
  }
  return false;
}

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const work = process.env.BENCH_WORKDIR;
const revPath = path.join(work, 'data', 'rule-revisions.json');
const cli = path.join(work, 'bin', 'cli.js');

const revisions = [
  { id: 'rev-a2', categoryId: 'cat-A', effectiveAt: 200, discountPct: 20, minPrice: 10 },
  { id: 'rev-a9', categoryId: 'cat-A', effectiveAt: 300, discountPct: 90, minPrice: 10 },
  { id: 'rev-a1', categoryId: 'cat-A', effectiveAt: 100, discountPct: 10, minPrice: 10 },
  { id: 'rev-b1', categoryId: 'cat-B', effectiveAt: 50, discountPct: 0, minPrice: 5 },
  { id: 'rev-a3', categoryId: 'cat-A', effectiveAt: 300, discountPct: 30, minPrice: 10 },
];
fs.writeFileSync(revPath, JSON.stringify(revisions, null, 2) + '\n');

const inputPath = path.join(os.tmpdir(), `price-events-small-${process.pid}.json`);
fs.writeFileSync(inputPath, JSON.stringify({
  events: [
    { id: 'e1', categoryId: 'cat-A', timestamp: 150, basePrice: 100 },
    { id: 'e2', categoryId: 'cat-A', timestamp: 250, basePrice: 100 },
    { id: 'e3', categoryId: 'cat-A', timestamp: 200, basePrice: 50 },
    { id: 'e4', categoryId: 'cat-A', timestamp: 350, basePrice: 100 },
    { id: 'e5', categoryId: 'cat-B', timestamp: 10, basePrice: 100 },
    { id: 'e6', categoryId: 'cat-C', timestamp: 1000, basePrice: 100 },
  ],
}));

const result = spawnSync('node', [cli, 'price-events', '--input', inputPath], {
  cwd: work,
  encoding: 'utf8',
  maxBuffer: 16 * 1024 * 1024,
});

let out = null;
try {
  out = JSON.parse(result.stdout);
} catch {
  out = null;
}

const expected = {
  priced: [
    { id: 'e1', ruleId: 'rev-a1', price: 90 },
    { id: 'e2', ruleId: 'rev-a2', price: 80 },
    { id: 'e3', ruleId: 'rev-a2', price: 40 },
    { id: 'e4', ruleId: 'rev-a9', price: 10 },
  ],
  rejected: [
    { id: 'e5', reason: 'no_effective_rule' },
    { id: 'e6', reason: 'unknown_category' },
  ],
};

const ok = result.status === 0 && result.stderr === '' && deepEqual(out, expected);

console.log(JSON.stringify({ ok, status: result.status, stderr: result.stderr, out, expected }));
process.exit(ok ? 0 : 1);
