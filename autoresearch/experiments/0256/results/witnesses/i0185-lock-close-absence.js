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

// Claim K8 (initial absence lost after a lock-descriptor failure): with no prior installation, one ordinary failure of
// closeSync on the descriptor of the invocation's own lock (the descriptor is closed, then EIO is reported; every later
// operation succeeds) makes the installation fail but leaves the lock file -- and with it the newly created skills
// directory -- behind.
// Trigger: fresh fixture (no agent/ directory at all); the first closeSync of a descriptor opened on a path whose name
// contains "lock" (inside the fixture or under the system temp directory) fails once as described. A tree that never
// closes a descriptor opened on its lock is reported as not applicable and passes.
// Required behaviour (requirement 2: "An initially absent skills directory must again be absent after failure";
// requirement 4: remove task-created lock debris after successful recovery): if the call fails, the skills directory
// does not exist and the lock path no longer exists. (A call that instead completes must return 6.)
guard(() => {
  const f = fixture({ fresh: true });
  const originals = {};
  const patch = (method, wrapper) => { originals[method] = fs[method]; fs[method] = wrapper(originals[method]); };
  const lockFds = new Map();
  let fired = null;
  try {
    if (fs.existsSync(path.join(f.root, 'agent'))) throw new Error('fresh fixture unexpectedly has agent/');
    patch('openSync', (real) => function (target, ...rest) {
      const fd = real.call(this, target, ...rest);
      const p = typeof target === 'string' ? target : String(target);
      if (/lock/i.test(path.basename(p))) lockFds.set(fd, p);
      return fd;
    });
    patch('closeSync', (real) => function (fd, ...rest) {
      if (!fired && lockFds.has(fd)) {
        real.call(this, fd, ...rest);
        const p = lockFds.get(fd);
        fired = { method: 'closeSync', path: p.startsWith(f.root) ? '<fixture>' + p.slice(f.root.length) : p, absolute: p };
        throw ioError('EIO', 'close', 'fd ' + fd);
      }
      return real.call(this, fd, ...rest);
    });
    let error = null, returned;
    try { returned = f.run(); } catch (e) { error = String(e && e.message || e).slice(0, 300); }
    finally { for (const method of Object.keys(originals)) fs[method] = originals[method]; }
    if (!fired) return finish(false, { applicable: false, error, returned });
    const skillsDirPresent = fs.existsSync(f.target);
    const lockLeft = fs.existsSync(fired.absolute);
    delete fired.absolute;
    const ok = error === null ? returned === 6 : !skillsDirPresent && !lockLeft;
    finish(!ok, { applicable: true, fired, error, returned, skillsDirPresent, lockLeft,
      agentLeft: fs.existsSync(path.join(f.root, 'agent')) ? Object.keys(snapshot(path.join(f.root, 'agent'))) : null });
  } finally {
    for (const method of Object.keys(originals)) fs[method] = originals[method];
    f.dispose();
  }
});
