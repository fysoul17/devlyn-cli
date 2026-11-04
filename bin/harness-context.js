'use strict';
// What `devlyn run` hands the activation planner for one fresh terminal launch: the selected
// release and an ActivationContext built the way the Devlyn app builds it (docs/harness-run.md).
// Every read that fails stops the launch; nothing here falls back to a raw engine start.
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const readline = require('readline');
const { spawn, spawnSync } = require('child_process');
const { verifyRelease, materializeRelease, fail } = require('./release');

const ENGINES = Object.freeze(['claude', 'codex', 'omp']);
const READ_MS = 6000;
const CODEX_READ_MS = 10000;
const object = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);

// Arguments `devlyn run` cannot plan around yet: each would make the launch other than the fresh
// session the plan describes, or change settings the plan merges without the merge seeing them.
const REFUSED = Object.freeze({
  claude: { continuation: ['-c', '--continue', '-r', '--resume', '--fork-session', '--from-pr'],
    settings: ['--settings', '--setting-sources'] },
  codex: { continuation: [], settings: ['-p', '--profile'] },
  omp: { continuation: ['-c', '--continue', '-r', '--resume', '--restore', '--from-claude', '--from-codex'],
    settings: ['--config', '--profile'] },
});
// Codex global and `exec` options that take a value, so positional detection skips their value.
const CODEX_VALUE_FLAGS = new Set(['-c', '--config', '-m', '--model', '-p', '--profile', '-s', '--sandbox',
  '-a', '--ask-for-approval', '-C', '--cd', '-i', '--image', '--add-dir', '--enable', '--disable', '--color',
  '-o', '--output-last-message', '--output-schema', '--local-provider']);
// Codex config keys the plan writes; an owner override of one would be overwritten unseen.
const CODEX_PLANNED_KEYS = ['developer_instructions', 'plugins', 'skills', 'marketplaces'];

const flagName = (arg) => arg.split('=', 1)[0];

// Split the owner's engine arguments: what the plan merges (append text, plugin dirs), what stays,
// and what stops the launch. Arguments after a literal `--` are never read as options.
function analyzeArgs(engine, args, cwd) {
  const end = args.indexOf('--');
  const options = end < 0 ? args : args.slice(0, end);
  const refused = REFUSED[engine];
  for (const arg of options) {
    const name = flagName(arg);
    if (refused.continuation.includes(name)) fail('run-continuation-unsupported', { engine, argument: name }, 2);
    if (refused.settings.includes(name)) fail('run-argument-unsupported', { engine, argument: name }, 2);
  }
  const kept = [];
  const appendSources = [];
  const pluginDirs = [];
  let launchCwd = cwd;
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (end >= 0 && i >= end) { kept.push(arg); continue; }
    const name = flagName(arg);
    const inline = arg.includes('=') && arg.startsWith('--') ? arg.slice(name.length + 1) : null;
    const value = () => {
      if (inline !== null) return inline;
      if (i + 1 >= args.length || (end >= 0 && i + 1 >= end)) fail('invalid-arguments', { argument: name }, 2);
      return args[++i];
    };
    if ((engine === 'claude' || engine === 'omp') && name === '--append-system-prompt') {
      appendSources.push({ text: value() });
      continue;
    }
    if (engine === 'claude' && name === '--append-system-prompt-file') {
      const file = path.resolve(cwd, value());
      try { appendSources.push({ text: fs.readFileSync(file, 'utf8') }); }
      catch (error) { fail('config-unreadable', { field: '--append-system-prompt-file', detail: error.code || error.message }, 2); }
      continue;
    }
    if (engine === 'claude' && name === '--plugin-dir') {
      const dir = value();
      pluginDirs.push(path.resolve(cwd, dir));
      kept.push('--plugin-dir', dir);
      continue;
    }
    if (engine === 'codex' && (name === '-c' || name === '--config')) {
      const setting = value();
      const key = setting.split('=', 1)[0].trim();
      if (CODEX_PLANNED_KEYS.some((planned) => key === planned || key.startsWith(`${planned}.`))) {
        fail('run-argument-unsupported', { engine, argument: `${name} ${key}` }, 2);
      }
      kept.push(name, setting);
      continue;
    }
    if (engine === 'codex' && (name === '-C' || name === '--cd')) {
      const dir = value();
      launchCwd = path.resolve(cwd, dir);
      kept.push(name, dir);
      continue;
    }
    kept.push(arg);
  }
  if (appendSources.length > 1) fail('run-argument-unsupported', { engine, argument: 'more than one appended system prompt' }, 2);
  if (engine === 'codex') {
    // `codex resume` and `codex exec resume` continue a recorded session; `fork` copies one.
    const positionals = [];
    for (let i = 0; i < options.length; i++) {
      const arg = options[i];
      if (arg.startsWith('-')) { if (CODEX_VALUE_FLAGS.has(arg)) i++; continue; }
      positionals.push(arg);
    }
    const [first, second] = positionals;
    if (first === 'resume' || first === 'fork' || (first === 'exec' && (second === 'resume' || second === 'fork'))) {
      fail('run-continuation-unsupported', { engine, argument: first === 'exec' ? `exec ${second}` : first }, 2);
    }
  }
  const print = options.some((arg) => arg === '-p' || arg === '--print');
  return { kept, appendSystemPrompt: appendSources[0]?.text, pluginDirs, cwd: launchCwd, print };
}

