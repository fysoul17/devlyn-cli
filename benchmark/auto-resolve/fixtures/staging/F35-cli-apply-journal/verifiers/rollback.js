'use strict';
// F35 hidden verifier — the failing op is only discoverable AFTER a
// higher-priority op has added stock: op-12 (priority 8) raises widget
// 10 -> 15, then op-11 (priority 5) requests 20 and fails with
// available 15 — not 10 (pre-batch / file-order would report 10).
// Both files must be byte-for-byte unchanged afterward.

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

fs.writeFileSync(invPath, JSON.stringify({ widget: 10, gadget: 4, gizmo: 0 }, null, 2) + '\n');
fs.writeFileSync(jrnPath, JSON.stringify({ applied: ['op-900'] }, null, 2) + '\n');
const invBefore = fs.readFileSync(invPath, 'utf8');
const jrnBefore = fs.readFileSync(jrnPath, 'utf8');

const inputPath = path.join(os.tmpdir(), `apply-fail-${process.pid}.json`);
fs.writeFileSync(inputPath, JSON.stringify({
  ops: [
    { op_id: 'op-10', sku: 'gadget', delta: 2, priority: 9 },
    { op_id: 'op-11', sku: 'widget', delta: -20, priority: 5 },
    { op_id: 'op-12', sku: 'widget', delta: 5, priority: 8 }
  ]
}));

const cli = path.join(work, 'bin', 'cli.js');
const result = spawnSync('node', [cli, 'apply', '--input', inputPath], {
  cwd: work,
  encoding: 'utf8'
});

let err;
try {
  err = JSON.parse(result.stderr);
} catch {
  err = null;
}

const expectedErr = {
  error: 'insufficient_stock',
  op_id: 'op-11',
  sku: 'widget',
  available: 15,
  requested: 20
};

const filesUnchanged = fs.readFileSync(invPath, 'utf8') === invBefore
  && fs.readFileSync(jrnPath, 'utf8') === jrnBefore;

const ok = result.status === 2
  && result.stdout === ''
  && deepEqual(err, expectedErr)
  && filesUnchanged;

console.log(JSON.stringify({ ok, status: result.status, stdout: result.stdout, err, filesUnchanged }));
process.exit(ok ? 0 : 1);
