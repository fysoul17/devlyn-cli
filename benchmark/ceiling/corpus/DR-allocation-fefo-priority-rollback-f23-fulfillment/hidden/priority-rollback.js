'use strict';
const assert = require('node:assert');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const work = process.env.BENCH_WORKDIR || process.cwd();
const cli = path.join(work, 'bin', 'cli.js');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'f23-wave-'));
const input = path.join(tmp, 'wave.json');

fs.writeFileSync(input, JSON.stringify({
  warehouses: [
    {
      id: 'near',
      distance: 1,
      lots: [
        { sku: 'A', lot: 'n-old', qty: 2, expires: '2026-02-01' },
        { sku: 'B', lot: 'n-b', qty: 1, expires: '2026-02-01' }
      ]
    },
    {
      id: 'far',
      distance: 9,
      lots: [
        { sku: 'A', lot: 'f-a', qty: 3, expires: '2026-01-15' }
      ]
    }
  ],
  orders: [
    { id: 'low-first', priority: 1, submitted_at: '2026-01-01T09:00:00Z', lines: [{ sku: 'A', qty: 2, single_warehouse: false }] },
    { id: 'bad-middle', priority: 5, submitted_at: '2026-01-01T09:01:00Z', lines: [{ sku: 'B', qty: 1, single_warehouse: false }, { sku: 'C', qty: 1, single_warehouse: false }] },
    { id: 'high-second', priority: 10, submitted_at: '2026-01-01T09:02:00Z', lines: [{ sku: 'A', qty: 5, single_warehouse: false }] },
    { id: 'after-bad', priority: 4, submitted_at: '2026-01-01T09:03:00Z', lines: [{ sku: 'B', qty: 1, single_warehouse: false }] }
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
    id: 'high-second',
    allocations: [
        { sku: 'A', warehouse: 'near', lot: 'n-old', qty: 2 },
        { sku: 'A', warehouse: 'far', lot: 'f-a', qty: 3 }
    ]
  },
  {
    id: 'after-bad',
    allocations: [
      { sku: 'B', warehouse: 'near', lot: 'n-b', qty: 1 }
    ]
  }
]);
assert.deepStrictEqual(parsed.rejected, [
  { id: 'low-first', reason: 'insufficient_stock' },
  { id: 'bad-middle', reason: 'insufficient_stock' }
]);
console.log(JSON.stringify({ ok: true }));
