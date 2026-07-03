'use strict';
// F36 hidden verifier — four independent small-scale correctness sub-traps:
// (1) half-open boundary (touching is not overlapping), (2) eligibility
// order is by `start` ascending with file-order tiebreak, not file order or
// output order, (3) `blocking` reports the exact currently-active admitted
// ids at each candidate's own turn (not a static/final list), (4) eviction
// must be driven by actual expiry (`end`), not admission order — a FIFO
// queue that only evicts from its front would miss B's expiry here since A
// (admitted first, longer-lived) is still in front and never expired.
//
// Structural equality: object key order is not part of the visible
// contract; array order is (Codex fairness-audit pattern from F35).
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
const cli = path.join(work, 'bin', 'cli.js');

let callCount = 0;
function runAdmit(payload) {
  callCount += 1;
  const inputPath = path.join(os.tmpdir(), `admit-small-${process.pid}-${callCount}.json`);
  fs.writeFileSync(inputPath, JSON.stringify(payload));
  const result = spawnSync('node', [cli, 'admit', '--input', inputPath], {
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
  return { result, out };
}

const failures = [];

// Sub-test 1: half-open boundary — b.start === a.end must not overlap.
{
  const { result, out } = runAdmit({
    capacity: 1,
    sessions: [
      { id: 'a', start: 0, end: 10 },
      { id: 'b', start: 10, end: 20 },
    ],
  });
  const expected = { admitted: ['a', 'b'], deferred: [] };
  if (result.status !== 0 || result.stderr !== '' || !deepEqual(out, expected)) {
    failures.push({ test: 'boundary', status: result.status, stderr: result.stderr, out, expected });
  }
}

// Sub-test 2: eligibility order is by start ascending (file-order tiebreak
// only applies to equal starts) — output arrays follow eligibility order,
// not input file order.
{
  const { result, out } = runAdmit({
    capacity: 1,
    sessions: [
      { id: 'x', start: 5, end: 6 },
      { id: 'y', start: 1, end: 2 },
    ],
  });
  const expected = { admitted: ['y', 'x'], deferred: [] };
  if (result.status !== 0 || result.stderr !== '' || !deepEqual(out, expected)) {
    failures.push({ test: 'eligibility-order', status: result.status, stderr: result.stderr, out, expected });
  }
}

// Sub-test 3: `blocking` must be the exact currently-active admitted ids at
// each candidate's own turn, not a static or cumulative list.
{
  const { result, out } = runAdmit({
    capacity: 2,
    sessions: [
      { id: 'a', start: 0, end: 5 },
      { id: 'b', start: 1, end: 100 },
      { id: 'c', start: 2, end: 3 },
      { id: 'd', start: 10, end: 100 },
      { id: 'e', start: 15, end: 16 },
    ],
  });
  const expected = {
    admitted: ['a', 'b', 'd'],
    deferred: [
      { id: 'c', reason: 'over_capacity', blocking: ['a', 'b'] },
      { id: 'e', reason: 'over_capacity', blocking: ['b', 'd'] },
    ],
  };
  if (result.status !== 0 || result.stderr !== '' || !deepEqual(out, expected)) {
    failures.push({ test: 'blocking-per-candidate', status: result.status, stderr: result.stderr, out, expected });
  }
}

// Sub-test 4: eviction must be driven by actual expiry, not admission
// order. A (admitted 1st, end=100) stays in front of any admission-order
// queue; B (admitted 2nd, end=3) expires first. C's admission at start=5
// depends on correctly evicting B (expired) while keeping A (still
// active) — a front-only-eviction shortcut stops at A and never checks B,
// leaving B incorrectly counted as active and wrongly deferring C.
{
  const { result, out } = runAdmit({
    capacity: 2,
    sessions: [
      { id: 'A', start: 0, end: 100 },
      { id: 'B', start: 1, end: 3 },
      { id: 'C', start: 5, end: 6 },
    ],
  });
  const expected = { admitted: ['A', 'B', 'C'], deferred: [] };
  if (result.status !== 0 || result.stderr !== '' || !deepEqual(out, expected)) {
    failures.push({ test: 'non-monotonic-eviction', status: result.status, stderr: result.stderr, out, expected });
  }
}

const ok = failures.length === 0;
console.log(JSON.stringify({ ok, failures }));
process.exit(ok ? 0 : 1);
