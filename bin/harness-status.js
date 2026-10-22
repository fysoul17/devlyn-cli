const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const { Lexer } = require('marked');
const { managedBody } = require('./instructions');
const { ENGINE_IDS } = require('./engines');
const templates = require('./instruction-templates.json');
const history = require('./skill-history.json');
const { fingerprint, gitEnvironment } = require('./skill-ownership');
const { verifyRelease, sha256, physicalRoot, fail, options } = require('./release');

function git(root, args, encoding = 'utf8') {
  return spawnSync('git', ['-C', root, ...args], {
    env: { ...gitEnvironment(), GIT_OPTIONAL_LOCKS: '0' }, encoding, maxBuffer: 8 * 1024 * 1024,
  });
}
function gitOutput(root, args) {
  const result = git(root, args);
  if (result.error || result.status !== 0) fail('repository-unreadable', { detail: result.error?.message || result.stderr.trim() });
  return result.stdout.trim();
}
function repositoryIdentity(project) {
  const result = git(project, ['rev-parse', '--show-toplevel']);
  if (result.error?.code === 'ENOENT' || (result.status === 128 && result.stderr.includes('not a git repository'))) return null;
  if (result.error || result.status !== 0) fail('repository-unreadable', { detail: result.error?.message || result.stderr.trim() });
  const root = fs.realpathSync(result.stdout.trim());
  const commonGitDir = fs.realpathSync(gitOutput(root, ['rev-parse', '--path-format=absolute', '--git-common-dir']));
  // Committed identity survives missing/edited files and linked worktrees.
  const pkg = git(root, ['show', 'HEAD:package.json']);
  const cli = git(root, ['cat-file', '-e', 'HEAD:bin/devlyn.js']);
  let sourceRepository = false;
  if (pkg.status === 0 && cli.status === 0) {
    try { sourceRepository = JSON.parse(pkg.stdout).name === 'devlyn-cli'; }
    catch (error) { fail('repository-unreadable', { detail: error.message }); }
  }
  return { root, commonGitDir, sourceRepository };
}

function inspectInstruction(text, template, name) {
  const normalized = text.replace(/^\uFEFF/, '').replace(/\r\n/g, '\n');
  const body = managedBody(template);
  const current = sha256(body);
  const tokens = new Lexer({ gfm: false }).lex(normalized);
  const hasMarkers = tokens.some((token) => token.type === 'html' && /^<!-- devlyn:instructions:(?:begin|end)/.test(token.raw));
  const starts = [...normalized.matchAll(/^<!-- devlyn:instructions:begin sha256=([a-f0-9]{64}) -->\n/gm)];
  const ends = [...normalized.matchAll(/^<!-- devlyn:instructions:end -->(?:\n|$)/gm)];
  if (hasMarkers) {
    if (starts.length !== 1 || ends.length !== 1 || ends[0].index < starts[0].index
        || normalized.split('<!-- devlyn:instructions:begin').length !== 2
        || normalized.split('<!-- devlyn:instructions:end').length !== 2) return { ownership: 'modified', blockSha256: null };
    const previous = normalized.slice(starts[0].index + starts[0][0].length, ends[0].index);
    const hash = sha256(previous);
    if (hash !== starts[0][1]) return { ownership: 'modified', blockSha256: hash };
    if (hash === current) return { ownership: 'current', blockSha256: hash };
    const raw = previous.replace(/^Project-specific instructions outside this managed block take precedence over these defaults\.\n\n/, '');
    const known = (templates[name] || []).some((entry) => entry.sha256 === sha256(raw));
    return { ownership: known ? 'outdated' : 'modified', blockSha256: hash };
  }
  if (normalized === template.replace(/\r\n/g, '\n')) return { ownership: 'current', blockSha256: current };
  const known = (templates[name] || []).some((entry) => entry.sha256 === sha256(normalized));
  return { ownership: known ? 'outdated' : 'unowned', blockSha256: null };
}

