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


// Claim K10 (a release retry deletes a peer's lock): the operation that removes the invocation's own lock performs the
// removal and then reports an error (the finding's trigger: an NFS retransmit, or a wrapper that delegates and then
// throws). Between that report and the tree's next action a cooperating peer acquires the now-free lock. A tree that
// answers the reported failure by removing the lock path again, without checking that the lock is still its own,
// deletes the peer's lock, so a third installation can enter beside the peer.
// Trigger: after the owner (this process) has started copying from the source bundle, the first removal
// (rmdirSync/rmSync/unlinkSync) of a path whose name contains "lock" that frees the lock is performed for real; then a
// second real process loads the same product with the same destination and enters installSkillsForCLI('codex'); once
// it has acquired the lock and reached its first source copy it exits, leaving its lock exactly as a live peer holds
// it; then the owner's removal throws EIO. A lock-named removal after which the peer is still busy is passed through
// unchanged (it did not free the lock), so the single fault lands on the removal that freed it.
// Required behaviour (requirement 3: "Release only the current invocation's lock on success or ordinary failure ...
// leave the owner's lock/data intact ... An existing lock is never assumed stale or stolen"): every lock artifact the
// peer created is still present and unchanged after the owner's call returns or throws. If no lock-named removal ever
// frees the lock for the peer, the scenario cannot occur and passes.
const { spawnSync } = require('node:child_process');
const PEER = `
const fs = require('node:fs'); const path = require('node:path'); const vm = require('node:vm');
const { createRequire } = require('node:module');
const [product, root, target, source] = process.argv.slice(1);
const context = vm.createContext({ require: createRequire(product), __dirname: path.join(root, 'bin'), __filename: product,
  process, Buffer, console: { log() {}, error() {} }, setTimeout, clearTimeout });
vm.runInContext(fs.readFileSync(product, 'utf8').split('const args = process.argv.slice(2);')[0] +
  '\\nglobalThis.api={installSkillsForCLI,CLI_TARGETS};', context, { filename: product });
context.api.CLI_TARGETS.codex.skillsDir = target;
const copy = fs.copyFileSync;
fs.copyFileSync = function (src, ...rest) {
  if (String(src).startsWith(source)) { fs.writeSync(1, JSON.stringify({ acquired: true })); process.exit(0); }
  return copy.call(this, src, ...rest);
};
let error = null;
try { context.api.installSkillsForCLI('codex'); } catch (e) { error = String(e && e.message || e).slice(0, 300); }
fs.writeSync(1, JSON.stringify({ acquired: false, error }));
`;
const LOCKY = /lock/i;
// Every lock-named path under the fixture (outside the source bundle) and at the top of os.tmpdir(), with its content.
function lockEntries(f) {
  const result = {};
  function visit(current) {
    let s; try { s = fs.lstatSync(current); } catch (e) { return; }
    if (LOCKY.test(path.basename(current))) result[current] = JSON.stringify(snapshot(current));
    if (s.isDirectory() && !s.isSymbolicLink()) for (const child of fs.readdirSync(current)) visit(path.join(current, child));
  }
  for (const child of fs.readdirSync(f.root)) if (child !== 'config') visit(path.join(f.root, child));
  for (const child of fs.readdirSync(os.tmpdir())) if (LOCKY.test(child)) visit(path.join(os.tmpdir(), child));
  return result;
}
guard(() => {
  const f = fixture();
  const saved = { rmdirSync: fs.rmdirSync, rmSync: fs.rmSync, unlinkSync: fs.unlinkSync, copyFileSync: fs.copyFileSync };
  const trace = [];
  let armed = false, faulted = null, peerArtifacts = null;
  try {
    fs.copyFileSync = function (src, ...rest) {
      if (String(src).startsWith(f.source)) armed = true;
      return saved.copyFileSync.call(this, src, ...rest);
    };
    for (const name of ['rmdirSync', 'rmSync', 'unlinkSync']) {
      fs[name] = function (target, ...rest) {
        const result = saved[name].call(this, target, ...rest);
        if (!armed || faulted || !LOCKY.test(String(target))) return result;
        const before = lockEntries(f);
        const child = spawnSync(process.execPath, ['-e', PEER, PRODUCT, f.root, f.target, f.source], { encoding: 'utf8', timeout: 60000 });
        let peer; try { peer = JSON.parse(child.stdout); } catch (e) { throw new Error('peer failed: ' + (child.stdout + child.stderr).slice(-300)); }
        trace.push({ removal: `${name} ${target}`, peer });
        if (!peer.acquired) return result;
        const after = lockEntries(f);
        peerArtifacts = {};
        for (const [p, content] of Object.entries(after)) if (before[p] !== content) peerArtifacts[p] = content;
        if (Object.keys(peerArtifacts).length === 0) throw new Error('peer acquired but no lock artifact was found');
        faulted = `${name} ${target}`;
        throw ioError('EIO', name.replace('Sync', ''), String(target));
      };
    }
    const owner = { error: null, returned: undefined };
    try { owner.returned = f.run(); } catch (e) { owner.error = String(e && e.message || e).slice(0, 300); }
    finally { Object.assign(fs, saved); }
    if (!armed) throw new Error('the owner never copied from the source bundle');
    if (!faulted) return finish(false, { note: 'no lock-named removal freed the lock for the peer', trace, owner });
    const now = lockEntries(f);
    const lost = Object.keys(peerArtifacts).filter((p) => now[p] !== peerArtifacts[p]);
    finish(lost.length > 0, { faulted, peerArtifacts: Object.keys(peerArtifacts), lost, trace, owner });
  } finally { Object.assign(fs, saved); f.dispose(); }
});
