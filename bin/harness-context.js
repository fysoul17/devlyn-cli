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

// Engine arguments `devlyn run` passes through: each is known not to change the session's freshness,
// its directory, or settings the plan merges. Anything else is refused, so a form this list has never
// seen (an attached short option, an alias, a future flag) cannot slip past as it could past a deny
// list. `flags` take no value and `values` take one; widen by reading the engine's help.
const OPTIONS = Object.freeze({
  claude: {
    flags: new Set(['-p', '--print', '--verbose', '--dangerously-skip-permissions', '--allow-dangerously-skip-permissions',
      '--no-session-persistence', '--include-partial-messages', '--no-chrome']),
    values: new Set(['--model', '--fallback-model', '--effort', '--permission-mode', '--output-format', '--input-format',
      '--add-dir', '--allowedTools', '--allowed-tools', '--disallowedTools', '--disallowed-tools', '--max-budget-usd',
      '--json-schema', '--mcp-config']),
  },
  codex: {
    flags: new Set(['--oss', '--search', '--no-alt-screen', '--dangerously-bypass-approvals-and-sandbox',
      '--skip-git-repo-check', '--ephemeral', '--json']),
    values: new Set(['-m', '--model', '-s', '--sandbox', '-a', '--ask-for-approval', '-i', '--image', '--add-dir',
      '--output-schema', '--color', '-o', '--output-last-message']),
  },
  omp: {
    flags: new Set(['-p', '--print', '--no-session', '--no-tools', '--no-lsp', '--no-pty', '--hide-thinking',
      '--auto-approve', '--print-thoughts', '--no-title']),
    values: new Set(['--model', '--smol', '--slow', '--plan', '--mode', '--thinking', '--tools', '--service-tier',
      '--max-time', '--warn-cost', '--max-cost', '--approval-mode', '--add-dir']),
  },
});
// `exec` (alias `e`) runs one Codex task; `debug prompt-input` shows the model input without a model call.
const CODEX_RUNS = new Set(['exec', 'e']);
const CONTINUATIONS = new Set(['resume', 'fork']);
// Options the engine itself reads as a list: the words after them are their values, up to the next
// option. Per engine, because the same name takes one value elsewhere (Codex and omp `--add-dir`).
const LISTS = Object.freeze({
  claude: new Set(['--add-dir', '--allowedTools', '--allowed-tools', '--disallowedTools', '--disallowed-tools', '--mcp-config']),
  codex: new Set(['-i', '--image']),
  omp: new Set(),
});
// Codex config keys the plan writes; an owner override of one would be overwritten unseen.
const CODEX_PLANNED_KEYS = ['developer_instructions', 'plugins', 'skills', 'marketplaces'];

// Text too long for a path, or otherwise no path at all, simply names no file.
function namesFile(candidate) {
  try { return fs.statSync(candidate, { throwIfNoEntry: false })?.isFile() === true; } catch { return false; }
}

function readAppend(file, field) {
  try { return fs.readFileSync(file, 'utf8'); }
  catch (error) { fail('config-unreadable', { field, detail: error.code || 'unreadable' }, 2); }
}

