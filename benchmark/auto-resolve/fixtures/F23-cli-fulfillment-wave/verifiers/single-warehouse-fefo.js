'use strict';
const assert = require('node:assert');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const work = process.env.BENCH_WORKDIR || process.cwd();
const cli = path.join(work, 'bin', 'cli.js');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'f23-single-'));
const input = path.join(tmp, 'wave.json');

fs.writeFileSync(input, JSON.stringify({
  warehouses: [
    {
      id: 'east',
      distance: 2,
      lots: [
        { sku: 'K', lot: 'e-late', qty: 2, expires: '2026-04-01' },
        { sku: 'K', lot: 'e-early', qty: 1, expires: '2026-03-01' }
      ]
    },
    {
      id: 'west',
      distance: 1,
      lots: [
        { sku: 'K', lot: 'w-only', qty: 2, expires: '2026-02-01' },
        { sku: 'Z', lot: 'w-z', qty: 1, expires: '2026-02-01' }
      ]
    }
  ],
  orders: [
    { id: 'single-ok', priority: 10, submitted_at: '2026-01-01T09:00:00Z', lines: [{ sku: 'K', qty: 3, single_warehouse: true }] },
    { id: 'single-reject', priority: 9, submitted_at: '2026-01-01T09:01:00Z', lines: [{ sku: 'K', qty: 3, single_warehouse: true }] },
    { id: 'normal-z', priority: 8, submitted_at: '2026-01-01T09:02:00Z', lines: [{ sku: 'Z', qty: 1, single_warehouse: false }] }
  ]
}), 'utf8');

const stdout = execFileSync('node', [cli, 'fulfill-wave', '--input', input], {
  cwd: work,
  encoding: 'utf8',
  stdio: ['ignore', 'pipe', 'pipe']
});
const parsed = JSON.parse(stdout);
assert.deepStrictEqual(parsed.accepted, [
  {
    id: 'single-ok',
    allocations: [
      { sku: 'K', warehouse: 'east', lot: 'e-early', qty: 1 },
      { sku: 'K', warehouse: 'east', lot: 'e-late', qty: 2 }
    ]
  },
  {
    id: 'normal-z',
    allocations: [
      { sku: 'Z', warehouse: 'west', lot: 'w-z', qty: 1 }
    ]
  }
]);
assert.deepStrictEqual(parsed.rejected, [
  { id: 'single-reject', reason: 'insufficient_stock' }
]);
assert.deepStrictEqual(parsed.remaining, [
  { warehouse: 'west', sku: 'K', lot: 'w-only', qty: 2, expires: '2026-02-01' }
]);
console.log(JSON.stringify({ ok: true }));
