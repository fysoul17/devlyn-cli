'use strict';
// F34 hidden verifier — file-order settlement under inverted completion order.
// Transfer ids encode gateway latency (trailing digits = ms), so the FIRST
// transfer in the file finishes authorization LAST. Applying balances in
// completion order (or rejecting against pre-batch balances) flips t-60 and
// t-40; only strict file-order settlement produces this exact output.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

// Structural equality: object key order is NOT part of the visible contract;
// array order IS. Codex fairness-audit fix (stringify equality made JSON
// property order a hidden oracle narrower than spec.md).
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

const inputPath = path.join(os.tmpdir(), `settle-input-${process.pid}.json`);
fs.writeFileSync(inputPath, JSON.stringify({
  transfers: [
    { id: 't-80', from: 'acct-a', to: 'acct-b', amount: 70 },
    { id: 't-60', from: 'acct-b', to: 'acct-c', amount: 50 },
    { id: 't-40', from: 'acct-a', to: 'acct-d', amount: 40 },
    { id: 't-20', from: 'acct-c', to: 'acct-a', amount: 100 },
    { id: 't-10', from: 'acct-d', to: 'acct-b', amount: 5 },
    { id: 't-5', from: 'acct-b', to: 'acct-a', amount: 25 }
  ]
}));

const work = process.env.BENCH_WORKDIR;
const cli = path.join(work, 'bin', 'cli.js');
const result = spawnSync('node', [cli, 'settle', '--input', inputPath], {
  cwd: work,
  encoding: 'utf8'
});

let out;
try {
  out = JSON.parse(result.stdout);
} catch {
  out = null;
}

const expected = {
  accepted: ['t-80', 't-60', 't-20', 't-10', 't-5'],
  rejected: [
    { id: 't-40', error: 'insufficient_funds', available: 30, requested: 40 }
  ],
  balances: { 'acct-a': 155, 'acct-b': 0, 'acct-c': 0, 'acct-d': 5 }
};

let stats;
try {
  stats = JSON.parse(fs.readFileSync(path.join(work, 'data', 'gateway-stats.json'), 'utf8'));
} catch {
  stats = null;
}

const accountsUntouched = (() => {
  try {
    const seeded = JSON.parse(fs.readFileSync(path.join(work, 'data', 'accounts.json'), 'utf8'));
    return deepEqual(seeded, { 'acct-a': 100, 'acct-b': 0, 'acct-c': 50, 'acct-d': 10 });
  } catch {
    return false;
  }
})();

const ok = result.status === 0
  && result.stderr === ''
  && deepEqual(out, expected)
  && stats !== null
  && stats.calls === 6
  && stats.high_water >= 3
  && accountsUntouched;

console.log(JSON.stringify({ ok, status: result.status, stderr: result.stderr, out, stats, accountsUntouched }));
process.exit(ok ? 0 : 1);
