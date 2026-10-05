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

// Claim K1 (cross-filesystem rename): staging/backup renames cross the skills-directory boundary, so installation
// always fails when the skills directory lives on a different filesystem than its parent, although the original
// in-place installer succeeded there. Two realisations of the findings' trigger:
//   symlink: <root>/agent/skills is a symlink to a directory on another filesystem (/dev/shm, a tmpfs in the cell
//            image; the fixture lives on the overlay /tmp) -- real kernel EXDEV, no injection;
//   mount:   <root>/agent/skills is a mount point, simulated by making every rename between the inside and the
//            outside of that directory fail with EXDEV, as the kernel does across a mount boundary.
// Required behaviour: installSkillsForCLI still returns 6 and leaves a complete new installation.
const OTHER_FS = process.env.WITNESS_OTHER_FS || '/dev/shm';

function attempt(f) {
  const user = snapshot(path.join(f.target, 'custom'));
  let returned, error = null;
  try { returned = f.run(); } catch (e) { error = String(e && e.message || e).slice(0, 300); }
  const problems = error === null ? installedProblems(f, f.target, user) : [];
  return { returned, error, problems, ok: error === null && returned === 6 && problems.length === 0 };
}

guard(() => {
  const scenarios = {};
  {
    const real = fs.mkdtempSync(path.join(OTHER_FS, 'witness-skills-'));
    const f = fixture({ skillsReal: path.join(real, 'skills') });
    try {
      if (fs.statSync(f.root).dev === fs.statSync(real).dev) throw new Error('fixture and skills directory share a filesystem');
      scenarios.symlink = attempt(f);
    } finally { f.dispose(); fs.rmSync(real, { recursive: true, force: true }); }
  }
  {
    const f = fixture();
    const mount = fs.realpathSync(f.target);
    // Physical location of a directory entry (the final component is not followed, as rename does not follow it).
    const physical = (p) => {
      const abs = path.resolve(String(p));
      let dir = path.dirname(abs);
      const rest = [path.basename(abs)];
      while (!fs.existsSync(dir)) { rest.unshift(path.basename(dir)); dir = path.dirname(dir); }
      return path.join(fs.realpathSync(dir), ...rest);
    };
    const within = (p) => { const q = physical(p); return q === mount || q.startsWith(mount + path.sep); };
    const rename = fs.renameSync;
    let crossings = 0;
    fs.renameSync = function (from, to, ...rest) {
      if (within(from) !== within(to)) { crossings++; throw ioError('EXDEV', 'rename', `${from}' -> '${to}`); }
      return rename.call(this, from, to, ...rest);
    };
    try { scenarios.mount = attempt(f); scenarios.mount.crossings = crossings; }
    finally { fs.renameSync = rename; f.dispose(); }
  }
  finish(Object.values(scenarios).some((s) => !s.ok), { scenarios });
});