// The executable a launch runs, resolved once from PATH and used for every probe and the launch.
function resolveProgram(engine, env) {
  if (process.platform === 'win32') fail('run-platform-unsupported', { platform: process.platform }, 2);
  for (const dir of (env.PATH || '').split(path.delimiter)) {
    if (!dir) continue;
    const candidate = path.join(dir, engine);
    try {
      if (fs.statSync(candidate).isFile()) { fs.accessSync(candidate, fs.constants.X_OK); return candidate; }
    } catch (error) {
      if (!['ENOENT', 'ENOTDIR', 'EACCES'].includes(error.code)) throw error;
    }
  }
  fail('run-engine-missing', { engine }, 2);
}

function engineVersion(program, env) {
  const result = spawnSync(program, ['--version'], { env, encoding: 'utf8', timeout: READ_MS, stdio: ['ignore', 'pipe', 'pipe'] });
  if (result.error || result.status !== 0) return null;
  const match = `${result.stdout}`.match(/\d+\.\d+\.\d+/);
  return match ? match[0] : null;
}

function readJsonFile(file, missing = undefined) {
  let text;
  try { text = fs.readFileSync(file, 'utf8'); }
  catch (error) {
    if (error.code === 'ENOENT') return missing;
    fail('config-unreadable', { path: file, detail: error.code || error.message }, 2);
  }
  try { return JSON.parse(text); }
  catch { fail('config-unreadable', { path: file, detail: 'not JSON' }, 2); }
}

function gitCommonDir(cwd) {
  const result = spawnSync('git', ['-C', cwd, 'rev-parse', '--path-format=absolute', '--git-common-dir'],
    { encoding: 'utf8', env: { ...process.env, GIT_OPTIONAL_LOCKS: '0' }, stdio: ['ignore', 'pipe', 'ignore'] });
  if (result.status !== 0) return null;
  try { return fs.realpathSync.native(result.stdout.trim()); } catch { return null; }
}

// The Devlyn app's machine record (`~/.devlyn/harness/state.json`), read only: its default release and
// the machine's or this repository's choice. Absent is fine; present but unreadable stops the launch.
function appState(home, common) {
  const file = path.join(home, '.devlyn/harness/state.json');
  const state = readJsonFile(file, null);
  if (state === null) return { defaultRelease: null, choice: 'default' };
  const choices = ['default', 'devlyn', 'none'];
  if (!object(state) || state.schemaVersion !== 1 || !(state.defaultRelease === null || state.defaultRelease === undefined
      || (object(state.defaultRelease) && typeof state.defaultRelease.version === 'string'
        && /^[a-f0-9]{64}$/.test(state.defaultRelease.digest || '')))
      || (state.machineChoice !== undefined && !choices.includes(state.machineChoice))
      || (state.projects !== undefined && !object(state.projects))) {
    fail('state-unreadable', { path: file }, 3);
  }
  let choice = state.machineChoice === 'none' ? 'none' : 'default';
  if (choice !== 'none' && common) {
    const key = crypto.createHash('sha256').update(Buffer.from(common)).digest('hex');
    const project = state.projects?.[key];
    if (project !== undefined) {
      if (!object(project) || !choices.includes(project.choice)) fail('state-unreadable', { path: file }, 3);
      choice = project.choice;
    }
  }
  return { defaultRelease: state.defaultRelease || null, choice };
}

