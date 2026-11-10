const fs = require('fs');
const os = require('os');
const path = require('path');
const { ENGINE_IDS, ENGINE_CAPABILITIES, readableVersion, supportedVersion } = require('./engines');
const { verifyRelease, sha256, fail, options, HarnessError } = require('./release');
const { fingerprint } = require('./skill-ownership');
const history = require('./skill-history.json');
const { MARKER, marketplaceName, projectionPath, inspectProjection } = require('./codex-projection');

const SKILLS = ['devlyn-ideate', 'devlyn-engines'];
// The version an engine's run-folder channel was examined on; bin/engines.js keeps the engine's floor. An
// older version, and Windows (channelGate), keep the plan they had before the channel: only a first task
// carries the principles.
const CHANNEL_MINIMUM = { antigravity: '1.5.4', cursor: '2026.11.05-86047df' };
const object = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);
const textValue = (value) => typeof value === 'string' && !value.includes('\0');
const strings = (value) => Array.isArray(value) && value.every(textValue);
const isFile = (file) => fs.statSync(file, { throwIfNoEntry: false })?.isFile() === true;
const reason = (code, params = {}) => ({ code, params });
const channel = (state = 'disabled', mechanism = null, reasons = []) => ({ state, mechanism, reasons });
const joinText = (...parts) => parts.filter((part) => part !== null && part !== undefined && part !== '').join('\n\n');

// TOML basic strings share JSON escaping except JSON's optional slash escape.
// Also escape DEL, forbidden in TOML strings. No shell quoting is involved.
function toml(value) {
  if (typeof value === 'string') return JSON.stringify(value).replace(/\x7f/g, '\\u007f');
  if (typeof value === 'boolean' || (typeof value === 'number' && Number.isFinite(value))) return String(value);
  if (Array.isArray(value)) return `[${value.map(toml).join(',')}]`;
  if (object(value)) return `{${Object.entries(value).map(([key, item]) => `${toml(key)}=${toml(item)}`).join(',')}}`;
  fail('config-unreadable', { field: 'TOML override', detail: 'unsupported value' }, 2);
}

function validateContext(context) {
  const allowed = ['schemaVersion', 'engine', 'version', 'launchMode', 'cwd', 'runDir', 'projectChoice',
    'committedBlockApplies', 'initialPrompt', 'accountRef', 'accountHome', 'effectiveConfig', 'skillRoots', 'recordedRelease'];
  if (!object(context) || context.schemaVersion !== 1 || Object.keys(context).some((key) => !allowed.includes(key))
      || !ENGINE_IDS.includes(context.engine) || !(context.version === null || textValue(context.version))
      || !['fresh', 'resume', 'fork'].includes(context.launchMode)
      || !['default', 'devlyn', 'none'].includes(context.projectChoice)
      || typeof context.committedBlockApplies !== 'boolean'
      || ![context.cwd, context.runDir].every((p) => textValue(p) && path.isAbsolute(p))
      || !(context.initialPrompt === null || (object(context.initialPrompt) && textValue(context.initialPrompt.text)
        && ['argv', 'stdin'].includes(context.initialPrompt.transport)
        && Object.keys(context.initialPrompt).every((k) => ['text', 'transport'].includes(k))))
      || (context.accountRef !== undefined && context.accountRef !== null && !textValue(context.accountRef))
      || (context.accountHome !== undefined && (!textValue(context.accountHome) || !path.isAbsolute(context.accountHome)))
      || (context.skillRoots !== undefined && (!strings(context.skillRoots) || !context.skillRoots.every(path.isAbsolute)))) {
    fail('invalid-arguments', { argument: 'activation context' }, 2);
  }
  if (context.recordedRelease !== undefined && context.recordedRelease !== null) {
    const ref = context.recordedRelease;
    if (!object(ref) || ref.package !== 'devlyn-cli' || !textValue(ref.version)
        || !/^[a-f0-9]{64}$/.test(ref.digest) || !textValue(ref.root) || !path.isAbsolute(ref.root)
        || Object.keys(ref).some((key) => !['package', 'version', 'digest', 'root'].includes(key))) {
      fail('invalid-arguments', { argument: 'recordedRelease' }, 2);
    }
  }
  return context;
}

function readContext(file) {
  if (file !== '-' && (!textValue(file) || !path.isAbsolute(file))) fail('invalid-arguments', { argument: 'context-file' }, 2);
  try {
    return validateContext(JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(fs.readFileSync(file === '-' ? 0 : file))));
  } catch (error) {
    if (error instanceof HarnessError) throw error;
    fail('config-unreadable', { field: 'context-file', detail: error.message }, 2);
  }
}

function statusFor(context) {
  const supported = ENGINE_CAPABILITIES[context.engine].executor;
  return {
    engine: context.engine, version: context.version, accountRef: context.accountRef ?? null,
    overall: 'disabled', principles: channel(), skills: channel(), hide: channel(), invocation: null,
    executor: { supported, reasons: supported ? [] : [reason('executor-unqualified', { engine: context.engine })] },
    inheritedDevlyn: [],
  };
}

function finish(plan) {
  const states = [plan.channels.principles.state, plan.channels.skills.state];
  plan.channels.overall = states.every((s) => s === 'disabled') ? 'disabled'
    : states.every((s) => s === 'configured') ? 'configured'
      : states.every((s) => s === 'unavailable') ? 'unavailable' : 'partial';
  if (plan.channels.overall === 'configured' && plan.channels.hide.state === 'partial') plan.channels.overall = 'partial';
  return plan;
}

