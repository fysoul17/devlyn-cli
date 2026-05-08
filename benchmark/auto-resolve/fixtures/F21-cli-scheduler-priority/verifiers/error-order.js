'use strict';
const assert = require('node:assert');
const { execFileSync, spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const work = process.env.BENCH_WORKDIR || process.cwd();
const cli = path.join(work, 'bin', 'cli.js');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'f21-errors-'));

const unknownInput = path.join(tmp, 'unknown.json');
fs.writeFileSync(unknownInput, JSON.stringify({
  resources: [
    { id: 'r1', windows: [{ start: '10:00', end: '10:30' }], blocked: [] }
  ],
  requests: [
    { id: 'unknown-first', resource: 'missing', start: '10:00', duration_min: 5, priority: 9, submitted_at: '2026-01-01T10:00:00Z' },
    { id: 'too-long', resource: 'r1', start: '10:00', duration_min: 45, priority: 8, submitted_at: '2026-01-01T10:01:00Z' },
    { id: 'ok', resource: 'r1', start: '10:00', duration_min: 30, priority: 7, submitted_at: '2026-01-01T10:02:00Z' }
  ]
}), 'utf8');

const out = execFileSync('node', [cli, 'schedule', '--input', unknownInput], {
  cwd: work,
  encoding: 'utf8',
  stdio: ['ignore', 'pipe', 'pipe']
});
const parsed = JSON.parse(out);
assert.deepStrictEqual(parsed.scheduled, [
  { id: 'ok', resource: 'r1', start: '10:00', end: '10:30' }
]);
assert.deepStrictEqual(parsed.rejected, [
  { id: 'unknown-first', reason: 'unknown_resource' },
  { id: 'too-long', reason: 'no_slot' }
]);

const dupInput = path.join(tmp, 'dup.json');
fs.writeFileSync(dupInput, JSON.stringify({
  resources: [
    { id: 'r1', windows: [{ start: '10:00', end: '11:00' }], blocked: [] }
  ],
  requests: [
    { id: 'dup', resource: 'r1', start: '10:00', duration_min: 10, priority: 1, submitted_at: '2026-01-01T10:00:00Z' },
    { id: 'dup', resource: 'r1', start: '10:10', duration_min: 10, priority: 1, submitted_at: '2026-01-01T10:01:00Z' }
  ]
}), 'utf8');
const dup = spawnSync('node', [cli, 'schedule', '--input', dupInput], {
  cwd: work,
  encoding: 'utf8'
});
assert.strictEqual(dup.status, 2);
assert.strictEqual(dup.stdout, '');
assert.doesNotThrow(() => JSON.parse(dup.stderr));
console.log(JSON.stringify({ ok: true }));
