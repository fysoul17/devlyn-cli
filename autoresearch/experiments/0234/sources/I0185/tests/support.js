const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const { createRequire } = require('node:module');

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
function fixture(product = path.resolve('bin/devlyn.js'), fresh = false) {
  const root = fs.mkdtempSync(path.join(process.env.TMPDIR || os.tmpdir(), 'install-check-'));
  const source = path.join(root, 'config/skills');
  const target = path.join(root, 'agent/skills');
  const names = ['devlyn:resolve', 'devlyn:ideate', 'devlyn:design-ui', 'devlyn:engines', 'devlyn:queue', '_shared'];
  const write = (relative, text, mode) => { const p = path.join(root, relative); fs.mkdirSync(path.dirname(p), { recursive: true }); fs.writeFileSync(p, text, mode ? {mode} : undefined); };
  for (const name of names) {
    write('config/skills/' + name + '/SKILL.md', '# ' + name + '\n${CLAUDE_SKILL_DIR:-__DEVLYN_SKILL_DIR__}\n');
    write('config/skills/' + name + '/references/nested.md', 'new ' + name);
    if (!fresh) write('agent/skills/' + name + '/old.txt', 'old ' + name, 0o640);
  }
  if (!fresh) {
    write('agent/skills/.devlyn-install.json', '{"old":"marker"}\n', 0o600);
    write('agent/skills/custom/SKILL.md', 'user skill');
    write('agent/skills/devlyn:auto-resolve/old.md', 'deprecated skill');
    write('agent/commands/devlyn.handoff.md', 'deprecated command', 0o640);
    write('outside.txt', 'unrelated symlink target');
    fs.symlinkSync(path.join(root, 'outside.txt'), path.join(target, 'custom/link'));
  }
  const api = load(product, root, target);
  return {root, source, target, names, write, api,
    run: () => api.installSkillsForCLI('codex'), dispose: () => fs.rmSync(root, {recursive:true, force:true})};
}
function load(product, root, target) {
  const requireProduct = createRequire(product);
  const context = vm.createContext({ require: requireProduct, __dirname: path.join(root, 'bin'), __filename: product,
    process, Buffer, console: {log(){}, error(){}}, setTimeout, clearTimeout });
  const code = fs.readFileSync(product, 'utf8').split('const args = process.argv.slice(2);')[0];
  vm.runInContext(code + '\nglobalThis.api={installSkillsForCLI,CLI_TARGETS};', context, {filename: product});
  context.api.CLI_TARGETS.codex.skillsDir = target;
  context.api.CLI_TARGETS.omp.skillsDir = path.join(root, 'different/skills');
  return context.api;
}
function injected(method, predicate, action, body) {
  const original = fs[method]; let fired = false;
  fs[method] = function(...args) {
    if (!fired && predicate(...args)) { fired = true; action(...args); }
    return original.apply(this, args);
  };
  try { body(); } finally { fs[method] = original; }
  return fired;
}
module.exports = {fixture, snapshot, injected, load};