// The app supplies only effective values used by this recipe. Null means the
// model-free config read failed; {} means it succeeded with no values set.
function effectiveConfig(context) {
  const config = context.effectiveConfig;
  const keys = {
    claude: ['appendSystemPrompt', 'pluginDirs'], codex: ['developer_instructions', 'skills', 'marketplaces', 'plugins'],
    grok: ['rules'], omp: ['appendSystemPrompt', 'skills'], antigravity: [], cursor: [],
    opencode: ['inlineConfig', 'skillsPaths'], kimi: ['ownerAgent'], copilot: ['skillsDirs', 'instructionsDirs'], qwen: ['appendSystemPrompt'],
    pi: ['appendSystemPrompt'],
  }[context.engine];
  if (!object(config) || Object.keys(config).some((key) => !keys.includes(key))) return null;
  for (const field of ['appendSystemPrompt', 'developer_instructions', 'rules', 'inlineConfig', 'skillsDirs', 'instructionsDirs']) {
    if (config[field] !== undefined && config[field] !== null && !textValue(config[field])) return null;
  }
  if (context.engine === 'kimi' && typeof config.ownerAgent !== 'boolean') return null;
  if (config.pluginDirs !== undefined && (!strings(config.pluginDirs) || !config.pluginDirs.every(path.isAbsolute))) return null;
  if (config.skillsPaths != null && !strings(config.skillsPaths)) return null;
  if (context.engine === 'codex') {
    for (const key of ['marketplaces', 'plugins', 'skills']) if (config[key] != null && !object(config[key])) return null;
    if (config.skills?.config !== undefined && (!Array.isArray(config.skills.config)
      || !config.skills.config.every((entry) => object(entry) && textValue(entry.path) && path.isAbsolute(entry.path)
        && typeof entry.enabled === 'boolean' && Object.keys(entry).every((key) => ['path', 'enabled'].includes(key))))) return null;
    for (const entry of Object.values(config.plugins || {})) {
      if (!object(entry) || typeof entry.enabled !== 'boolean') return null;
    }
    for (const entry of Object.values(config.marketplaces || {})) {
      if (!object(entry) || !textValue(entry.source_type) || !textValue(entry.source)) return null;
    }
  }
  if (context.engine === 'omp') {
    if (config.skills != null && !object(config.skills)) return null;
    for (const key of ['customDirectories', 'ignoredSkills']) {
      if (config.skills?.[key] !== undefined && !strings(config.skills[key])) return null;
    }
    if (config.skills?.enableSkillCommands !== undefined && typeof config.skills.enableSkillCommands !== 'boolean') return null;
  }
  return config;
}

// pi's agent dir is PI_CODING_AGENT_DIR, else ~/.pi/agent. That ~, and a leading ~ pi expands in the
// variable, is os.homedir(): USERPROFILE on Windows, HOME elsewhere (config.js getAgentDir). The home of
// its user .agents/skills takes HOME first on every platform (package-manager.js getHomeDir).
function piFolders(cwd, env, platform = process.platform) {
  const paths = platform === 'win32' ? path.win32 : path.posix;
  const home = (platform === 'win32' ? env.USERPROFILE : env.HOME) || os.homedir();
  const dir = env.PI_CODING_AGENT_DIR;
  const agentDir = dir ? dir.replace(platform === 'win32' ? /^~(?=$|[\\/])/ : /^~(?=$|\/)/, () => home) : paths.join(home, '.pi', 'agent');
  return { agentDir: paths.resolve(cwd, agentDir), agentsHome: env.HOME || home };
}

function discoveryRoots(context, env, config) {
  const home = env.HOME || env.USERPROFILE || os.homedir();
  const pi = piFolders(context.cwd, env);
  const roots = [...(context.skillRoots || [])];
  const add = (base, ...parts) => { if (base) roots.push(path.resolve(base, ...parts)); };
  const engine = context.engine;
  // Antigravity and Cursor search the folders their examined version reads only where they get their run-folder
  // channel; elsewhere they keep the folders searched before it.
  const channelled = ['antigravity', 'cursor'].includes(engine) && !channelGate(context);
  const antigravity = channelled && engine === 'antigravity';
  const native = {
    claude: [env.CLAUDE_CONFIG_DIR || path.join(home, '.claude'), '.claude'],
    codex: [context.accountHome || env.CODEX_HOME || path.join(home, '.codex'), '.agents'],
    grok: [env.GROK_HOME || path.join(home, '.grok'), '.grok'],
    omp: [env.PI_CODING_AGENT_DIR || path.join(home, '.omp/agent'), '.omp'],
    antigravity: [path.join(home, '.gemini/antigravity-cli'), '.agents'],
    cursor: [null, null], opencode: [path.join(env.XDG_CONFIG_HOME || path.join(home, '.config'), 'opencode'), '.opencode'],
    kimi: [env.KIMI_CODE_HOME || path.join(home, '.kimi-code'), '.kimi-code'],
    copilot: [env.COPILOT_HOME || path.join(home, '.copilot'), '.github'],
    qwen: [env.QWEN_HOME || path.join(home, '.qwen'), '.qwen'],
    pi: [pi.agentDir, null],
  }[engine];
  if (engine !== 'codex') add(native[0], 'skills');
  const copilotDefaultHome = !env.COPILOT_HOME || path.resolve(env.COPILOT_HOME) === path.join(home, '.copilot');
  if (!['claude', 'cursor'].includes(engine) && !antigravity && (engine !== 'copilot' || copilotDefaultHome)) add(engine === 'pi' ? pi.agentsHome : home, '.agents/skills');
  // The examined Antigravity reads ~/.gemini/skills and its personal folder ~/.gemini/config instead.
  if (antigravity) { add(home, '.gemini/skills'); add(home, '.gemini/config/skills'); }
  if (['omp', 'opencode', 'grok'].includes(engine)) add(home, '.claude/skills');
  if (engine === 'omp') {
    add(home, '.codex/skills'); add(home, '.agent/skills');
    for (const dir of config?.skills?.customDirectories || []) add(context.cwd, dir);
  }
  if (engine === 'codex' && process.platform !== 'win32') add('/etc/codex', 'skills');
  if (engine === 'opencode') {
    add(env.OPENCODE_CONFIG_DIR, 'skills');
    for (const dir of config?.skillsPaths || []) add(context.cwd, dir);
  }
  if (engine === 'copilot') for (const dir of (config?.skillsDirs ?? env.COPILOT_SKILLS_DIRS ?? '').split(',').filter(Boolean)) add(context.cwd, dir);
  if (engine === 'pi') add(context.cwd, '.pi/skills');
  const walk = [];
  for (let dir = path.resolve(context.cwd); ; dir = path.dirname(dir)) {
    walk.push(dir);
    if (fs.existsSync(path.join(dir, '.git'))) break;
    // Outside any repository the examined Antigravity reads the working directory alone.
    if (dir === path.dirname(dir)) { if (antigravity) walk.splice(1); break; }
  }
  // The examined Cursor also searches nested folders below the working directory, which the planner does not.
  const cursorFolders = channelled && engine === 'cursor' ? ['.cursor', '.agents', '.claude', '.codex', '.grok'] : [];
  for (const folder of cursorFolders) add(home, folder, 'skills');
  if (cursorFolders.length) add(home, '.cursor/skills-cursor');
  for (const dir of walk) {
    for (const folder of cursorFolders) add(dir, folder, 'skills');
    if (native[1]) add(dir, native[1], 'skills');
    if (!['claude', 'cursor'].includes(engine)) add(dir, '.agents/skills');
    if (['grok', 'omp', 'opencode', 'copilot'].includes(engine)) add(dir, '.claude/skills');
    if (['omp', 'antigravity'].includes(engine)) add(dir, '.agent/skills');
    if (antigravity) { add(dir, '_agents/skills'); add(dir, '_agent/skills'); }
  }
  return [...new Set(roots)];
}

