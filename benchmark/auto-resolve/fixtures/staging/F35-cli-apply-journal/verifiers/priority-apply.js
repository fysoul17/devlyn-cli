'use strict';
// F35 hidden verifier — success path mixing a journaled (replayed) op, unequal
// priorities, and a priority tie. Final quantities are order-independent
// (addition commutes), so the discriminator is the exact `applied` ORDER and
// the journal append order: priority-desc with file-order ties, replayed op
// skipped regardless of its (otherwise failing) fields.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

// Structural equality: object key order is NOT part of the visible contract;
// array order IS. Codex fairness-audit fix (stringify equality made JSON
// property order a hidden oracle narrower than spec.md).
function deepEqual(a, b) {
  if (a === b) return true;
  if (Array.isArray(a) && Array.isArray(b)) {
    return a.length === b.length && a.every((v, i) => deepEqual(v, b[i]));
  }
  if (a && b && typeof a === 'object' && typeof b === 'object' && !Array.isArray(a) && !Array.isArray(b)) {
    const ka = Object.keys(a).sort();
    const kb = Object.keys(b).sort();
    return deepEqual(ka, kb) && ka.every((k) => deepEqual(a[k], b[k]));
  }
  return false;
}

const work = process.env.BENCH_WORKDIR;
const invPath = path.join(work, 'data', 'inventory.json');
const jrnPath = path.join(work, 'data', 'journal.json');

// Reset seeds so this verifier is order-independent from other commands.
fs.writeFileSync(invPath, JSON.stringify({ widget: 10, gadget: 4, gizmo: 0 }, null, 2) + '\n');
fs.writeFileSync(jrnPath, JSON.stringify({ applied: ['op-900'] }, null, 2) + '\n');

const inputPath = path.join(os.tmpdir(), `apply-ok-${process.pid}.json`);
fs.writeFileSync(inputPath, JSON.stringify({
  ops: [
    { op_id: 'op-1', sku: 'widget', delta: -4, priority: 1 },
    { op_id: 'op-900', sku: 'widget', delta: -9, priority: 9 },
    { op_id: 'op-2', sku: 'widget', delta: -5, priority: 5 },
    { op_id: 'op-3', sku: 'gadget', delta: -4, priority: 5 },
    { op_id: 'op-4', sku: 'widget', delta: 3, priority: 0 }
  ]
}));

const cli = path.join(work, 'bin', 'cli.js');
const result = spawnSync('node', [cli, 'apply', '--input', inputPath], {
  cwd: work,
  encoding: 'utf8'
});

let out;
try {
  out = JSON.parse(result.stdout);
} catch {
  out = null;
}

const expected = {
  applied: ['op-2', 'op-3', 'op-1', 'op-4'],
  skipped: ['op-900'],
  inventory: { widget: 4, gadget: 0, gizmo: 0 }
};

let inv; let jrn;
try {
  inv = JSON.parse(fs.readFileSync(invPath, 'utf8'));
  jrn = JSON.parse(fs.readFileSync(jrnPath, 'utf8'));
} catch {
  inv = null; jrn = null;
}

const ok = result.status === 0
  && result.stderr === ''
  && deepEqual(out, expected)
  && deepEqual(inv, expected.inventory)
  && deepEqual(jrn, { applied: ['op-900', 'op-2', 'op-3', 'op-1', 'op-4'] });

console.log(JSON.stringify({ ok, status: result.status, stderr: result.stderr, out, inv, jrn }));
process.exit(ok ? 0 : 1);
