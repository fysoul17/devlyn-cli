'use strict';
const assert = require('node:assert');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const work = process.env.BENCH_WORKDIR || process.cwd();
const cli = path.join(work, 'bin', 'cli.js');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'f31-rebalance-'));
const input = path.join(tmp, 'events.json');

fs.writeFileSync(input, JSON.stringify({
  accounts: [
    { id: 'team-a', region: 'us', seats: 5, used: 3 },
    { id: 'team-b', region: 'us', seats: 4, used: 1 },
    { id: 'team-eu', region: 'eu', seats: 4, used: 0 }
  ],
  events: [
    { id: 'low-reserve', type: 'reserve', account: 'team-b', qty: 3, priority: 1, effective_at: '2026-01-01T09:00:00Z' },
    { id: 'bad-cross', type: 'transfer', from: 'team-a', to: 'team-eu', qty: 1, priority: 8, effective_at: '2026-01-01T09:02:00Z' },
    { id: 'high-transfer', type: 'transfer', from: 'team-a', to: 'team-b', qty: 2, priority: 10, effective_at: '2026-01-01T09:05:00Z' },
    { id: 'after-release', type: 'release', account: 'team-a', qty: 1, priority: 7, effective_at: '2026-01-01T09:03:00Z' },
    { id: 'after-reserve', type: 'reserve', account: 'team-a', qty: 5, priority: 6, effective_at: '2026-01-01T09:04:00Z' }
  ]
}), 'utf8');

const result = spawnSync('node', [cli, 'rebalance-seats', '--input', input], {
  cwd: work,
  encoding: 'utf8'
});
assert.strictEqual(result.status, 0, result.stderr || result.stdout);
assert.strictEqual(result.stderr, '');
const parsed = JSON.parse(result.stdout);

assert.deepStrictEqual(parsed, {
  applied: [
    { id: 'high-transfer', type: 'transfer' },
    { id: 'after-release', type: 'release' },
    { id: 'after-reserve', type: 'reserve' }
  ],
  rejected: [
    { id: 'low-reserve', reason: 'no_capacity' },
    { id: 'bad-cross', reason: 'region_mismatch' }
  ],
  accounts: [
    { id: 'team-a', region: 'us', seats: 5, used: 5, free: 0 },
    { id: 'team-b', region: 'us', seats: 4, used: 3, free: 1 },
    { id: 'team-eu', region: 'eu', seats: 4, used: 0, free: 4 }
  ]
});

console.log(JSON.stringify({ ok: true }));
