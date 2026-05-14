'use strict';
const assert = require('node:assert');
const { spawnSync } = require('node:child_process');
const path = require('node:path');

const work = process.env.BENCH_WORKDIR || process.cwd();
const cli = path.join(work, 'bin', 'cli.js');

const policies = JSON.stringify([
  {
    category: 'electronics',
    restock_window_days: 30,
    destinations: {
      restock: 'restock-a',
      refurbish: 'refurb-a',
      dispose: 'dispose-a'
    }
  }
]);
const capacity = JSON.stringify({
  'dispose-a': 1,
  'refurb-a': 1,
  'restock-a': 1
});
const returns = JSON.stringify([
  { id: 'low-sealed', category: 'electronics', condition: 'sealed', days_since_purchase: 10, priority: 1 },
  { id: 'vip-opened', category: 'electronics', condition: 'opened', days_since_purchase: 20, priority: 10 },
  { id: 'vip-damaged', category: 'electronics', condition: 'damaged', days_since_purchase: 5, priority: 9 },
  { id: 'std-sealed', category: 'electronics', condition: 'sealed', days_since_purchase: 10, priority: 5 },
  { id: 'late-sealed', category: 'electronics', condition: 'sealed', days_since_purchase: 10, priority: 4 },
  { id: 'unknown-cat', category: 'furniture', condition: 'sealed', days_since_purchase: 1, priority: 3 }
]);

const result = spawnSync('node', [
  cli,
  'route-returns',
  '--policies',
  policies,
  '--capacity',
  capacity,
  '--returns',
  returns
], {
  cwd: work,
  encoding: 'utf8'
});

assert.strictEqual(result.status, 0, result.stderr || result.stdout);
assert.strictEqual(result.stderr, '');
const parsed = JSON.parse(result.stdout);

assert.deepStrictEqual(parsed, {
  routed: [
    { id: 'vip-opened', destination: 'refurb-a' },
    { id: 'vip-damaged', destination: 'dispose-a' },
    { id: 'std-sealed', destination: 'restock-a' }
  ],
  rejected: [
    { id: 'low-sealed', reason: 'destination_full' },
    { id: 'late-sealed', reason: 'destination_full' },
    { id: 'unknown-cat', reason: 'unknown_category' }
  ],
  capacity: {
    'dispose-a': 0,
    'refurb-a': 0,
    'restock-a': 0
  }
});

console.log(JSON.stringify({ ok: true }));