// A release chosen by a record must verify as recorded; it never yields to another release.
function recorded(root, version, digest, source) {
  let release;
  try { release = verifyRelease(root).release; }
  catch (error) { fail('release-unavailable', { source, version, detail: error.reason?.code || error.message }, 3); }
  if (release.version !== version || release.digest !== digest) fail('release-version-conflict', { source, version }, 3);
  return { release, source };
}

// The release a terminal launch plans with: an unfinished queue's bound release in this repository,
// else the app's default release, else this package itself, captured once into ~/.devlyn/cli/releases.
function selectRelease({ home, common, packageRoot, defaultRelease }) {
  if (common) {
    const file = path.join(common, 'devlyn-loops/harness.json');
    const binding = readJsonFile(file, null);
    if (binding !== null) {
      const ref = binding?.release;
      if (!object(binding) || binding.schemaVersion !== 1 || !object(ref) || typeof ref.root !== 'string'
          || typeof ref.version !== 'string' || typeof ref.digest !== 'string') {
        fail('state-unreadable', { path: file }, 3);
      }
      return recorded(ref.root, ref.version, ref.digest, 'queue');
    }
  }
  if (defaultRelease) {
    return recorded(path.join(home, '.devlyn/harness/devlyn-cli', defaultRelease.version), defaultRelease.version,
      defaultRelease.digest, 'app-default');
  }
  try {
    return { release: materializeRelease(packageRoot, path.join(home, '.devlyn/cli/releases')).release, source: 'package' };
  } catch (error) {
    // A source checkout or a damaged install is not a release; say so instead of planning without one.
    fail('release-unavailable', { source: 'package', detail: error.reason?.code || error.code || error.message }, 3);
  }
}

// Claude plugins named devlyn that Claude itself loads here (crates/devlynd harness.rs claude_devlyn_plugins).
function claudeDevlynPlugins(root, cwd) {
  const registry = readJsonFile(path.join(root, 'plugins/installed_plugins.json'), null);
  if (registry === null) return [];
  if (!object(registry) || registry.version !== 2 || !object(registry.plugins)) {
    fail('config-unreadable', { field: 'claude plugin registry', detail: 'not version 2' }, 2);
  }
  const settings = [path.join(cwd, '.claude/settings.local.json'), path.join(cwd, '.claude/settings.json'),
    path.join(root, 'settings.json')].map((file) => readJsonFile(file, null));
  const enabled = (id) => settings.find((value) => object(value) && object(value.enabledPlugins)
    && typeof value.enabledPlugins[id] === 'boolean')?.enabledPlugins[id] === true;
  return Object.entries(registry.plugins)
    .filter(([id]) => id.split('@')[0] === 'devlyn' && enabled(id))
    .flatMap(([, installs]) => (Array.isArray(installs) ? installs : []))
    .filter((install) => install?.scope === 'user'
      || (typeof install?.projectPath === 'string' && (cwd === install.projectPath || cwd.startsWith(install.projectPath + path.sep))))
    .map((install) => install?.installPath)
    .filter((dir) => typeof dir === 'string' && fs.statSync(dir, { throwIfNoEntry: false })?.isDirectory());
}

function withoutNulls(value) {
  if (value === null) return undefined;
  if (Array.isArray(value)) return value.map(withoutNulls).filter((item) => item !== undefined);
  if (object(value)) {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, withoutNulls(item)]).filter(([, item]) => item !== undefined));
  }
  return value;
}

