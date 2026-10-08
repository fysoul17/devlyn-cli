'use strict';
// Shared I0185 fixture (identical in every I0185 witness). It mirrors the supplied tests/support.js: a source bundle,
// a prior installation with marker, a user skill holding an unrelated symlink, a deprecated skill dir and a deprecated
// command, and the product's installSkillsForCLI loaded in a VM with source/destination redirected to the fixture.
// Run from the tree root (/work). Exit 1 = the claimed defect reproduces, 0 = the tree behaves correctly, 2 = witness error.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const { createRequire } = require('node:module');

const PRODUCT = path.resolve('bin/devlyn.js');
const NAMES = ['devlyn:resolve', 'devlyn:ideate', 'devlyn:design-ui', 'devlyn:engines', 'devlyn:queue', '_shared'];
const BUSY = /busy|lock|progress/i;

function snapshot(root) {
  const result = {};
  function visit(current, relative) {
    const s = fs.lstatSync(current);
    result[relative] = s.isSymbolicLink() ? ['link', fs.readlinkSync(current)] :
      s.isDirectory() ? ['dir', s.mode & 0o777] : ['file', s.mode & 0o777, fs.readFileSync(current).toString('base64')];
    if (s.isDirectory()) for (const child of fs.readdirSync(current).sort()) visit(path.join(current, child), path.join(relative, child));
  }
  if (fs.existsSync(root)) visit(root, '.');
  return result;
}

function write(root, relative, text, mode) {
  const p = path.join(root, relative);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, text, mode ? { mode } : undefined);
}

function load(root, target) {
  const context = vm.createContext({ require: createRequire(PRODUCT), __dirname: path.join(root, 'bin'), __filename: PRODUCT,
    process, Buffer, console: { log() {}, error() {} }, setTimeout, clearTimeout });
  const code = fs.readFileSync(PRODUCT, 'utf8').split('const args = process.argv.slice(2);')[0];
  vm.runInContext(code + '\nglobalThis.api={installSkillsForCLI,CLI_TARGETS};', context, { filename: PRODUCT });
  context.api.CLI_TARGETS.codex.skillsDir = target;
  context.api.CLI_TARGETS.omp.skillsDir = path.join(root, 'different/skills');
  return context.api;
}

// skillsReal: place the real skills directory there and make <root>/agent/skills a symlink to it.
function fixture({ fresh = false, skillsReal = null } = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'witness-i0185-'));
  const source = path.join(root, 'config/skills');
  const target = path.join(root, 'agent/skills');
  for (const name of NAMES) {
    write(root, 'config/skills/' + name + '/SKILL.md', '# ' + name + '\n${CLAUDE_SKILL_DIR:-__DEVLYN_SKILL_DIR__}\n');
    write(root, 'config/skills/' + name + '/references/nested.md', 'new ' + name);
  }
  if (!fresh) {
    if (skillsReal) {
      fs.mkdirSync(path.join(root, 'agent'), { recursive: true });
      fs.mkdirSync(skillsReal, { recursive: true });
      fs.symlinkSync(skillsReal, target);
    }
    for (const name of NAMES) write(root, 'agent/skills/' + name + '/old.txt', 'old ' + name, 0o640);
    write(root, 'agent/skills/.devlyn-install.json', '{"old":"marker"}\n', 0o600);
    write(root, 'agent/skills/custom/SKILL.md', 'user skill');
    write(root, 'agent/skills/devlyn:auto-resolve/old.md', 'deprecated skill');
    write(root, 'agent/commands/devlyn.handoff.md', 'deprecated command', 0o640);
    write(root, 'outside.txt', 'unrelated symlink target');
    fs.symlinkSync(path.join(root, 'outside.txt'), path.join(target, 'custom/link'));
  }
  const api = load(root, target);
  return { root, source, target, api, run: () => api.installSkillsForCLI('codex'),
    dispose: () => fs.rmSync(root, { recursive: true, force: true }) };
}

// The new installation is complete at `skillsDir` (followed if it is a symlink): every selected skill replaced,
// marker schema 1, deprecated paths gone, the user skill (with its symlink) untouched. Returns a list of problems.
function installedProblems(f, skillsDir, userBefore) {
  const problems = [];
  for (const name of NAMES) {
    const dir = path.join(skillsDir, name);
    if (!fs.existsSync(path.join(dir, 'references/nested.md'))) problems.push(`${name}: new content missing`);
    if (fs.existsSync(path.join(dir, 'old.txt'))) problems.push(`${name}: stale old.txt kept`);
  }
  try {
    if (JSON.parse(fs.readFileSync(path.join(skillsDir, '.devlyn-install.json'), 'utf8')).schemaVersion !== 1) problems.push('marker schema');
  } catch (error) { problems.push('marker unreadable: ' + error.code); }
  if (fs.existsSync(path.join(skillsDir, 'devlyn:auto-resolve'))) problems.push('deprecated skill dir kept');
  if (fs.existsSync(path.join(f.root, 'agent/commands/devlyn.handoff.md'))) problems.push('deprecated command kept');
  if (userBefore && JSON.stringify(snapshot(path.join(skillsDir, 'custom'))) !== JSON.stringify(userBefore)) problems.push('user skill changed');
  return problems;
}

