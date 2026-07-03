'use strict';
// F36 hidden verifier — the performance discriminator. 150,000 sessions,
// each with a 100,000-unit duration (so the natural overlap peak reaches
// ~100,000 concurrently-active sessions across a wide middle stretch), with
// `capacity` set to 140,000 — comfortably above the natural peak (so
// nothing is ever actually deferred, keeping the expected output tiny and
// the correctness check trivial: everyone is admitted, in start order) but
// still below `n` (so an implementation cannot mathematically prove up
// front that capacity never binds and skip active-set tracking entirely —
// it must genuinely compute the active count per candidate for a batch this
// size and still get the right, ever-growing answer).
//
// Sessions are written to the input file in a shuffled (non-start-sorted)
// order via a deterministic permutation, so an implementation that trusts
// file order instead of actually sorting by `start` also fails here.
//
// A brute nested-loop-over-all-admitted approach, or a "keep an array of
// admitted sessions and linearly filter/scan it on every candidate"
// approach, costs on the order of n * (average active-set size) ~= 150,000
// * 90,000 =~ 1.35e10 element touches here — many minutes in Node. A
// genuinely sub-linear-per-op structure (evict-expired + size-check via an
// ordered-by-end structure) finishes in well under a second. The 15-second
// hard kill sits far above the efficient solution's expected running time
// and correspondingly far below any realistic degraded-shortcut running
// time, so the gate has a wide, non-flaky margin in both directions.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const work = process.env.BENCH_WORKDIR;
const cli = path.join(work, 'bin', 'cli.js');

const N = 150000;
const DURATION = 100000;
const CAPACITY = 140000;
const PERMUTE_MULTIPLIER = 99991; // coprime with N (150000 = 2^4 * 3 * 5^5)

const sessions = new Array(N);
for (let i = 0; i < N; i++) {
  const pos = (i * PERMUTE_MULTIPLIER) % N;
  sessions[pos] = { id: `s-${i}`, start: i, end: i + DURATION };
}

const inputPath = path.join(os.tmpdir(), `admit-scale-${process.pid}.json`);
fs.writeFileSync(inputPath, JSON.stringify({ capacity: CAPACITY, sessions }));

const start = Date.now();
const result = spawnSync('node', [cli, 'admit', '--input', inputPath], {
  cwd: work,
  encoding: 'utf8',
  timeout: 15000,
  killSignal: 'SIGKILL',
  maxBuffer: 64 * 1024 * 1024,
});
const elapsedMs = Date.now() - start;

const timedOut = result.status === null && result.signal !== null;

let out = null;
if (!timedOut) {
  try {
    out = JSON.parse(result.stdout);
  } catch {
    out = null;
  }
}

const expectedAdmitted = Array.from({ length: N }, (_, i) => `s-${i}`);

let correct = false;
let mismatch = null;
if (out && Array.isArray(out.admitted) && Array.isArray(out.deferred)) {
  correct =
    out.deferred.length === 0 &&
    out.admitted.length === expectedAdmitted.length &&
    out.admitted.every((id, i) => id === expectedAdmitted[i]);
  if (!correct) {
    mismatch = {
      admittedLength: out.admitted.length,
      deferredLength: out.deferred.length,
      firstMismatchIndex: out.admitted.findIndex((id, i) => id !== expectedAdmitted[i]),
    };
  }
}

const ok = !timedOut && result.status === 0 && result.stderr === '' && correct;

console.log(JSON.stringify({
  ok,
  timedOut,
  elapsedMs,
  status: result.status,
  signal: result.signal,
  stderrLength: result.stderr ? result.stderr.length : 0,
  correct,
  mismatch,
}));
process.exit(ok ? 0 : 1);