// Codex's merged layers as its own app-server answers `config/read` (crates/devlynd codex.rs read_config).
function codexConfig(program, accountHome, cwd, env) {
  return new Promise((resolve, reject) => {
    const child = spawn(program, ['app-server'], { env: { ...env, CODEX_HOME: accountHome }, stdio: ['pipe', 'pipe', 'ignore'] });
    const lines = readline.createInterface({ input: child.stdout });
    const pending = new Map();
    let settled = false;
    const finish = (error, value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      lines.close();
      child.kill();
      if (error) reject(error); else resolve(value);
    };
    const refuse = (detail) => finish(Object.assign(new Error(detail), { reason: { code: 'config-unreadable', params: { field: 'codex config/read', detail } } }));
    const timer = setTimeout(() => refuse('timed out'), CODEX_READ_MS);
    child.on('error', (error) => refuse(error.code || error.message));
    child.on('exit', () => refuse('app-server exited'));
    lines.on('line', (line) => {
      let message;
      try { message = JSON.parse(line); } catch { refuse('unreadable line'); return; }
      if (message.id === undefined || !pending.has(message.id)) return;
      const handle = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) refuse(`${handle.method}: ${message.error.message}`);
      else handle.next(message.result);
    });
    let id = 0;
    const call = (method, params, next) => {
      id += 1;
      pending.set(id, { method, next });
      child.stdin.write(`${JSON.stringify({ id, method, params })}\n`);
    };
    call('initialize', { clientInfo: { name: 'devlyn-cli', version: require('../package.json').version } }, () => {
      child.stdin.write(`${JSON.stringify({ method: 'initialized' })}\n`);
      call('config/read', { cwd }, (result) => {
        if (!object(result?.config)) { refuse('no config'); return; }
        const read = result.config;
        const config = {};
        for (const key of ['developer_instructions', 'marketplaces', 'plugins']) {
          const value = withoutNulls(read[key]);
          if (value !== undefined) config[key] = value;
        }
        const entries = withoutNulls(read.skills?.config);
        if (entries !== undefined) config.skills = { config: entries };
        finish(null, config);
      });
    });
  }).catch((error) => fail(error.reason?.code || 'config-unreadable', error.reason?.params || { detail: error.message }, 2));
}

// omp's effective settings in this folder (crates/devlynd harness.rs omp_skills), plus autoResume.
function ompConfig(program, cwd, env) {
  const result = spawnSync(program, ['config', 'list', '--json'], { cwd, env, encoding: 'utf8', timeout: READ_MS, stdio: ['ignore', 'pipe', 'pipe'] });
  if (result.error || result.status !== 0) fail('config-unreadable', { field: 'omp config list', detail: (result.stderr || result.error?.message || '').trim().slice(0, 200) }, 2);
  let listed;
  try { listed = JSON.parse(result.stdout); } catch { fail('config-unreadable', { field: 'omp config list', detail: 'not JSON' }, 2); }
  if (!object(listed)) fail('config-unreadable', { field: 'omp config list', detail: 'not an object' }, 2);
  const skills = {};
  for (const [key, setting] of Object.entries(listed)) {
    if (key.startsWith('skills.') && object(setting) && 'value' in setting) skills[key.slice('skills.'.length)] = setting.value;
  }
  return { skills, autoResume: listed.autoResume?.value === true };
}

// Everything one fresh launch of `engine` with the owner's `args` needs before planning.
async function launchInputs({ engine, args, cwd, env, home, packageRoot }) {
  if (!ENGINES.includes(engine)) fail('run-engine-unsupported', { engine, supported: ENGINES.join(',') }, 2);
  const analyzed = analyzeArgs(engine, args, cwd);
  const program = resolveProgram(engine, env);
  const version = engineVersion(program, env);
  const common = gitCommonDir(analyzed.cwd);
  const state = appState(home, common);
  const { release, source } = selectRelease({ home, common, packageRoot, defaultRelease: state.defaultRelease });
  let effectiveConfig;
  let accountHome;
  if (engine === 'claude') {
    const root = env.CLAUDE_CONFIG_DIR || path.join(home, '.claude');
    effectiveConfig = { pluginDirs: [...analyzed.pluginDirs, ...claudeDevlynPlugins(root, analyzed.cwd)] };
    if (analyzed.appendSystemPrompt !== undefined) effectiveConfig.appendSystemPrompt = analyzed.appendSystemPrompt;
  } else if (engine === 'codex') {
    accountHome = env.CODEX_HOME || path.join(home, '.codex');
    if (!path.isAbsolute(accountHome) || !fs.statSync(accountHome, { throwIfNoEntry: false })?.isDirectory()) {
      fail('config-unreadable', { field: 'CODEX_HOME', detail: 'not an existing absolute folder' }, 2);
    }
    effectiveConfig = await codexConfig(program, accountHome, analyzed.cwd, env);
  } else {
    const omp = ompConfig(program, analyzed.cwd, env);
    if (omp.autoResume && !analyzed.print) fail('run-continuation-unsupported', { engine, argument: 'autoResume' }, 2);
    effectiveConfig = { skills: omp.skills };
    if (analyzed.appendSystemPrompt !== undefined) effectiveConfig.appendSystemPrompt = analyzed.appendSystemPrompt;
  }
  return { program, version, release, source, args: analyzed.kept, cwd: analyzed.cwd, choice: state.choice,
    accountHome, effectiveConfig };
}

module.exports = { ENGINES, analyzeArgs, launchInputs };
