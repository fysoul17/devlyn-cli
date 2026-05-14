'use strict';
const assert = require('node:assert');
const { spawnSync } = require('node:child_process');
const path = require('node:path');

const work = process.env.BENCH_WORKDIR || process.cwd();
const cli = path.join(work, 'bin', 'cli.js');

const agents = JSON.stringify([
  { id: 'a-west', skills: ['billing'], capacity: 1 }
]);
const tickets = JSON.stringify([
  { id: 'dup', skill: 'billing', priority: 2, created_at: '2026-01-01T00:00:00Z' },
  { id: 'dup', skill: 'billing', priority: 1, created_at: '2026-01-02T00:00:00Z' }
]);

const result = spawnSync('node', [cli, 'assign-tickets', '--agents', agents, '--tickets', tickets], {
  cwd: work,
  encoding: 'utf8'
});

assert.strictEqual(result.status, 2);
assert.strictEqual(result.stdout, '');
assert.deepStrictEqual(JSON.parse(result.stderr), {
  error: 'duplicate_ticket_id',
  id: 'dup'
});

console.log(JSON.stringify({ ok: true }));
