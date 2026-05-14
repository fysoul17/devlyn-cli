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
    destinations: { restock: 'restock-a', refurbish: 'refurb-a', dispose: 'dispose-a' }
  }
]);
const capacity = JSON.stringify({ 'restock-a': 1 });
const returns = JSON.stringify([
  { id: 'dup', category: 'electronics', condition: 'sealed', days_since_purchase: 1, priority: 2 },
  { id: 'dup', category: 'electronics', condition: 'opened', days_since_purchase: 1, priority: 1 }
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

assert.strictEqual(result.status, 2);
assert.strictEqual(result.stdout, '');
assert.deepStrictEqual(JSON.parse(result.stderr), {
  error: 'duplicate_return_id',
  id: 'dup'
});

console.log(JSON.stringify({ ok: true }));