function kimiSkillRoots(context, env) {
  const home = env.HOME || env.USERPROFILE || os.homedir();
  let project = path.resolve(context.cwd);
  const roots = new Set(), errors = [];
  for (let dir = project; ; dir = path.dirname(dir)) {
    const git = path.join(dir, '.git');
    try {
      if (fs.statSync(git, { throwIfNoEntry: false })) { project = dir; break; }
    } catch (error) {
      errors.push(reason('config-unreadable', { path: git, detail: error.message }));
      break;
    }
    if (dir === path.dirname(dir)) break;
  }
  // --skills-dir replaces auto discovery and makes every root user-priority:
  // first-name wins, so preserve workspace precedence by putting it first.
  for (const root of [path.join(project, '.kimi-code/skills'), path.join(project, '.agents/skills'),
    path.resolve(env.KIMI_CODE_HOME || path.join(home, '.kimi-code'), 'skills'), path.resolve(home, '.agents/skills')]) {
    try {
      if (fs.statSync(root, { throwIfNoEntry: false })?.isDirectory()) roots.add(fs.realpathSync(root));
    } catch (error) {
      errors.push(reason('config-unreadable', { path: root, detail: error.message }));
    }
  }
  return { roots: [...roots], errors };
}

// omp and pi read their own APPEND_SYSTEM.md only when no append text is passed, and the plan passes
// some, so the owner's text leads it. Text the caller supplies wins, an explicit empty string included.
// Only when it supplies none (the key absent, or null for unset) is the first existing file `lookup()`
// names read, as `devlyn run` reads omp's (harness-context.js ompOwnerAppend). Returns {text}, or
// {reason} when the owner's text cannot be known.
function ownerAppend(config, lookup) {
  if (config.appendSystemPrompt != null) return { text: config.appendSystemPrompt };
  try {
    const found = lookup();
    if (found.reason) return found;
    const file = found.files.find(isFile);
    return { text: file === undefined ? null : fs.readFileSync(file, 'utf8') };
  } catch (error) {
    return { reason: reason('config-unreadable', { path: error.path, detail: error.code || error.message }) };
  }
}

// pi's user and project settings.json (settings-manager.js). Entries they name resolve through pi's own
// package manager, which the planner does not repeat. A file that cannot be read is null and reported.
function piSettings(cwd, agentDir) {
  const settings = { errors: [] };
  for (const [scope, file] of [['user', path.join(agentDir, 'settings.json')], ['project', path.join(cwd, '.pi/settings.json')]]) {
    try {
      settings[scope] = fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, '') || '{}') : {};
    } catch (error) {
      settings[scope] = null;
      settings.errors.push(reason('config-unreadable', { path: file, detail: error.code || error.message }));
    }
  }
  return settings;
}
const listed = (settings, ...keys) => keys.some((key) => settings?.[key] != null && settings[key].length !== 0);

// Whether the agent dir's extensions folder holds anything pi could load; pi skips dot entries and
// node_modules (package-manager.js collectAutoExtensionEntries).
function piExtensionEntries(agentDir) {
  try {
    return fs.readdirSync(path.join(agentDir, 'extensions')).some((name) => !name.startsWith('.') && name !== 'node_modules');
  } catch (error) {
    if (error.code === 'ENOENT') return false;
    throw error;
  }
}

// pi reads a project's .pi/APPEND_SYSTEM.md only when it trusts the project, else its agent dir's
// (resource-loader discoverAppendSystemPromptFile). pi first asks the extensions it loads before trust,
// and the first yes or no wins (project-trust.js resolveProjectTrusted). With project settings held
// untrusted, those come only from the agent dir's extensions folder and the extensions or packages its
// user settings name (resource-loader loadProjectTrustExtensions, package-manager resolve): the app
// passes no -e, and pi's built-in extensions answer no trust question. With none, trust is pi's saved
// decision for the folder or its nearest decided parent (trust.json). Otherwise pi settles trust at
// launch, so which file it reads cannot be known here. The planner never writes trust.
function piAppendFiles(cwd, agentDir, userSettings) {
  const project = path.join(cwd, '.pi/APPEND_SYSTEM.md');
  const user = path.join(agentDir, 'APPEND_SYSTEM.md');
  if (!isFile(project)) return { files: [user] };
  const undecided = { reason: reason('principles-unavailable', { detail: 'project-trust-undecided', path: project }) };
  if (userSettings === null || listed(userSettings, 'extensions', 'packages') || piExtensionEntries(agentDir)) return undecided;
  const store = path.join(agentDir, 'trust.json');
  let trusted = null;
  try {
    const saved = fs.existsSync(store) ? JSON.parse(fs.readFileSync(store, 'utf8').replace(/^\uFEFF/, '')) : {};
    if (!object(saved) || Object.values(saved).some((value) => ![true, false, null].includes(value))) throw new Error('not a trust record');
    for (let dir = fs.realpathSync(cwd); trusted === null; dir = path.dirname(dir)) {
      if (typeof saved[dir] === 'boolean') trusted = saved[dir];
      else if (dir === path.dirname(dir)) break;
    }
  } catch (error) {
    return { reason: reason('config-unreadable', { path: store, detail: error.code || error.message }) };
  }
  if (trusted === null) return undecided;
  return { files: [trusted ? project : user] };
}