// Read the owner's arguments in order with each option's arity, so a value is never taken for an
// option. A dash always starts an option, as it does for the engine, and a one-word positional may be
// the engine's own command (`claude attach`, `codex resume`), so only text with a space is a prompt
// here; anything literal goes after `--`. Returns what stays, what the plan merges instead, and
// whether this is a print run.
function analyzeArgs(engine, args, cwd) {
  const { flags, values } = OPTIONS[engine];
  const kept = [];
  const positionals = [];
  const appended = [];
  const pluginDirs = [];
  let literal = [];
  let print = false;
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === '--') {
      kept.push(...args.slice(i));
      literal = args.slice(i + 1);
      break;
    }
    if (!arg.startsWith('-') || arg === '-') {
      kept.push(arg);
      positionals.push(arg);
      continue;
    }
    const equals = arg.startsWith('--') ? arg.indexOf('=') : -1;
    const name = equals < 0 ? arg : arg.slice(0, equals);
    const value = () => {
      if (equals >= 0) return arg.slice(equals + 1);
      if (++i >= args.length) fail('invalid-arguments', { argument: name }, 2);
      return args[i];
    };
    if (flags.has(name) && equals < 0) {
      if (name === '-p' || name === '--print') print = true;
      kept.push(arg);
    } else if (name === '--append-system-prompt' && engine !== 'codex') {
      const text = value();
      // omp reads an existing file named here; merging its name would lose the owner's text.
      appended.push(engine === 'omp' && namesFile(path.resolve(cwd, text)) ? readAppend(path.resolve(cwd, text), name) : text);
    } else if (name === '--append-system-prompt-file' && engine === 'claude') {
      appended.push(readAppend(path.resolve(cwd, value()), name));
    } else if (name === '--plugin-dir' && engine === 'claude') {
      const dir = value();
      pluginDirs.push(path.resolve(cwd, dir));
      kept.push('--plugin-dir', dir);
    } else if ((name === '-c' || name === '--config') && engine === 'codex') {
      const setting = value();
      const key = setting.split('=', 1)[0].trim();
      if (CODEX_PLANNED_KEYS.some((planned) => key === planned || key.startsWith(`${planned}.`))) {
        fail('run-argument-unsupported', { engine, argument: `${name} ${key}` }, 2);
      }
      kept.push(name, setting);
    } else if (values.has(name)) {
      const given = value();
      kept.push(...(equals < 0 ? [name, given] : [arg]));
      if (equals < 0 && LISTS[engine].has(name)) {
        while (i + 1 < args.length && !args[i + 1].startsWith('-')) kept.push(args[++i]);
      }
    } else {
      fail('run-argument-unsupported', { engine, argument: name }, 2);
    }
  }
  if (appended.length > 1) fail('run-argument-unsupported', { engine, argument: 'more than one appended system prompt' }, 2);
  // Interactive Claude and omp route a one-word command even after `--` (`claude -- update`).
  const routed = engine !== 'codex' && !print && literal.find((word) => !/\s/.test(word));
  if (routed) fail('run-argument-unsupported', { engine, argument: routed, hint: 'a one-word task needs -p' }, 2);
  const words = positionals.filter((word) => !/\s/.test(word));
  const [first, second] = words;
  const allowed = engine === 'codex'
    ? (positionals[0] === first && CODEX_RUNS.has(first) ? 1 : (first === 'debug' && second === 'prompt-input' ? 2 : 0)) : 0;
  const command = words[allowed];
  if (command !== undefined) {
    if (engine === 'codex' && CONTINUATIONS.has(command)) fail('run-continuation-unsupported', { engine, argument: command }, 2);
    fail('run-argument-unsupported', { engine, argument: command, hint: 'a one-word prompt goes after --' }, 2);
  }
  return { kept, appendSystemPrompt: appended[0], pluginDirs, print };
}

