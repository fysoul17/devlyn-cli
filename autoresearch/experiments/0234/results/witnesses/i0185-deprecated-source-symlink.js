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


// Claim K11 (deprecated cleanup follows a symlinked parent into the source bundle): the CLI's commands directory
// beside skills/ is a preexisting user symlink into a selected source skill, and that source skill contains a file named
// like the retired command. The tree's deprecated-path handling removes (or moves into its backup and then disposes)
// <agent>/commands/devlyn.handoff.md through the symlink, which deletes the real source file.
// Trigger: the standard fixture, with <root>/agent/commands replaced by a symlink to <root>/config/skills/devlyn:resolve
// and config/skills/devlyn:resolve/devlyn.handoff.md added. No fault and no concurrent writer.
// Required behaviour (requirement 1: "Preserve unrelated files, user-installed skills and every source file ...
// Preserve symlinks in unrelated user content without following or rewriting their targets"; requirement 4: "Preserve
// original content outside the owned paths"): whether the call returns or throws, the source bundle (config/skills)
// is byte-for-byte unchanged and the agent/commands symlink still exists with the same target.
guard(() => {
  const f = fixture();
  try {
    const resolveSource = path.join(f.source, 'devlyn:resolve');
    write(f.root, 'config/skills/devlyn:resolve/devlyn.handoff.md', 'source file named like the retired command\n', 0o644);
    const commands = path.join(f.root, 'agent/commands');
    fs.rmSync(commands, { recursive: true });
    fs.symlinkSync(resolveSource, commands);
    const sourceBefore = JSON.stringify(snapshot(f.source));
    const owner = { error: null, returned: undefined };
    try { owner.returned = f.run(); } catch (e) { owner.error = String(e && e.message || e).slice(0, 300); }
    const sourceKept = JSON.stringify(snapshot(f.source)) === sourceBefore;
    const handoffKept = fs.existsSync(path.join(resolveSource, 'devlyn.handoff.md'));
    let link = null; try { link = fs.readlinkSync(commands); } catch (e) { link = 'missing: ' + e.code; }
    const linkKept = link === resolveSource;
    finish(!(sourceKept && linkKept), { sourceKept, handoffKept, link, owner });
  } finally { f.dispose(); }
});