// The files pi may load as skills below a root (package-manager.js collectSkillEntries). pi stops at a
// folder's SKILL.md unless an ignore file hides it, and takes other .md files at the root of its own
// folders and below it in .agents/skills. Ignore files are not read here, so every .md file is taken and
// every folder searched: at least what pi finds is found. Dot entries and node_modules are skipped as pi
// skips them.
function piSkillFiles(root) {
  const files = [], seen = new Set();
  const visit = (dir) => {
    let entries;
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch (error) {
      if (dir === root && error.code === 'ENOENT') return;
      throw error;
    }
    seen.add(fs.realpathSync(dir));
    for (const entry of entries) {
      if (entry.name.startsWith('.') || entry.name === 'node_modules') continue;
      const full = path.join(dir, entry.name);
      let kind = entry;
      // pi follows links and skips one it cannot follow.
      if (entry.isSymbolicLink()) { try { kind = fs.statSync(full); } catch { continue; } }
      if (kind.isDirectory()) { if (!seen.has(fs.realpathSync(full))) visit(full); }
      else if (kind.isFile() && entry.name.endsWith('.md')) files.push(full);
    }
  };
  visit(root);
  return files;
}

// The names pi may give a skill file (skills.js loadSkillFromFile): its frontmatter's string `name`, else,
// also for an empty one, its folder's name. A plain scalar may be no string (null, a number), so the
// folder counts then too.
// null when the name is not one simple line, which counts as a collision.
function piSkillNames(file) {
  const text = fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, '').replace(/\r\n?/g, '\n');
  const folder = path.basename(path.dirname(file));
  const end = text.startsWith('---') ? text.indexOf('\n---', 3) : -1;
  const lines = end < 0 ? [] : text.slice(4, end).split('\n');
  if (/^\s/.test(lines.find((line) => line.trim() && !line.trim().startsWith('#')) ?? '')) return null;
  // Lines that are or may be a top-level name key: quoted or complex keys, merges, anchors, flow mappings.
  const keys = lines.flatMap((line, index) => (/^(?:name[ \t]*:|["'?{[&*!]|<<)/.test(line) ? [index] : []));
  if (!keys.length) return [folder];
  const match = keys.length === 1 && /^name:(.*)$/.exec(lines[keys[0]]);
  if (!match) return null;
  const value = match[1].replace(/\s#.*$/, '').trim();
  const quoted = /^"([^"\\]*)"$|^'([^']*)'$/.exec(value);
  if (quoted) return [(quoted[1] ?? quoted[2]) || folder];
  const next = lines.slice(keys[0] + 1).find((line) => line.trim()) ?? '';
  if (!value || /^[-?:,[\]{}#&*!|>'"%@`]/.test(value) || /^\s/.test(next)) return null;
  return [value, folder];
}

// pi names a skill by its frontmatter wherever it sits below a root, and a found name wins over --skill.
// Files `found` already reports are skipped.
function piNameCollisions(roots, found) {
  const collisions = [], errors = [], seen = new Set(found.map((entry) => entry.path));
  for (const root of roots) {
    try {
      for (const file of piSkillFiles(root)) {
        if (seen.has(file)) continue;
        seen.add(file);
        const names = piSkillNames(file);
        if (names === null) collisions.push(reason('name-collision', { path: file }));
        else for (const name of new Set(names)) if (SKILLS.includes(name)) collisions.push(reason('name-collision', { name, path: file }));
      }
    } catch (error) {
      errors.push(reason('config-unreadable', { path: error.path || root, detail: error.code || error.message }));
    }
  }
  return { collisions, errors };
}

function inspectSkills(context, release, env, config, active) {
  const found = [], errors = [], hashes = new Map();
  for (const root of discoveryRoots(context, env, config)) {
    // Reusing the selected, verified release is not a competing OpenCode source.
    if (active && context.engine === 'opencode' && config?.skillsPaths && root === path.join(release.root, 'config/skills')) continue;
    for (const name of SKILLS) {
      const dir = path.join(root, name);
      try {
        if (!fs.lstatSync(dir, { throwIfNoEntry: false })) continue;
        const hash = fingerprint(dir);
        if (!hashes.has(name)) hashes.set(name, fingerprint(path.join(release.root, 'config/skills', name)));
        found.push({ name, path: path.join(dir, 'SKILL.md'), owned: hash === hashes.get(name) || (history.skills[name] || []).includes(hash) });
      } catch (error) {
        // An unreadable/linked candidate can collide, but never authorizes hide.
        found.push({ name, path: path.join(dir, 'SKILL.md'), owned: false });
        errors.push(reason('config-unreadable', { path: dir, detail: error.message }));
      }
    }
  }
  return { found, errors };
}

function skillCatalog(release, paths = path) {
  const root = paths.join(release.root, 'config', 'skills');
  return ['Devlyn session skill catalog (read the absolute file to invoke):',
    ...SKILLS.map((name) => `${name}: ${paths.join(root, name, 'SKILL.md')}`),
    `This session's _shared folder is ${paths.join(root, '_shared')}.`,
    'Use that absolute folder wherever the Devlyn defaults name _shared/.',
  ].join('\n');
}

// A skill entry of Antigravity's run folder: the release skill's own name and description lines as
// written, then the release SKILL.md to follow. A copy cannot be planned (plan files are text and the
// skills carry scripts), and since 1.5.2 Antigravity skips a link or a manifest entry that leads outside
// the added folder. Each line must be one complete top-level entry, or the plan fails.
function antigravitySkill(release, name) {
  const dir = path.join(release.root, 'config/skills', name);
  const file = path.join(dir, 'SKILL.md');
  const text = fs.readFileSync(file, 'utf8').replace(/\r\n/g, '\n');
  const end = text.startsWith('---\n') ? text.indexOf('\n---\n', 3) : -1;
  const lines = end < 0 ? [] : text.slice(4, end).split('\n');
  const header = ['name', 'description'].map((field) => {
    const at = lines.flatMap((line, index) => (line.startsWith(`${field}:`) ? [index] : []));
    if (at.length !== 1 || !lines[at[0]].slice(field.length + 1).trim() || /^\s/.test(lines[at[0] + 1] ?? '')) {
      fail('config-unreadable', { path: file, field }, 1);
    }
    return lines[at[0]];
  });
  return `---\n${header.join('\n')}\n---\nRead ${file} and follow it as this skill. `
    + `Its folder, ${dir}, is the skill's folder (DEVLYN_SKILL_DIR), not the folder of this file.\n`;
}

// The path with the links of its existing part resolved; parts that do not exist yet are kept as given.
function physicalPath(target) {
  let parent = path.resolve(target);
  const missing = [];
  while (!fs.existsSync(parent)) { missing.unshift(path.basename(parent)); parent = path.dirname(parent); }
  return path.join(fs.realpathSync(parent), ...missing);
}

// The reasons for the principles and the skills when neither reaches the session.
const withheld = (params) => [reason('principles-unavailable', params), reason('skills-unavailable', params)];

// Why an engine keeps the plan it had before its run-folder channel, as the reasons for the principles and the
// skills when no first task carries them, or null when it gets the channel. The channels were examined on macOS
// and are not planned on Windows, whatever the version: it cannot show who owns a folder, and an argument that
// misbehaves there would break a pane. Below the version a channel was examined on, updating the engine gets it.
function channelGate(context) {
  if (process.platform === 'win32') return withheld({ detail: 'platform-unexamined' });
  const minimum = CHANNEL_MINIMUM[context.engine];
  if (supportedVersion(context.engine, context.version, minimum)) return null;
  const outdated = reason('engine-version-unsupported', { minimum });
  return [outdated, outdated];
}

// The first directory that makes a run-folder channel's `folder`, inside a resolved run directory (physicalPath),
// unsafe to hand an engine that loads what it finds there, or null. Every existing level from the folder up, the
// folder included, must be a real directory (a link is not one) of this user or root that no one else can write:
// another user could put a .git or a folder of their own there later. With `git`, no directory from the folder up
// may hold a .git entry of any kind: Antigravity 1.5.4 loads the agents and hooks of a Git root above an added
// folder with no trust check. A level that does not exist yet is skipped; a level lstat cannot read cannot be
// shown safe. Access-control lists are not read.
function unsafeRunDir(folder, git) {
  const entry = (file) => {
    try { return fs.lstatSync(file, { throwIfNoEntry: false }) ?? null; } catch { return false; }
  };
  for (let dir = folder; ; dir = path.dirname(dir)) {
    const stats = entry(dir);
    if (stats === false || (stats && (!stats.isDirectory() || ![process.getuid(), 0].includes(stats.uid) || stats.mode & 0o022))) return dir;
    if (git && entry(path.join(dir, '.git')) !== null) return dir;
    if (dir === path.dirname(dir)) return null;
  }
}

function codexRegistrations(config, accountHome) {
  const owned = [], errors = [];
  for (const [key, plugin] of Object.entries(config.plugins || {})) {
    if (!plugin.enabled || !key.startsWith('devlyn@')) continue;
    const market = key.slice('devlyn@'.length), source = config.marketplaces?.[market];
    if (source?.source_type !== 'local' || !path.isAbsolute(source.source)) continue;
    const root = path.resolve(source.source, '../..');
    if (path.join(root, 'native/codex') !== source.source) continue;
    try {
      // Name and marketplace source alone never prove ownership. Require the
      // resolver's marker, release verification and exact projection payload.
      const manifest = path.join(root, 'release.json');
      if (!fs.lstatSync(manifest, { throwIfNoEntry: false })) continue;
      const release = verifyRelease(root).release;
      if (marketplaceName(release) !== market) continue;
      if (!fs.lstatSync(path.join(projectionPath(release, accountHome), MARKER), { throwIfNoEntry: false })) continue;
      inspectProjection(release, accountHome);
      owned.push(key);
    } catch (error) {
      errors.push(reason('config-unreadable', { field: 'plugins', name: key, detail: error.message }));
    }
  }
  return { owned, errors };
}

function planActivation(releaseRoot, input, env = process.env) {
  const context = validateContext(input);
  const status = statusFor(context);
  const plan = { schemaVersion: 1, release: null, engineArgs: [], envPatch: {}, prompt: null,
    files: [], machineSync: null, channels: status };
  const continuation = context.launchMode !== 'fresh';
  const recorded = continuation && context.recordedRelease !== undefined;
  const off = recorded ? context.recordedRelease === null : context.projectChoice === 'none';
  const release = verifyRelease(recorded && !off ? context.recordedRelease.root : releaseRoot).release;
  if (recorded && !off && (release.digest !== context.recordedRelease.digest || release.version !== context.recordedRelease.version)) {
    fail('release-version-conflict', { version: context.recordedRelease.version }, 3);
  }
  const config = effectiveConfig(context);
  const { found, errors } = inspectSkills(context, release, env, config, !off);
  if (errors.length) status.hide = channel('partial', null, errors);
  status.inheritedDevlyn = found.filter((entry) => entry.owned).map((entry) => entry.path);
  const supported = supportedVersion(context.engine, context.version);
  const c = (key, value) => {
    const encoded = `${key}=${toml(value)}`;
    const previous = plan.engineArgs.findIndex((arg) => arg.startsWith(`${key}=`));
    if (previous < 0) plan.engineArgs.push('-c', encoded);
    else plan.engineArgs[previous] = encoded;
  };
  const accountHome = context.accountHome || env.CODEX_HOME || path.join(env.HOME || env.USERPROFILE || os.homedir(), '.codex');
  let pluginOverrides = config?.plugins || {};
  if (context.engine === 'codex' && config && supported) {
    if (!path.isAbsolute(accountHome)) fail('config-unreadable', { field: 'CODEX_HOME' }, 2);
    if (context.accountHome && env.CODEX_HOME && fs.realpathSync(context.accountHome) !== fs.realpathSync(env.CODEX_HOME)) {
      fail('config-unreadable', { field: 'accountHome', detail: 'does not match finalized CODEX_HOME' }, 2);
    }
    const registrations = codexRegistrations(config, accountHome);
    status.inheritedDevlyn.push(...registrations.owned);
    pluginOverrides = { ...config.plugins };
    for (const key of registrations.owned) pluginOverrides[key] = { ...pluginOverrides[key], enabled: false };
    if (registrations.owned.length) {
      c('plugins', pluginOverrides);
      status.hide = channel('configured', 'plugins');
    }
    const hideErrors = [...errors, ...registrations.errors];
    if (hideErrors.length) status.hide = channel('partial', null, hideErrors);
    const owned = new Set(found.filter((entry) => entry.owned).map((entry) => entry.path));
    if (owned.size) {
      const entries = (config.skills?.config || []).map((entry) => ({ ...entry, ...(owned.has(entry.path) ? { enabled: false } : {}) }));
      for (const file of owned) if (!entries.some((entry) => entry.path === file)) entries.push({ path: file, enabled: false });
      c('skills.config', entries);
      status.hide = channel(hideErrors.length ? 'partial' : 'configured', 'skills.config', hideErrors);
    }
  }
  if (status.inheritedDevlyn.length && status.hide.state === 'disabled') {
    status.hide = channel('partial', null, [reason('skills-unavailable', { channel: 'selective-hide' })]);
  }
  if (off) return finish(plan);
  plan.release = release;
  if (!supported) {
    const reasons = [readableVersion(context.engine, context.version)
      ? reason('engine-version-unsupported', { minimum: ENGINE_CAPABILITIES[context.engine].minimum })
      : reason('engine-version-unreadable')];
    status.principles = channel('unavailable', null, reasons);
    status.skills = channel('unavailable', null, reasons);
    return finish(plan);
  }
  if (!config) {
    const reasons = [reason('config-unreadable', { field: 'effectiveConfig' })];
    status.principles = channel('partial', null, reasons);
    status.skills = channel('partial', null, reasons);
    return finish(plan);
  }
  // The selected release is the one source of principles; a committed project block never suppresses it.
  const defaults = fs.readFileSync(path.join(release.root, 'config/skills/_shared/runtime-principles.md'), 'utf8');
  const catalog = skillCatalog(release);
  const instructions = joinText(defaults, catalog);
  const file = (relativePath, utf8) => {
    const relative = path.relative(release.root, physicalPath(context.runDir));
    if (!relative || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))) {
      fail('invalid-arguments', { argument: 'runDir must be outside the release' }, 2);
    }
    plan.files.push({ relativePath, utf8, sha256: sha256(utf8) });
    return path.join(context.runDir, relativePath);
  };
  const principles = (mechanism) => { status.principles = channel('configured', mechanism); };
  // The catalog travels in the principles text: without that text only the absolute invocation is left.
  const fallback = (reasons = [], withCatalog = true) => {
    status.skills = withCatalog ? channel('partial', 'absolute-catalog', [...reasons, reason('skills-catalog')])
      : channel('partial', null, reasons);
    status.invocation = { kind: 'read-file', text: `Read ${path.join(release.root, 'config/skills/devlyn-ideate/SKILL.md')}` };
  };
  const native = (mechanism, kind, text) => { status.skills = channel('configured', mechanism); status.invocation = { kind, text }; };
  // Where no run-folder channel is planned, only a first task carries the principles and the catalog, ahead
  // of its text; without one nothing reaches the session and each channel gives its reason.
  const firstTask = ([principlesReason, skillsReason]) => {
    if (context.initialPrompt) {
      status.principles = channel('partial', 'initial-task', [reason('principles-task-only')]);
      plan.prompt = { ...context.initialPrompt, text: joinText(instructions, context.initialPrompt.text) };
      fallback();
    } else {
      status.principles = channel('unavailable', null, [principlesReason]);
      status.skills = channel('unavailable', null, [skillsReason]);
    }
  };
  // A skill folder that cannot be inspected is also found, so every inspection error comes with a collision.
  const collisions = found.map((entry) => reason('name-collision', { name: entry.name, path: entry.path }));
  switch (context.engine) {
    case 'claude': {
      const pluginDir = path.join(release.root, 'native/claude');
      const conflicts = [];
      let alreadySelected = false;
      for (const dir of config.pluginDirs || []) {
        try {
          if (fs.realpathSync(dir) === pluginDir) { alreadySelected = true; continue; }
          const manifest = JSON.parse(fs.readFileSync(path.join(dir, '.claude-plugin/plugin.json'), 'utf8'));
          if (!object(manifest) || !textValue(manifest.name)) conflicts.push(reason('config-unreadable', { path: dir }));
          else if (manifest.name === 'devlyn') conflicts.push(reason('name-collision', { name: 'devlyn', path: dir }));
        } catch (error) {
          conflicts.push(reason('config-unreadable', { path: dir, detail: error.message }));
        }
      }
      if (!conflicts.length && !alreadySelected) plan.engineArgs.push('--plugin-dir', pluginDir);
      plan.engineArgs.push('--append-system-prompt-file',
        file('devlyn-instructions.md', joinText(config.appendSystemPrompt, instructions)));
      principles('append-system-prompt-file');
      if (conflicts.length) fallback(conflicts);
      else native('plugin-dir', 'slash', '/devlyn:devlyn-ideate');
      break;
    }
    case 'codex': {
      const market = marketplaceName(release), key = `devlyn@${market}`;
      const source = path.join(release.root, 'native/codex');
      const existing = config.marketplaces?.[market];
      let collision = (existing && (existing.source_type !== 'local' || existing.source !== source))
        || (!existing && config.plugins?.[key] !== undefined);
      try { inspectProjection(release, accountHome); }
      catch (error) {
        if (!(error instanceof HarnessError) || error.reason.code !== 'name-collision') throw error;
        collision = true;
      }
      if (collision) fallback([reason('name-collision', { name: key, path: projectionPath(release, accountHome) })]);
      else {
        c('marketplaces', { ...config.marketplaces, [market]: { ...existing, source_type: 'local', source } });
        c('plugins', { ...pluginOverrides, [key]: { ...config.plugins?.[key], enabled: true } });
        plan.machineSync = { engine: 'codex', accountHome };
        native('session-plugin', 'dollar', '$devlyn:devlyn-ideate');
      }
      c('developer_instructions', joinText(config.developer_instructions, instructions));
      principles('developer_instructions');
      break;
    }
    case 'omp': {
      const skills = { ...config.skills,
        customDirectories: [...new Set([...(config.skills?.customDirectories || []), path.join(release.root, 'config/skills')])] };
      // The files in the order `devlyn run` reads them (harness-context.js ompOwnerAppend).
      const owner = ownerAppend(config, () => ({ files: [path.join(context.cwd, '.omp/APPEND_SYSTEM.md'),
        path.join(env.HOME || env.USERPROFILE || os.homedir(), '.omp/agent/APPEND_SYSTEM.md')] }));
      plan.engineArgs.push('--config', file('devlyn-omp.json', JSON.stringify({ skills }, null, 2) + '\n'));
      // Owner text that cannot be known leaves the flag off, so the engine's own lookup stays intact.
      if (owner.reason) status.principles = channel('partial', null, [owner.reason]);
      else {
        plan.engineArgs.push('--append-system-prompt', joinText(owner.text, instructions));
        principles('append-system-prompt');
      }
      if (collisions.length || errors.length || skills.enableSkillCommands === false || skills.ignoredSkills?.length) {
        fallback([...collisions, ...errors], !owner.reason);
      } else native('skills.customDirectories', 'slash', '/skill:devlyn-ideate');
      break;
    }
    case 'pi': {
      const { agentDir } = piFolders(context.cwd, env);
      const settings = piSettings(context.cwd, agentDir);
      const owner = ownerAppend(config, () => piAppendFiles(context.cwd, agentDir, settings.user));
      if (owner.reason) status.principles = channel('partial', null, [owner.reason]);
      else {
        plan.engineArgs.push('--append-system-prompt', file('devlyn-instructions.md', joinText(owner.text, instructions)));
        principles('append-system-prompt');
      }
      // A discovered or settings-named skill wins over a --skill of the same name.
      const named = piNameCollisions(discoveryRoots(context, env, config), found);
      const reasons = [...collisions, ...named.collisions, ...errors, ...named.errors, ...settings.errors];
      if (reasons.length || [settings.user, settings.project].some((scope) => listed(scope, 'skills', 'packages'))) {
        fallback(reasons, !owner.reason);
      } else {
        for (const name of SKILLS) plan.engineArgs.push('--skill', path.join(release.root, 'config/skills', name));
        native('--skill', 'slash', '/skill:devlyn-ideate');
      }
      break;
    }
    case 'grok':
      plan.engineArgs.push('--rules', joinText(config.rules, instructions));
      principles('rules'); fallback();
      break;
    case 'qwen':
      plan.engineArgs.push('--append-system-prompt', joinText(config.appendSystemPrompt, instructions));
      principles('append-system-prompt'); fallback();
      break;
    case 'opencode': {
      let inline;
      try { inline = config.inlineConfig == null ? {} : JSON.parse(config.inlineConfig); }
      catch (error) { if (!(error instanceof SyntaxError)) throw error; inline = null; }
      const invalidField = !object(inline) || (inline.instructions !== undefined && !strings(inline.instructions))
        ? 'inlineConfig.instructions'
        : config.skillsPaths != null && inline.skills !== undefined && !object(inline.skills) ? 'inlineConfig.skills' : null;
      if (invalidField) {
        status.principles = channel('partial', null, [reason('config-unreadable', { field: invalidField })]);
        status.skills = channel('partial', null, [reason('config-unreadable', { field: invalidField })]);
        break;
      }
      if (Array.isArray(config.skillsPaths) && !collisions.length && !errors.length) {
        inline.skills = { ...inline.skills, paths: [...new Set([...config.skillsPaths, path.join(release.root, 'config/skills')])] };
        native('skills.paths', 'read-file', `Read ${path.join(release.root, 'config/skills/devlyn-ideate/SKILL.md')}`);
      } else fallback(config.skillsPaths == null ? [] : [...collisions, ...errors]);
      plan.envPatch.OPENCODE_CONFIG_CONTENT = JSON.stringify({ ...inline,
        instructions: [...(inline.instructions || []), file('devlyn-instructions.md', instructions)] });
      principles('OPENCODE_CONFIG_CONTENT.instructions');
      break;
    }
    case 'copilot': {
      const directory = path.join(context.runDir, 'copilot');
      if (directory.includes(',')) {
        status.principles = channel('unavailable', null, [reason('principles-unavailable', { detail: 'comma-in-path' })]);
      } else {
        file('copilot/devlyn.instructions.md', '---\napplyTo: "**"\n---\n' + instructions);
        const dirs = config.instructionsDirs ?? env.COPILOT_CUSTOM_INSTRUCTIONS_DIRS ?? '';
        plan.envPatch.COPILOT_CUSTOM_INSTRUCTIONS_DIRS = dirs.split(',').includes(directory) ? dirs : (dirs ? `${dirs},${directory}` : directory);
        principles('COPILOT_CUSTOM_INSTRUCTIONS_DIRS');
      }
      const root = path.join(release.root, 'config/skills');
      if (root.includes(',') || collisions.length || errors.length) {
        status.skills = channel('partial', null, root.includes(',') ? [reason('skills-unavailable', { detail: 'comma-in-path' })] : [...collisions, ...errors]);
        status.invocation = { kind: 'read-file', text: `Read ${path.join(root, 'devlyn-ideate/SKILL.md')}` };
      } else {
        const dirs = config.skillsDirs ?? env.COPILOT_SKILLS_DIRS ?? '';
        plan.envPatch.COPILOT_SKILLS_DIRS = dirs.split(',').includes(root) ? dirs : (dirs ? `${dirs},${root}` : root);
        native('COPILOT_SKILLS_DIRS', 'slash', '/devlyn-ideate');
      }
      break;
    }
    case 'kimi':
      if (continuation || config.ownerAgent) {
        status.principles = channel('partial', null, [reason('principles-unavailable', { launchMode: context.launchMode, ownerAgent: config.ownerAgent })]);
        status.skills = channel('partial', null, [reason('skills-unavailable', { launchMode: context.launchMode, ownerAgent: config.ownerAgent })]);
      } else {
        plan.engineArgs.push('--agent-file', file('devlyn-kimi.md', joinText('${base_prompt}', instructions)));
        principles('agent-file');
        const kimi = kimiSkillRoots(context, env);
        if (!collisions.length && !errors.length && !kimi.errors.length) {
          for (const root of [...kimi.roots, path.join(release.root, 'config/skills')]) plan.engineArgs.push('--skills-dir', root);
          native('--skills-dir', 'read-file', `Read ${path.join(release.root, 'config/skills/devlyn-ideate/SKILL.md')}`);
        } else fallback([...collisions, ...errors, ...kimi.errors]);
      }
      break;
    case 'antigravity': {
      // Antigravity reads AGENTS.md (always on) and .agents/skills in every workspace folder, and a folder given
      // by --add-dir is one. A conversation keeps its added folders and reads them from disk again on every
      // launch, so the plan is the same in every launch mode and a caller hands a resumed conversation the same
      // runDir: with another, both folders apply while the old one exists. A folder removed later only stops
      // applying. It truncates a rule file over 24,000 bytes.
      const gate = channelGate(context);
      if (gate) {
        firstTask(gate);
        break;
      }
      // The engine is given the resolved folder, the one the checks ran on.
      const folder = path.join(physicalPath(context.runDir), 'antigravity');
      const unsafe = unsafeRunDir(folder, true);
      if (unsafe) {
        firstTask(withheld({ detail: 'run-dir-unsafe', path: unsafe }));
        break;
      }
      const bytes = Buffer.byteLength(instructions), maximum = 24000;
      if (bytes > maximum) {
        status.principles = channel('unavailable', null, [reason('principles-unavailable', { detail: 'too-large', bytes, maximum })]);
      } else {
        file('antigravity/AGENTS.md', instructions);
        principles('add-dir');
      }
      if (collisions.length) fallback([...collisions, ...errors], bytes <= maximum);
      else {
        for (const name of SKILLS) file(`antigravity/.agents/skills/${name}/SKILL.md`, antigravitySkill(release, name));
        native('add-dir', 'slash', '/devlyn-ideate');
      }
      if (plan.files.length) plan.engineArgs.push('--add-dir', folder);
      break;
    }
    case 'cursor': {
      const gate = channelGate(context);
      if (gate) {
        firstTask(gate);
        break;
      }
      // A --plugin-dir folder's sessionStart command hook runs when a session is created, and Cursor puts the
      // additional_context it prints before the model as instructions, kept with the conversation (10,200
      // characters were delivered whole). A resumed chat runs no hook and keeps what its first launch had
      // (measured); a fork is treated the same way, because what it gets is not established. The hook is a
      // command Cursor runs, so it is planned only in a safe run directory, by its resolved absolute path, quoted
      // for the shell: no lookup through PATH or the working folder. The skills come from the release, whatever
      // the run directory.
      const hook = path.join(physicalPath(context.runDir), 'cursor');
      const unsafe = unsafeRunDir(hook);
      if (unsafe || !isFile('/bin/cat')) {
        firstTask(withheld(unsafe ? { detail: 'run-dir-unsafe', path: unsafe } : { detail: 'platform-unexamined' }));
      } else {
        const command = `/bin/cat '${path.join(hook, 'context.json').replace(/'/g, "'\\''")}'`;
        file('cursor/hooks/hooks.json', JSON.stringify({ version: 1, hooks: { sessionStart: [{ command }] } }) + '\n');
        // Every non-ASCII character escaped, so no shell or code page can change the text.
        file('cursor/context.json', JSON.stringify({ additional_context: instructions })
          .replace(/[\u0080-\uffff]/g, (character) => `\\u${character.charCodeAt(0).toString(16).padStart(4, '0')}`) + '\n');
        plan.engineArgs.push('--plugin-dir', hook);
        status.principles = continuation ? channel('partial', 'session-start-hook', [reason('principles-session-start-only')])
          : channel('configured', 'session-start-hook');
      }
      if (collisions.length) fallback([...collisions, ...errors], plan.files.length > 0 || plan.prompt !== null);
      else {
        plan.engineArgs.push('--plugin-dir', path.join(release.root, 'config'));
        native('plugin-dir', 'slash', '/devlyn-ideate');
      }
      break;
    }
  }
  if (plan.engineArgs.length || Object.keys(plan.envPatch).length || plan.prompt) plan.envPatch.DEVLYN_HARNESS_ROOT = release.root;
  return finish(plan);
}

function activationCommand(args) {
  const opts = options(args, { plan: { type: 'boolean' }, 'release-root': { type: 'string' }, 'context-file': { type: 'string' } });
  if (!opts.plan || !opts['release-root'] || !path.isAbsolute(opts['release-root']) || !opts['context-file']) {
    fail('invalid-arguments', { argument: 'plan, absolute release-root and context-file required' }, 2);
  }
  return planActivation(opts['release-root'], readContext(opts['context-file']));
}

module.exports = { planActivation, activationCommand, readContext, toml, skillCatalog, piFolders };
