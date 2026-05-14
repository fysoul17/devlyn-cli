'use strict';
const assert = require('node:assert');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const work = process.env.BENCH_WORKDIR || process.cwd();
const cli = path.join(work, 'bin', 'cli.js');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'f31-duplicate-'));
const input = path.join(tmp, 'events.json');

fs.writeFileSync(input, JSON.stringify({
  accounts: [
    { id: 'team-a', region: 'us', seats: 5, used: 1 }
  ],
  events: [
    { id: 'dup', type: 'reserve', account: 'team-a', qty: 1, priority: 2, effective_at: '2026-01-01T09:00:00Z' },
    { id: 'dup', type: 'release', account: 'team-a', qty: 1, priority: 1, effective_at: '2026-01-01T09:01:00Z' }
  ]
}), 'utf8');

const result = spawnSync('node', [cli, 'rebalance-seats', '--input', input], {
  cwd: work,
  encoding: 'utf8'
});

assert.strictEqual(result.status, 2);
assert.strictEqual(result.stdout, '');
assert.deepStrictEqual(JSON.parse(result.stderr), {
  error: 'duplicate_event_id',
  id: 'dup'
});

console.log(JSON.stringify({ ok: true }));