function requirements() {
  const [major, minor] = process.versions.node.split('.').map(Number);
  const nodeSupported = (major === 20 && minor >= 17) || (major === 22 && minor >= 13)
    || (major === 23 && minor >= 5) || major > 23;
  const node = { name: 'node', required: true, available: nodeSupported, version: process.versions.node,
    reasons: nodeSupported ? [] : [{ code: 'requirement-version', params: { name: 'node' } }] };
  const probes = [
    ['python', true, 'python3', ['-B', '--version']],
    ['git', true, 'git', ['--version']],
    ['git-bash', process.platform === 'win32', 'bash', ['--version']],
    ['gh', false, 'gh', ['--version']],
  ];
  return [node, ...probes.map(([name, required, binary, argv]) => {
    const result = spawnSync(binary, argv, { encoding: 'utf8', timeout: 5000, env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' } });
    const output = (result.stdout || result.stderr || '').trim();
    const match = output.match(/\b(\d+)\.(\d+)(?:\.\d+)?/);
    let available = !result.error && result.status === 0 && Boolean(match);
    if (name === 'python' && available) available = Number(match[1]) > 3 || (Number(match[1]) === 3 && Number(match[2]) >= 11);
    if (name === 'git-bash' && required && available) available = /mingw|msys/i.test(output);
    return { name, required, available, version: match?.[0] || null,
      reasons: available ? [] : [{ code: 'requirement-unavailable', params: { name } }] };
  })];
}

function harnessStatus(project, { releaseRoot = path.resolve(__dirname, '..') } = {}) {
  const release = verifyRelease(releaseRoot, { npmInstall: true }).release;
  project = physicalRoot(project);
  const repository = repositoryIdentity(project);
  const root = repository?.root || project;
  const instructions = [];
  const ownership = [];
  for (const name of ['CLAUDE.md', 'AGENTS.md']) {
    const file = path.join(root, name);
    const stat = fs.lstatSync(file, { throwIfNoEntry: false });
    if (!stat) continue;
    let inspected = { ownership: 'unowned', blockSha256: null };
    let committed = false;
    const reasons = [];
    if (stat.isFile() && stat.nlink === 1) {
      const bytes = fs.readFileSync(file);
      let text;
      try { text = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes); }
      catch (error) {
        if (!(error instanceof TypeError)) throw error;
        reasons.push({ code: 'instruction-encoding', params: { path: file } });
      }
      if (text !== undefined) inspected = inspectInstruction(text, fs.readFileSync(path.join(release.root, name), 'utf8'), name);
      if (repository) {
        const head = git(root, ['show', `HEAD:${name}`], 'buffer');
        committed = head.status === 0 && head.stdout.equals(bytes);
      }
    } else reasons.push({ code: 'outside-root-link-or-special-file', params: { path: file } });
    // Native trust/config/loading is established by CLI-3. A familiar filename is insufficient.
    instructions.push({ path: file, committed, ...inspected, applicableEngines: [], applicability: 'unknown' });
    ownership.push({ path: file, kind: 'instructions', proof: inspected.ownership === 'current' ? 'current'
      : inspected.ownership === 'outdated' ? 'historical' : 'none', reasons });
  }
  const current = new Map();
  for (const agent of ['.agents', '.claude']) {
    for (const name of ['devlyn-ideate', 'devlyn-engines', '_shared']) {
      const file = path.join(root, agent, 'skills', name);
      // Do not traverse an ancestor link just to discover an installation.
      const ancestors = [path.join(root, agent), path.join(root, agent, 'skills')];
      if (ancestors.some((dir) => {
        const stat = fs.lstatSync(dir, { throwIfNoEntry: false });
        return stat && !stat.isDirectory();
      })) {
        if (!ownership.some((entry) => entry.path === ancestors[0])) ownership.push({ path: ancestors[0], kind: 'core-skill',
          proof: 'none', reasons: [{ code: 'outside-root-link-or-special-file', params: { path: ancestors[0] } }] });
        continue;
      }
      if (!fs.lstatSync(file, { throwIfNoEntry: false })) continue;
      let proof = 'none';
      const reasons = [];
      try {
        const hash = fingerprint(file);
        if (!current.has(name)) current.set(name, fingerprint(path.join(release.root, 'config/skills', name)));
        if (hash === current.get(name)) proof = 'current';
        else if ((history.skills[name] || []).includes(hash)) proof = 'historical';
      } catch (error) {
        reasons.push({ code: 'ownership-unverifiable', params: { path: file, detail: error.message } });
      }
      ownership.push({ path: file, kind: 'core-skill', proof, reasons });
    }
  }
  // Pure queue inspection and effective engine configuration belong to CLI-2/CLI-3.
  return { release, repository, instructions, requirements: requirements(), ownership };
}

function statusCommand(args) {
  const opts = options(args, { project: { type: 'string' }, engine: { type: 'string' }, 'context-file': { type: 'string' } });
  if (!opts.project) fail('invalid-arguments', { argument: '--project' }, 2);
  if (opts.engine && !ENGINE_IDS.includes(opts.engine)) {
    fail('invalid-arguments', { argument: '--engine' }, 2);
  }
  const status = harnessStatus(opts.project);
  if (opts['context-file']) {
    const { readContext, planActivation } = require('./harness-activation');
    const context = readContext(opts['context-file']);
    if ((opts.engine && opts.engine !== context.engine) || physicalRoot(context.cwd) !== physicalRoot(opts.project)) {
      fail('invalid-arguments', { argument: 'status context must match project and engine' }, 2);
    }
    status.engines = [planActivation(status.release.root, context).channels];
  }
  return status;
}

module.exports = { harnessStatus, statusCommand, repositoryIdentity, inspectInstruction };