function ioError(code, syscall, target) {
  const error = new Error(`${code}: injected ${syscall} failure, '${target}'`);
  error.code = code; error.syscall = syscall; error.path = target;
  return error;
}

function finish(reproduced, detail) {
  console.log(JSON.stringify({ reproduced, ...detail }));
  process.exitCode = reproduced ? 1 : 0;
}

function guard(body) {
  try { body(); } catch (error) {
    console.log('WITNESS ERROR: ' + (error && error.stack || error));
    process.exitCode = 2;
  }
}

// Claim K7 (environment-dependent lock location): the lock is placed under os.tmpdir(), which follows each process's
// TMPDIR, so two cooperating processes installing into the same destination with different (existing) TMPDIR values
// take different locks and both proceed.
// Trigger (two real processes, no timing assumptions): this process (owner, TMPDIR=<tmpA>) installs into the fixture;
// on its first copy from the source bundle -- while it holds its lock -- it synchronously runs a second Node process
// (contender, TMPDIR=<tmpB>, same product, same destination) and waits for its result.
// Required behaviour (requirement 3: "Exclude simultaneous cooperating installations to the same destination with an
// exclusive filesystem lock ... Another process ... must fail promptly with a clear busy error and leave the owner's
// lock/data intact"): the contender fails busy, the installation is unchanged by it, and the owner returns 6.
const { spawnSync } = require('node:child_process');

const CONTENDER = `
const fs = require('node:fs'); const path = require('node:path'); const vm = require('node:vm');
const { createRequire } = require('node:module');
const [product, root, target] = process.argv.slice(1);
const context = vm.createContext({ require: createRequire(product), __dirname: path.join(root, 'bin'), __filename: product,
  process, Buffer, console: { log() {}, error() {} }, setTimeout, clearTimeout });
vm.runInContext(fs.readFileSync(product, 'utf8').split('const args = process.argv.slice(2);')[0] +
  '\\nglobalThis.api={installSkillsForCLI,CLI_TARGETS};', context, { filename: product });
context.api.CLI_TARGETS.codex.skillsDir = target;
const result = { tmpdir: require('node:os').tmpdir(), error: null, returned: undefined };
try { result.returned = context.api.installSkillsForCLI('codex'); } catch (e) { result.error = String(e && e.message || e).slice(0, 300); }
process.stdout.write(JSON.stringify(result));
`;

guard(() => {
  const f = fixture();
  const tmpA = fs.mkdtempSync(path.join(os.tmpdir(), 'witness-tmpdir-a-'));
  const tmpB = fs.mkdtempSync(path.join(os.tmpdir(), 'witness-tmpdir-b-'));
  const savedTmp = process.env.TMPDIR;
  const copy = fs.copyFileSync;
  try {
    process.env.TMPDIR = tmpA;
    if (os.tmpdir() !== tmpA) throw new Error('TMPDIR not honoured by os.tmpdir()');
    let contender = null;
    fs.copyFileSync = function (src, ...rest) {
      if (!contender && String(src).startsWith(f.source)) {
        const before = JSON.stringify(snapshot(path.join(f.root, 'agent')));
        const child = spawnSync(process.execPath, ['-e', CONTENDER, PRODUCT, f.root, f.target],
          { env: { ...process.env, TMPDIR: tmpB }, encoding: 'utf8', timeout: 120000 });
        if (child.status !== 0 || !child.stdout) throw new Error('contender process failed: ' + child.status + ' ' + String(child.stderr).slice(-300));
        contender = JSON.parse(child.stdout);
        contender.unchanged = JSON.stringify(snapshot(path.join(f.root, 'agent'))) === before;
      }
      return copy.call(this, src, ...rest);
    };
    let ownerError = null, ownerReturned;
    try { ownerReturned = f.run(); } catch (e) { ownerError = String(e && e.message || e).slice(0, 300); }
    finally { fs.copyFileSync = copy; }
    if (!contender) throw new Error('the owner installation never copied from the source bundle');
    const ok = contender.error !== null && BUSY.test(contender.error) && contender.unchanged && ownerError === null && ownerReturned === 6;
    finish(!ok, { contender, ownerError, ownerReturned });
  } finally {
    fs.copyFileSync = copy;
    if (savedTmp === undefined) delete process.env.TMPDIR; else process.env.TMPDIR = savedTmp;
    fs.rmSync(tmpA, { recursive: true, force: true });
    fs.rmSync(tmpB, { recursive: true, force: true });
    f.dispose();
  }
});
