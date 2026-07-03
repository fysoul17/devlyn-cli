'use strict';
// F37 hidden verifier — the performance discriminator. 60,000 rule
// revisions spread over 4 categories (15,000 revisions/category) and
// 200,000 events. Every event resolves successfully (no rejections),
// which keeps the expected output small and the correctness check a
// direct array comparison; the discriminator is entirely in how the
// lookup is done, not in exercising the reject paths (those are covered
// by correctness-small.js).
//
// A per-event linear scan of a category's revisions costs on the order of
// events * revisions-per-category =~ 200,000 * 15,000 = 3e9 comparisons —
// tens of seconds or more in Node. Grouping by category (near-free) and
// then binary-searching a sorted per-category list is a few million
// log-steps — trivially fast. The reference below independently
// implements the efficient shape (not shared code with the CLI) so it can
// also serve as ground truth without becoming a second bottleneck. The
// 15-second hard kill sits far above the efficient solution's expected
// running time and correspondingly far below any realistic
// linear-scan running time at these parameters.
//
// Revisions are written to `data/rule-revisions.json` in a shuffled
// (non-category-grouped, non-time-sorted) order via a deterministic
// permutation, matching the visible "not sorted by category or by time"
// spec fact and closing a "trust file order" shortcut.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const work = process.env.BENCH_WORKDIR;
const revPath = path.join(work, 'data', 'rule-revisions.json');
const cli = path.join(work, 'bin', 'cli.js');

const CATS = 4;
const REVS_PER_CAT = 15000;
const TOTAL_REVS = CATS * REVS_PER_CAT;
const EVENTS = 200000;
const REV_PERMUTE_MULTIPLIER = 39989; // coprime with 60000 (2^5 * 3 * 5^4)

const revisionsInOrder = new Array(TOTAL_REVS);
let k = 0;
for (let c = 0; c < CATS; c++) {
  for (let j = 0; j < REVS_PER_CAT; j++) {
    revisionsInOrder[k] = {
      id: `rev-${c}-${j}`,
      categoryId: `cat-${c}`,
      effectiveAt: j * 10,
      discountPct: (j * 7) % 50,
      minPrice: 100 + ((j * 13) % 900),
    };
    k += 1;
  }
}

const shuffled = new Array(TOTAL_REVS);
for (let i = 0; i < TOTAL_REVS; i++) {
  const pos = (i * REV_PERMUTE_MULTIPLIER) % TOTAL_REVS;
  shuffled[pos] = revisionsInOrder[i];
}
fs.writeFileSync(revPath, JSON.stringify(shuffled));

const events = new Array(EVENTS);
for (let i = 0; i < EVENTS; i++) {
  const c = i % CATS;
  const base = (i * 131) % REVS_PER_CAT;
  events[i] = {
    id: `ev-${i}`,
    categoryId: `cat-${c}`,
    timestamp: base * 10 + 5,
    basePrice: 1000 + (i % 500),
  };
}

const inputPath = path.join(os.tmpdir(), `price-events-scale-${process.pid}.json`);
fs.writeFileSync(inputPath, JSON.stringify({ events }));

// Independent reference: group by category, sort each group by
// (effectiveAt asc, id asc), binary-search the rightmost entry with
// effectiveAt <= timestamp.
const groups = new Map();
for (const rev of revisionsInOrder) {
  if (!groups.has(rev.categoryId)) groups.set(rev.categoryId, []);
  groups.get(rev.categoryId).push(rev);
}
for (const list of groups.values()) {
  list.sort((a, b) => a.effectiveAt - b.effectiveAt || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
}

function findRuleIndex(sorted, timestamp) {
  let lo = 0;
  let hi = sorted.length - 1;
  let ans = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (sorted[mid].effectiveAt <= timestamp) {
      ans = mid;
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }
  return ans;
}

const expectedPriced = new Array(EVENTS);
let expectedRejectedCount = 0;
for (let i = 0; i < EVENTS; i++) {
  const ev = events[i];
  const group = groups.get(ev.categoryId);
  if (!group) {
    expectedRejectedCount += 1;
    expectedPriced[i] = null;
    continue;
  }
  const idx = findRuleIndex(group, ev.timestamp);
  if (idx < 0) {
    expectedRejectedCount += 1;
    expectedPriced[i] = null;
    continue;
  }
  const rule = group[idx];
  const price = Math.max(rule.minPrice, Math.round((ev.basePrice * (100 - rule.discountPct)) / 100));
  expectedPriced[i] = { id: ev.id, ruleId: rule.id, price };
}

const start = Date.now();
const result = spawnSync('node', [cli, 'price-events', '--input', inputPath], {
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

let correct = false;
let mismatch = null;
if (out && Array.isArray(out.priced) && Array.isArray(out.rejected)) {
  correct =
    out.rejected.length === expectedRejectedCount &&
    out.priced.length === EVENTS - expectedRejectedCount &&
    out.priced.every((row, i) => {
      const expected = expectedPriced[i];
      return expected && row.id === expected.id && row.ruleId === expected.ruleId && row.price === expected.price;
    });
  if (!correct) {
    const firstMismatchIndex = out.priced.findIndex((row, i) => {
      const expected = expectedPriced[i];
      return !expected || row.id !== expected.id || row.ruleId !== expected.ruleId || row.price !== expected.price;
    });
    mismatch = {
      pricedLength: out.priced.length,
      rejectedLength: out.rejected.length,
      expectedRejectedCount,
      firstMismatchIndex,
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
