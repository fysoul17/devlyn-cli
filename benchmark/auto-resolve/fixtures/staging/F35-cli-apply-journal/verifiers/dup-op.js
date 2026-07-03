'use strict';
// F35 hidden verifier — an op_id duplicated WITHIN the input file is a
// validation error (whole file rejected, nothing changes), distinct from a
// journal replay which is a per-op skip. Exit 2, one JSON error object on
// stderr, no stdout, both files untouched.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const work = process.env.BENCH_WORKDIR;
const invPath = path.join(work, 'data', 'inventory.json');
const jrnPath = path.join(work, 'data', 'journal.json');

fs.writeFileSync(invPath, JSON.stringify({ widget: 10, gadget: 4, gizmo: 0 }, null, 2) + '\n');
fs.writeFileSync(jrnPath, JSON.stringify({ applied: ['op-900'] }, null, 2) + '\n');
const invBefore = fs.readFileSync(invPath, 'utf8');
const jrnBefore = fs.readFileSync(jrnPath, 'utf8');

const inputPath = path.join(os.tmpdir(), `apply-dup-${process.pid}.json`);
fs.writeFileSync(inputPath, JSON.stringify({
  ops: [
    { op_id: 'op-20', sku: 'widget', delta: -1, priority: 3 },
    { op_id: 'op-21', sku: 'gadget', delta: 1, priority: 2 },
    { op_id: 'op-20', sku: 'gizmo', delta: 2, priority: 1 }
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

const filesUnchanged = fs.readFileSync(invPath, 'utf8') === invBefore
  && fs.readFileSync(jrnPath, 'utf8') === jrnBefore;

const ok = result.status === 2
  && result.stdout === ''
  && err !== null
  && err.error === 'invalid_input'
  && typeof err.reason === 'string'
  && filesUnchanged;

console.log(JSON.stringify({ ok, status: result.status, stdout: result.stdout, err, filesUnchanged }));
process.exit(ok ? 0 : 1);
