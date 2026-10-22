const fs = require('fs');
const os = require('os');
const path = require('path');
const { ENGINE_IDS, ENGINE_CAPABILITIES, supportedVersion } = require('./engines');
const { verifyRelease, sha256, fail, options, HarnessError } = require('./release');
const { fingerprint } = require('./skill-ownership');
const history = require('./skill-history.json');
const { MARKER, marketplaceName, projectionPath, inspectProjection } = require('./codex-projection');

const SKILLS = ['devlyn-ideate', 'devlyn-engines'];
const object = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);
const textValue = (value) => typeof value === 'string' && !value.includes('\0');
const strings = (value) => Array.isArray(value) && value.every(textValue);
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
    opencode: ['inlineConfig'], kimi: ['ownerAgent'], copilot: ['skillsDirs'], qwen: ['appendSystemPrompt'],
  }[context.engine];
  if (!object(config) || Object.keys(config).some((key) => !keys.includes(key))) return null;
  for (const field of ['appendSystemPrompt', 'developer_instructions', 'rules', 'inlineConfig', 'skillsDirs']) {
    if (config[field] !== undefined && config[field] !== null && !textValue(config[field])) return null;
  }
  if (context.engine === 'kimi' && typeof config.ownerAgent !== 'boolean') return null;
  if (config.pluginDirs !== undefined && (!strings(config.pluginDirs) || !config.pluginDirs.every(path.isAbsolute))) return null;
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

function discoveryRoots(context, env, config) {
  const home = env.HOME || env.USERPROFILE || os.homedir();
  const roots = [...(context.skillRoots || [])];
  const add = (base, ...parts) => { if (base) roots.push(path.resolve(base, ...parts)); };
  const engine = context.engine;
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
  }[engine];
  if (engine !== 'codex') add(native[0], 'skills');
  const copilotDefaultHome = !env.COPILOT_HOME || path.resolve(env.COPILOT_HOME) === path.join(home, '.copilot');
  if (!['claude', 'cursor'].includes(engine) && (engine !== 'copilot' || copilotDefaultHome)) add(home, '.agents/skills');
  if (['omp', 'opencode', 'grok'].includes(engine)) add(home, '.claude/skills');
  if (engine === 'omp') {
    add(home, '.codex/skills'); add(home, '.agent/skills');
    for (const dir of config?.skills?.customDirectories || []) add(context.cwd, dir);
  }
  if (engine === 'codex' && process.platform !== 'win32') add('/etc/codex', 'skills');
  if (engine === 'opencode') add(env.OPENCODE_CONFIG_DIR, 'skills');
  if (engine === 'copilot') for (const dir of (config?.skillsDirs ?? env.COPILOT_SKILLS_DIRS ?? '').split(',').filter(Boolean)) add(context.cwd, dir);
  for (let dir = path.resolve(context.cwd); ; dir = path.dirname(dir)) {
    if (native[1]) add(dir, native[1], 'skills');
    if (!['claude', 'cursor'].includes(engine)) add(dir, '.agents/skills');
    if (['grok', 'omp', 'opencode', 'copilot'].includes(engine)) add(dir, '.claude/skills');
    if (['omp', 'antigravity'].includes(engine)) add(dir, '.agent/skills');
    if (fs.existsSync(path.join(dir, '.git')) || dir === path.dirname(dir)) break;
  }
  return [...new Set(roots)];
}

