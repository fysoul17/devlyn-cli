'use strict';
const assert = require('node:assert');
const { spawnSync } = require('node:child_process');
const path = require('node:path');

const work = process.env.BENCH_WORKDIR || process.cwd();
const cli = path.join(work, 'bin', 'cli.js');

const agents = JSON.stringify([
  { id: 'a-west', skills: ['billing'], capacity: 1 },
  { id: 'b-flex', skills: ['billing', 'tech'], capacity: 2 },
  { id: 'c-tech', skills: ['tech'], capacity: 1 }
]);
const tickets = JSON.stringify([
  { id: 'low-billing', skill: 'billing', priority: 1, created_at: '2026-01-01T00:00:00Z' },
  { id: 'vip-tech', skill: 'tech', priority: 9, created_at: '2026-01-01T00:00:00Z' },
  { id: 'vip-billing', skill: 'billing', priority: 10, created_at: '2026-01-02T00:00:00Z' },
  { id: 'std-tech', skill: 'tech', priority: 5, created_at: '2026-01-01T00:00:00Z' },
  { id: 'late-billing', skill: 'billing', priority: 8, created_at: '2026-01-01T00:00:00Z' }
]);

const result = spawnSync('node', [cli, 'assign-tickets', '--agents', agents, '--tickets', tickets], {
  cwd: work,
  encoding: 'utf8'
});

assert.strictEqual(result.status, 0, result.stderr || result.stdout);
assert.strictEqual(result.stderr, '');
const parsed = JSON.parse(result.stdout);

assert.deepStrictEqual(parsed, {
  assigned: [
    { id: 'vip-billing', agent: 'b-flex' },
    { id: 'vip-tech', agent: 'b-flex' },
    { id: 'late-billing', agent: 'a-west' },
    { id: 'std-tech', agent: 'c-tech' }
  ],
  unassigned: [
    { id: 'low-billing', reason: 'no_agent' }
  ],
  agents: [
    { id: 'a-west', remaining: 0 },
    { id: 'b-flex', remaining: 0 },
    { id: 'c-tech', remaining: 0 }
  ]
});

console.log(JSON.stringify({ ok: true }));
