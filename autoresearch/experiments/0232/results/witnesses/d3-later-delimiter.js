'use strict';
// Shared D3 harness (identical in every D3 witness). A real parent program built on the tree's Commander dispatches
// the executable subcommand "child" (isDefault, alias "c") to a real child program, also built on the tree's
// Commander, with one option (--child) and a variadic operand; the child prints its raw argv and what it parsed.
// Run from the tree root (/work). Exit 1 = the claimed defect reproduces, 0 = the tree behaves correctly, 2 = witness error.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { pathToFileURL } = require('node:url');

const INDEX = pathToFileURL(path.resolve('index.js')).href;

function programs() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'witness-d3-'));
  fs.writeFileSync(path.join(dir, 'child.mjs'), `import { Command } from ${JSON.stringify(INDEX)};
const program = new Command().name('child').option('--child').argument('[values...]')
  .action((values) => { process.stdout.write(JSON.stringify({ argv: process.argv.slice(2), values, opts: program.opts() })); });
program.parse();
`);
  fs.writeFileSync(path.join(dir, 'parent.mjs'), `import { Command } from ${JSON.stringify(INDEX)};
const program = new Command().name('parent').option('--parent <value>');
program.command('child', 'executable child', { executableFile: ${JSON.stringify(path.join(dir, 'child.mjs'))}, isDefault: true }).alias('c');
program.parse();
`);
  return dir;
}

// Runs `parent <args>` and returns what the real spawned child received and parsed.
function run(dir, args) {
  const r = spawnSync(process.execPath, [path.join(dir, 'parent.mjs'), ...args], { encoding: 'utf8', timeout: 20000, killSignal: 'SIGKILL' });
  if (r.error) throw new Error('parent did not run: ' + r.error);
  let child = null;
  try { child = JSON.parse(r.stdout); } catch (e) { child = null; }
  return { args, status: r.status, child, stderr: (r.stderr || '').trim().slice(-300) };
}

const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

function finish(reproduced, detail) {
  console.log(JSON.stringify({ reproduced, ...detail }));
  process.exitCode = reproduced ? 1 : 0;
}

function guard(body) {
  const dir = programs();
  try { body(dir); } catch (error) {
    console.log('WITNESS ERROR: ' + (error && error.stack || error));
    process.exitCode = 2;
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
}

// Claim J2: after dispatch the first delimiter is lost while a later "--" survives, so the later one becomes the child's
// end-of-options marker: `parent child before -- after -- --tail` reaches the child as [before, after, --, --tail].
// Required behaviour (obligation 2): operands keep their order around the first delimiter and later "--" tokens stay
// literal: raw argv [before, --, after, --, --tail], operands [before, after, --, --tail], exit 0.
guard((dir) => {
  const r = run(dir, ['child', 'before', '--', 'after', '--', '--tail']);
  const ok = r.status === 0 && r.child !== null && same(r.child.argv, ['before', '--', 'after', '--', '--tail']) &&
    same(r.child.values, ['before', 'after', '--', '--tail']) && same(r.child.opts, {});
  finish(!ok, { run: r });
});
