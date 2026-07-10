'use strict';
const assert = require('node:assert');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const work = process.env.BENCH_WORKDIR || process.cwd();
const cli = path.join(work, 'bin', 'cli.js');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'f21-schedule-'));
const input = path.join(tmp, 'input.json');

fs.writeFileSync(input, JSON.stringify({
  resources: [
    {
      id: 'room-a',
      windows: [{ start: '09:00', end: '10:00' }],
      blocked: [{ start: '09:30', end: '09:40' }]
    },
    {
      id: 'room-b',
      windows: [{ start: '09:00', end: '09:45' }],
      blocked: []
    }
  ],
  requests: [
    { id: 'low-first', resource: 'room-a', start: '09:00', duration_min: 30, priority: 1, submitted_at: '2026-01-01T09:00:00Z' },
    { id: 'high-second', resource: 'room-a', start: '09:00', duration_min: 30, priority: 10, submitted_at: '2026-01-01T09:05:00Z' },
    { id: 'edge-ok', resource: 'room-b', start: '09:15', duration_min: 30, priority: 5, submitted_at: '2026-01-01T09:01:00Z' },
    { id: 'blocked-one-minute', resource: 'room-a', start: '09:29', duration_min: 2, priority: 4, submitted_at: '2026-01-01T09:02:00Z' }
  ]
}), 'utf8');

const stdout = execFileSync('node', [cli, 'schedule', '--input', input], {
  cwd: work,
  encoding: 'utf8',
  stdio: ['ignore', 'pipe', 'pipe']
});
const parsed = JSON.parse(stdout);
assert.deepStrictEqual(parsed.scheduled, [
  { id: 'high-second', resource: 'room-a', start: '09:00', end: '09:30' },
  { id: 'edge-ok', resource: 'room-b', start: '09:15', end: '09:45' },
  { id: 'blocked-one-minute', resource: 'room-a', start: '09:40', end: '09:42' }
]);
assert.deepStrictEqual(parsed.rejected, [
  { id: 'low-first', reason: 'no_slot' }
]);
console.log(JSON.stringify({ ok: true }));