function inspectSkills(context, release, env, config) {
  const found = [], errors = [], hashes = new Map();
  for (const root of discoveryRoots(context, env, config)) {
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
    'Use that absolute folder wherever the Devlyn defaults name _shared/, including the Quick Start references to .claude/skills/ or .agents/skills/.',
  ].join('\n');
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
  if (continuation && context.recordedRelease === undefined) {
    status.principles = channel('partial', null, [reason('principles-unavailable', { launchMode: context.launchMode, detail: 'recorded-binding-missing' })]);
    status.skills = channel('partial', null, [reason('skills-unavailable', { launchMode: context.launchMode, detail: 'recorded-binding-missing' })]);
    return finish(plan);
  }
  const off = continuation ? context.recordedRelease === null : context.projectChoice === 'none';
  const release = verifyRelease(continuation && !off ? context.recordedRelease.root : releaseRoot).release;
  if (continuation && !off && (release.digest !== context.recordedRelease.digest || release.version !== context.recordedRelease.version)) {
    fail('release-version-conflict', { version: context.recordedRelease.version }, 3);
  }
  const config = effectiveConfig(context);
  const { found, errors } = inspectSkills(context, release, env, config);
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
    const reasons = [reason('engine-version-unsupported', { minimum: ENGINE_CAPABILITIES[context.engine].minimum })];
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
  const defaults = context.committedBlockApplies ? '' : fs.readFileSync(path.join(release.root, 'config/skills/_shared/runtime-principles.md'), 'utf8');
  const catalog = skillCatalog(release);
  const instructions = joinText(defaults, catalog);
  const file = (relativePath, utf8) => {
    let parent = path.resolve(context.runDir);
    const missing = [];
    while (!fs.existsSync(parent)) { missing.unshift(path.basename(parent)); parent = path.dirname(parent); }
    const physical = path.join(fs.realpathSync(parent), ...missing);
    const relative = path.relative(release.root, physical);
    if (!relative || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))) {
      fail('invalid-arguments', { argument: 'runDir must be outside the release' }, 2);
    }
    plan.files.push({ relativePath, utf8, sha256: sha256(utf8) });
    return path.join(context.runDir, relativePath);
  };
  const principles = (mechanism) => { status.principles = channel('configured', context.committedBlockApplies ? 'native-project' : mechanism); };
  const fallback = (reasons = []) => {
    status.skills = channel('partial', 'absolute-catalog', [...reasons, reason('skills-catalog')]);
    status.invocation = { kind: 'read-file', text: `Read ${path.join(release.root, 'config/skills/devlyn-ideate/SKILL.md')}` };
  };
  const native = (mechanism, kind, text) => { status.skills = channel('configured', mechanism); status.invocation = { kind, text }; };
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
      plan.engineArgs.push('--config', file('devlyn-omp.json', JSON.stringify({ skills }, null, 2) + '\n'),
        '--append-system-prompt', joinText(config.appendSystemPrompt, instructions));
      principles('append-system-prompt');
      if (collisions.length || errors.length || skills.enableSkillCommands === false || skills.ignoredSkills?.length) fallback([...collisions, ...errors]);
      else native('skills.customDirectories', 'slash', '/skill:devlyn-ideate');
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
      if (!object(inline) || (inline.instructions !== undefined && !strings(inline.instructions))) {
        status.principles = channel('partial', null, [reason('config-unreadable', { field: 'inlineConfig.instructions' })]);
        status.skills = channel('partial', null, [reason('config-unreadable', { field: 'inlineConfig.instructions' })]);
        break;
      }
      plan.envPatch.OPENCODE_CONFIG_CONTENT = JSON.stringify({ ...inline,
        instructions: [...(inline.instructions || []), file('devlyn-instructions.md', instructions)] });
      principles('OPENCODE_CONFIG_CONTENT.instructions'); fallback();
      break;
    }
    case 'copilot': {
      status.principles = context.committedBlockApplies ? channel('configured', 'native-project')
        : channel('unavailable', null, [reason('principles-unavailable')]);
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
        principles('agent-file'); fallback();
      }
      break;
    case 'antigravity':
    case 'cursor':
      status.principles = channel('partial', context.initialPrompt ? 'initial-task' : null, [reason('principles-task-only')]);
      if (context.initialPrompt) {
        plan.prompt = { ...context.initialPrompt, text: joinText(instructions, context.initialPrompt.text) };
        fallback();
      } else status.skills = channel('partial', null, [reason('skills-unavailable', { detail: 'no-initial-task' })]);
      break;
  }
  if (context.committedBlockApplies) status.principles = channel('configured', 'native-project');
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

module.exports = { planActivation, activationCommand, readContext, toml, skillCatalog };