// The executable a launch runs, resolved once to an absolute path and used for every probe and the launch.
function resolveProgram(engine, env, cwd) {
  if (process.platform === 'win32') fail('run-platform-unsupported', { platform: process.platform }, 2);
  for (const dir of (env.PATH || '').split(path.delimiter)) {
    if (!dir) continue;
    const candidate = path.resolve(cwd, dir, engine);
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

const ABSENT = Symbol('absent');

// Only a path with nothing at it is absent. A dangling link or a file holding JSON null is a record
// that cannot be read, which must stop the launch rather than read as no record.
function readJsonFile(file) {
  if (!fs.lstatSync(file, { throwIfNoEntry: false })) return ABSENT;
  let text;
  try { text = fs.readFileSync(file, 'utf8'); }
  catch (error) { fail('config-unreadable', { path: file, detail: error.code || 'unreadable' }, 2); }
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
  const state = readJsonFile(file);
  if (state === ABSENT) return { defaultRelease: null, choice: 'default' };
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
    const binding = readJsonFile(file);
    if (binding !== ABSENT) {
      const ref = binding?.release;
      const defaults = binding?.defaults;
      const digest = /^[a-f0-9]{64}$/;
      if (!object(binding) || Object.keys(binding).sort().join() !== 'defaults,release,schemaVersion' || binding.schemaVersion !== 1
          || !object(ref) || ref.package !== 'devlyn-cli' || typeof ref.version !== 'string' || !digest.test(ref.digest || '')
          || typeof ref.root !== 'string' || !path.isAbsolute(ref.root)
          || !object(defaults) || typeof defaults.path !== 'string' || !path.isAbsolute(defaults.path)
          || !digest.test(defaults.sha256 || '')) {
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
  const registry = readJsonFile(path.join(root, 'plugins/installed_plugins.json'));
  if (registry === ABSENT) return [];
  if (!object(registry) || registry.version !== 2 || !object(registry.plugins)) {
    fail('config-unreadable', { field: 'claude plugin registry', detail: 'not version 2' }, 2);
  }
  const settings = [path.join(cwd, '.claude/settings.local.json'), path.join(cwd, '.claude/settings.json'),
    path.join(root, 'settings.json')].map(readJsonFile);
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
      // A read-only helper: nothing to save, and one that ignores SIGTERM must not hold this launch.
      child.kill('SIGKILL');
      child.stdin.destroy();
      child.stdout.destroy();
      child.unref();
      if (error) reject(error); else resolve(value);
    };
    const refuse = (detail) => finish(Object.assign(new Error(detail), { reason: { code: 'config-unreadable', params: { field: 'codex config/read', detail } } }));
    const timer = setTimeout(() => refuse('timed out'), CODEX_READ_MS);
    child.on('error', (error) => refuse(error.code || 'did not start'));
    child.on('exit', () => refuse('app-server exited'));
    lines.on('line', (line) => {
      let message;
      try { message = JSON.parse(line); } catch { refuse('unreadable line'); return; }
      if (message.id === undefined || !pending.has(message.id)) return;
      const handle = pending.get(message.id);
      pending.delete(message.id);
      // Its message can quote configuration, so only the failed method is said.
      if (message.error) refuse(`${handle.method} refused`);
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
  if (result.error || result.status !== 0) fail('config-unreadable', { field: 'omp config list', detail: result.error?.code || `exit ${result.status}` }, 2);
  let listed;
  try { listed = JSON.parse(result.stdout); } catch { fail('config-unreadable', { field: 'omp config list', detail: 'not JSON' }, 2); }
  if (!object(listed)) fail('config-unreadable', { field: 'omp config list', detail: 'not an object' }, 2);
  const skills = {};
  for (const [key, setting] of Object.entries(listed)) {
    if (key.startsWith('skills.') && object(setting) && 'value' in setting) skills[key.slice('skills.'.length)] = setting.value;
  }
  return { skills, autoResume: listed.autoResume?.value === true };
}

// omp loads APPEND_SYSTEM.md only when no append text is given, and the plan always gives some, so
// the owner's file is carried over: the project's first, then the user's, as omp looks them up.
function ompOwnerAppend(cwd, home) {
  for (const file of [path.join(cwd, '.omp/APPEND_SYSTEM.md'), path.join(home, '.omp/agent/APPEND_SYSTEM.md')]) {
    if (fs.statSync(file, { throwIfNoEntry: false })?.isFile()) return readAppend(file, 'APPEND_SYSTEM.md');
  }
  return undefined;
}

// Everything one fresh launch of `engine` with the owner's `args` needs before planning.
async function launchInputs({ engine, args, cwd, env, home, packageRoot }) {
  if (!ENGINES.includes(engine)) fail('run-engine-unsupported', { engine, supported: ENGINES.join(',') }, 2);
  const common = gitCommonDir(cwd);
  const state = appState(home, common);
  // A project turned off gets no plan to protect, so the owner's arguments go through untouched.
  const off = state.choice === 'none';
  const analyzed = off ? { kept: args, pluginDirs: [], print: false } : analyzeArgs(engine, args, cwd);
  const program = resolveProgram(engine, env, cwd);
  const version = engineVersion(program, env);
  const { release, source } = selectRelease({ home, common, packageRoot, defaultRelease: state.defaultRelease });
  let effectiveConfig;
  let accountHome;
  if (engine === 'claude') {
    const root = env.CLAUDE_CONFIG_DIR || path.join(home, '.claude');
    effectiveConfig = { pluginDirs: [...analyzed.pluginDirs, ...claudeDevlynPlugins(root, cwd)] };
    if (analyzed.appendSystemPrompt !== undefined) effectiveConfig.appendSystemPrompt = analyzed.appendSystemPrompt;
  } else if (engine === 'codex') {
    accountHome = env.CODEX_HOME || path.join(home, '.codex');
    if (!path.isAbsolute(accountHome) || !fs.statSync(accountHome, { throwIfNoEntry: false })?.isDirectory()) {
      fail('config-unreadable', { field: 'CODEX_HOME', detail: 'not an existing absolute folder' }, 2);
    }
    effectiveConfig = await codexConfig(program, accountHome, cwd, env);
  } else {
    const omp = ompConfig(program, cwd, env);
    if (omp.autoResume && !analyzed.print && !off) fail('run-continuation-unsupported', { engine, argument: 'autoResume' }, 2);
    effectiveConfig = { skills: omp.skills };
    const appended = analyzed.appendSystemPrompt ?? (off ? undefined : ompOwnerAppend(cwd, home));
    if (appended !== undefined) effectiveConfig.appendSystemPrompt = appended;
  }
  return { program, version, release, source, args: analyzed.kept, cwd, choice: state.choice, accountHome, effectiveConfig };
}

module.exports = { ENGINES, analyzeArgs, launchInputs };
