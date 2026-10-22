const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { spawnSync } = require('child_process');
const { parseArgs } = require('util');
const { managedBody, managedBlock, sessionDefaults } = require('./instructions');

const PACKAGE_ROOT = path.resolve(__dirname, '..');
const CORE = ['devlyn-ideate', 'devlyn-engines', '_shared'];
const DEFAULTS = 'config/skills/_shared/runtime-principles.md';
const SHA256 = /^[a-f0-9]{64}$/;
const VERSION = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$/;

class HarnessError extends Error {
  constructor(code, params = {}, exitCode = 1) {
    super(`${code}: ${JSON.stringify(params)}`);
    this.reason = { code, params };
    this.exitCode = exitCode;
  }
}
function fail(code, params, exitCode) { throw new HarnessError(code, params, exitCode); }
const sha256 = (bytes) => crypto.createHash('sha256').update(bytes).digest('hex');
function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((k) => `${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}
function manifestDigest(manifest) {
  const { digest, ...body } = manifest;
  return sha256(canonical(body));
}
const jsonBytes = (value) => Buffer.from(JSON.stringify(value, null, 2) + '\n');

// POSIX manifest names must also be unambiguous on Windows and macOS volumes.
function validatePath(name) {
  if (typeof name !== 'string' || !name || /[\\\x00-\x1f\x7f:<>"|?*]/.test(name)
      || path.posix.isAbsolute(name) || path.win32.isAbsolute(name)
      || name.split('/').some((part) => !part || part === '.' || part === '..' || /[. ]$/.test(part)
        || /^(?:con|prn|aux|nul|com[1-9¹²³]|lpt[1-9¹²³])(?:\.|$)/i.test(part))) {
    fail('release-unsafe-path', { path: String(name) });
  }
}
function validatePaths(names) {
  const seen = new Map();
  const files = new Set();
  for (const name of names) {
    validatePath(name);
    if (files.has(name)) fail('release-duplicate-path', { path: name });
    files.add(name);
    const parts = name.split('/');
    for (let i = 1; i <= parts.length; i++) {
      const prefix = parts.slice(0, i).join('/');
      const folded = prefix.normalize('NFC').toUpperCase().toLowerCase().toUpperCase();
      if (seen.has(folded) && seen.get(folded) !== prefix) fail('release-case-collision', { path: name });
      seen.set(folded, prefix);
    }
  }
  for (const name of names) {
    const parts = name.split('/');
    for (let i = 1; i < parts.length; i++) {
      if (files.has(parts.slice(0, i).join('/'))) fail('release-path-conflict', { path: name });
    }
  }
}
function regular(file, directory = false) {
  const stat = fs.lstatSync(file);
  if (directory ? !stat.isDirectory() : !stat.isFile() || stat.nlink !== 1) {
    fail('release-unsafe-entry', { path: file });
  }
  return stat;
}
function physicalRoot(root) {
  if (typeof root !== 'string' || !path.isAbsolute(root)) fail('invalid-arguments', { argument: 'absolute path required' }, 2);
  regular(root, true);
  return fs.realpathSync(root);
}
function safeFile(root, relative) {
  validatePath(relative);
  const parts = relative.split('/');
  for (let i = 1; i < parts.length; i++) regular(path.join(root, ...parts.slice(0, i)), true);
  const file = path.join(root, ...parts);
  regular(file);
  return file;
}
function readJson(file) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); }
  catch (error) {
    if (error instanceof SyntaxError) fail('invalid-json', { path: file });
    throw error;
  }
}
function treeFiles(root, relative = '', npmInstall = false) {
  regular(path.join(root, relative), true);
  const files = [];
  for (const name of fs.readdirSync(path.join(root, relative)).sort()) {
    const rel = relative ? `${relative}/${name}` : name;
    validatePath(rel);
    const stat = fs.lstatSync(path.join(root, rel));
    if (stat.isDirectory()) {
      // npm generates these launch shims after unpacking. Mutable install sources
      // may contain them; immutable releases never do, and capture never copies them.
      if (npmInstall && rel === 'node_modules/.bin') continue;
      files.push(...treeFiles(root, rel, npmInstall));
    }
    else { regular(path.join(root, rel)); files.push(rel); }
  }
  validatePaths(files);
  return files.sort();
}
function packageMetadata(root) {
  const pkg = readJson(safeFile(root, 'package.json'));
  if (pkg.name !== 'devlyn-cli' || !VERSION.test(pkg.version) || typeof pkg.engines?.node !== 'string') {
    fail('release-schema', { field: 'package.json' }, 3);
  }
  return pkg;
}

function generatedArtifacts(root) {
  const pkg = packageMetadata(root);
  const template = fs.readFileSync(safeFile(root, 'CLAUDE.md'), 'utf8').replace(/\r\n/g, '\n');
  const agents = fs.readFileSync(safeFile(root, 'AGENTS.md'), 'utf8').replace(/\r\n/g, '\n');
  if (template !== agents || /<!-- devlyn:instructions:(?:begin|end)/.test(template)) {
    fail('release-template-mismatch', {});
  }
  const outputs = new Map();
  const put = (name, bytes, executable = false) => outputs.set(name, { bytes: Buffer.from(bytes), executable });
  put(DEFAULTS, sessionDefaults(template));
  put('harness/CLAUDE.md', managedBlock(template));
  put('harness/AGENTS.md', managedBlock(template));
  const plugin = { name: 'devlyn', version: pkg.version, description: 'Devlyn harness skills', skills: './skills/' };
  put('native/claude/.claude-plugin/plugin.json', jsonBytes(plugin));
  put('native/codex/plugins/devlyn/.codex-plugin/plugin.json', jsonBytes(plugin));
  put('native/codex/.agents/plugins/marketplace.json', jsonBytes({
    name: `devlyn-harness-v${pkg.version.replace(/\./g, '-')}`,
    plugins: [{ name: 'devlyn', source: { source: 'local', path: './plugins/devlyn' } }],
  }));
  for (const skill of CORE) {
    const source = `config/skills/${skill}`;
    for (const relative of treeFiles(path.join(root, source))) {
      // Python bytecode and OS metadata are not release inputs.
      if (relative.split('/').includes('__pycache__') || /(?:^|\/)(?:\.DS_Store|Thumbs\.db)$|\.pyc$/.test(relative)) continue;
      const name = `${source}/${relative}`;
      const file = safeFile(root, name);
      const bytes = outputs.get(name)?.bytes || fs.readFileSync(file);
      const executable = name === DEFAULTS ? false : Boolean(fs.statSync(file).mode & 0o111);
      for (const mirror of ['native/claude', 'native/codex/plugins/devlyn']) put(`${mirror}/skills/${skill}/${relative}`, bytes, executable);
    }
  }
  return outputs;
}

function checkGenerated(root) {
  const expected = generatedArtifacts(root);
  for (const [name, { bytes, executable }] of expected) {
    const file = safeFile(root, name);
    if (!fs.readFileSync(file).equals(bytes) || (process.platform !== 'win32' && Boolean(fs.statSync(file).mode & 0o111) !== executable)) {
      fail('release-generated-mismatch', { path: name });
    }
  }
  const actual = ['harness', 'native'].flatMap((dir) => treeFiles(path.join(root, dir)).map((name) => `${dir}/${name}`));
  if (actual.some((name) => !expected.has(name))) fail('release-generated-mismatch', { path: 'unlisted generated file' });
  return expected.size;
}

function metadata(root) {
  const pkg = packageMetadata(root);
  return {
    schemaVersion: 1, package: 'devlyn-cli', version: pkg.version,
    principles: { defaults: DEFAULTS, memory: { claude: 'harness/CLAUDE.md', agents: 'harness/AGENTS.md' },
      sourceBlockSha256: sha256(managedBody(fs.readFileSync(safeFile(root, 'CLAUDE.md'), 'utf8'))) },
    skills: { root: 'config/skills', names: CORE.slice(0, 2), support: '_shared',
      claudePlugin: 'native/claude', codexMarketplace: 'native/codex' },
    stateCompat: {
      loopManifest: { read: [1, 1], write: 1 }, addRecord: { read: [1, 1], write: 1 },
      // CLI-2 introduces packet v2 and queueBinding together with their implementations.
      taskPacket: { inspect: [1, 1], execute: [1, 1], write: 1 },
      submission: { read: [1, 1], write: 1 }, review: { read: [1, 1], write: 1 },
      acceptanceResult: { read: [1, 1], write: 1 }, invocationReceipt: { read: [1, 1], write: 1 },
      legacyFormats: ['completion-receipt-unversioned', 'direct-acceptance-unversioned',
        'expected-contract-unversioned', 'engines-config-unversioned', 'queue-markdown-inspect-only'],
    },
    requires: { node: pkg.engines.node, python: '>=3.11', git: true, windowsGitBash: true, githubDelivery: 'gh' },
  };
}

function writeArtifact(root, name, bytes, executable) {
  const parts = name.split('/');
  for (let i = 1; i < parts.length; i++) {
    const dir = path.join(root, ...parts.slice(0, i));
    if (!fs.existsSync(dir)) fs.mkdirSync(dir);
    regular(dir, true);
  }
  const file = path.join(root, name);
  if (fs.lstatSync(file, { throwIfNoEntry: false })) regular(file);
  fs.writeFileSync(file, bytes);
  fs.chmodSync(file, executable ? 0o755 : 0o644);
}

function buildRelease(root = PACKAGE_ROOT) {
  root = physicalRoot(root);
  // npm omits links from its inventory; reject them before that omission can hide an input.
  for (const dir of ['bin', 'config', 'optional-skills']) treeFiles(path.join(root, dir));
  const outputs = generatedArtifacts(root);
  // Generated roots are package-owned. Validate before removing stale mirror files.
  for (const dir of ['harness', 'native']) {
    if (fs.lstatSync(path.join(root, dir), { throwIfNoEntry: false })) {
      treeFiles(path.join(root, dir));
      fs.rmSync(path.join(root, dir), { recursive: true });
    }
  }
  for (const [name, { bytes, executable }] of outputs) writeArtifact(root, name, bytes, executable);
  // npm's own inventory includes the exact bundled dependency closure and pack exclusions.
  const npmCli = process.env.npm_execpath || (process.platform === 'win32'
    ? path.join(path.dirname(process.execPath), 'node_modules/npm/bin/npm-cli.js') : null);
  const result = spawnSync(npmCli ? process.execPath : 'npm', [
    ...(npmCli ? [npmCli] : []), 'pack', '--dry-run', '--ignore-scripts', '--json',
  ], { cwd: root, encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 });
  if (result.error || result.status !== 0) fail('release-pack-failed', { detail: result.error?.message || result.stderr.trim() });
  const packed = JSON.parse(result.stdout)[0];
  const names = packed.files.map((file) => file.path).filter((name) => name !== 'release.json').sort();
  validatePaths(names);
  const pkg = packageMetadata(root);
  for (const dependency of pkg.bundleDependencies) {
    if (!names.includes(`node_modules/${dependency}/package.json`)) fail('release-missing-dependency', { dependency });
  }
  const modes = new Map(packed.files.map((file) => [file.path, Boolean(file.mode & 0o111)]));
  const manifest = { ...metadata(root), files: names.map((name) => ({
    path: name, sha256: sha256(fs.readFileSync(safeFile(root, name))), executable: modes.get(name),
  })) };
  manifest.digest = { algorithm: 'sha256', value: manifestDigest(manifest) };
  writeArtifact(root, 'release.json', jsonBytes(manifest), false);
  return { manifestPath: path.join(root, 'release.json'), version: manifest.version,
    digest: manifest.digest.value, fileCount: manifest.files.length };
}

function checkNpmShims(root, files) {
  const dir = path.join(root, 'node_modules/.bin');
  if (!fs.lstatSync(dir, { throwIfNoEntry: false })) return;
  regular(dir, true);
  const names = new Set(files.map((file) => file.path));
  const targets = new Map();
  for (const file of files) {
    if (!/^node_modules\/(?:@[^/]+\/)?[^/]+\/package\.json$/.test(file.path)) continue;
    const pkg = readJson(safeFile(root, file.path));
    const bins = typeof pkg.bin === 'string' ? { [pkg.name.split('/').at(-1)]: pkg.bin } : pkg.bin || {};
    for (const [name, relative] of Object.entries(bins)) {
      validatePath(name);
      if (name.includes('/') || typeof relative !== 'string') fail('release-schema', { field: 'dependency bin' }, 3);
      const target = path.posix.normalize(`${path.posix.dirname(file.path)}/${relative}`);
      validatePath(target);
      if (!names.has(target)) fail('release-file-list-mismatch', { path: target });
      for (const shim of [name, `${name}.cmd`, `${name}.ps1`]) {
        if (!targets.has(shim)) targets.set(shim, new Set());
        targets.get(shim).add(path.join(root, target));
      }
    }
  }
  for (const name of fs.readdirSync(dir)) {
    const file = path.join(dir, name);
    const stat = fs.lstatSync(file);
    if (!targets.has(name)) fail('release-file-list-mismatch', { path: `node_modules/.bin/${name}` });
    if (stat.isSymbolicLink()) {
      if (!targets.get(name).has(path.resolve(dir, fs.readlinkSync(file)))) fail('release-unsafe-entry', { path: file });
    } else regular(file); // Windows shims are regular files; never execute or copy them.
  }
}

function verifyRelease(root, { npmInstall = false } = {}) {
  root = physicalRoot(root);
  const manifest = readJson(safeFile(root, 'release.json'));
  if (!manifest || manifest.schemaVersion !== 1 || manifest.package !== 'devlyn-cli'
      || !VERSION.test(manifest.version) || manifest.digest?.algorithm !== 'sha256'
      || !SHA256.test(manifest.digest?.value) || !Array.isArray(manifest.files)
      || !manifest.files.every((f) => f && typeof f.path === 'string' && SHA256.test(f.sha256) && typeof f.executable === 'boolean')) {
    fail('release-schema', { path: 'release.json' }, 3);
  }
  const names = manifest.files.map((file) => file.path);
  validatePaths([...names, 'release.json']);
  if (canonical(names) !== canonical([...names].sort())) fail('release-schema', { field: 'files order' }, 3);
  if (manifestDigest(manifest) !== manifest.digest.value) fail('release-digest-mismatch', { path: 'release.json' });
  const actual = treeFiles(root, '', npmInstall).filter((name) => name !== 'release.json');
  if (canonical(actual) !== canonical(names)) fail('release-file-list-mismatch', {});
  for (const file of manifest.files) {
    const full = safeFile(root, file.path);
    if (sha256(fs.readFileSync(full)) !== file.sha256) fail('release-file-digest-mismatch', { path: file.path });
    // Windows has no POSIX execute bit; its declared mode is retained in the digest.
    if (process.platform !== 'win32' && Boolean(fs.statSync(full).mode & 0o111) !== file.executable) {
      fail('release-mode-mismatch', { path: file.path });
    }
  }
  if (npmInstall) checkNpmShims(root, manifest.files);
  const { files, digest, ...declared } = manifest;
  if (canonical(declared) !== canonical(metadata(root))) fail('release-schema', { field: 'metadata' }, 3);
  checkGenerated(root);
  return { release: { package: 'devlyn-cli', version: manifest.version, digest: digest.value, root }, valid: true };
}

function materializeRelease(source, store) {
  const verified = verifyRelease(source, { npmInstall: true }).release;
  if (!path.isAbsolute(store)) fail('invalid-arguments', { argument: 'absolute store required' }, 2);
  // Check every existing store component before mkdir; never write through a store link.
  const missing = [];
  let parent = path.resolve(store);
  while (!fs.lstatSync(parent, { throwIfNoEntry: false })) { missing.push(parent); parent = path.dirname(parent); }
  regular(parent, true);
  for (let dir = parent; dir !== path.dirname(dir); dir = path.dirname(dir)) regular(dir, true);
  for (const dir of missing.reverse()) { fs.mkdirSync(dir, { recursive: true }); regular(dir, true); }
  store = physicalRoot(store);
  const packageDir = path.join(store, 'devlyn-cli');
  fs.mkdirSync(packageDir, { recursive: true });
  regular(packageDir, true);
  const target = path.join(packageDir, verified.version);
  const existing = () => {
    const release = verifyRelease(target).release;
    if (release.digest !== verified.digest) fail('release-version-conflict', { version: release.version }, 3);
    return { release, created: false };
  };
  if (fs.lstatSync(target, { throwIfNoEntry: false })) return existing();
  const temp = fs.mkdtempSync(path.join(packageDir, `.${verified.version}-`));
  try {
    const manifest = readJson(safeFile(verified.root, 'release.json'));
    for (const file of [...manifest.files, { path: 'release.json', executable: false }]) {
      writeArtifact(temp, file.path, fs.readFileSync(safeFile(verified.root, file.path)), file.executable);
    }
    const captured = verifyRelease(temp).release;
    if (captured.digest !== verified.digest) fail('release-source-changed', {}, 3);
    try { fs.renameSync(temp, target); }
    catch (error) {
      if (['EEXIST', 'ENOTEMPTY', 'EPERM', 'EACCES'].includes(error.code) && fs.existsSync(target)) return existing();
      throw error;
    }
    return { release: { ...captured, root: target }, created: true };
  } finally {
    fs.rmSync(temp, { recursive: true, force: true });
  }
}

function options(args, definitions) {
  try { return parseArgs({ args, options: { json: { type: 'boolean' }, ...definitions }, strict: true }).values; }
  catch (error) { fail('invalid-arguments', { detail: error.message }, 2); }
}
function releaseCommand(args) {
  const opts = options(args, Object.fromEntries(['build', 'verify', 'materialize', 'root', 'source', 'store']
    .map((key) => [key, { type: ['build', 'verify', 'materialize'].includes(key) ? 'boolean' : 'string' }])));
  const actions = ['build', 'verify', 'materialize'].filter((key) => opts[key]);
  const allowed = { build: ['build', 'json'], verify: ['verify', 'root', 'json'], materialize: ['materialize', 'source', 'store', 'json'] };
  if (actions.length !== 1 || Object.keys(opts).some((key) => !allowed[actions[0]].includes(key))
      || (opts.verify && !opts.root) || (opts.materialize && (!opts.source || !opts.store))) fail('invalid-arguments', {}, 2);
  if (opts.build) return buildRelease();
  if (opts.verify) return verifyRelease(opts.root);
  return materializeRelease(opts.source, opts.store);
}
function runJson(action) {
  try { process.stdout.write(JSON.stringify({ schemaVersion: 1, ok: true, data: action() }) + '\n'); }
  catch (error) {
    const reason = error instanceof HarnessError ? error.reason
      : { code: 'operation-failed', params: { detail: error.message, ...(error.code ? { systemCode: error.code } : {}) } };
    process.stderr.write(`${reason.code}: ${JSON.stringify(reason.params)}\n`);
    process.stdout.write(JSON.stringify({ schemaVersion: 1, ok: false, error: reason }) + '\n');
    process.exitCode = error instanceof HarnessError ? error.exitCode : 1;
  }
}

module.exports = { buildRelease, verifyRelease, materializeRelease, checkGenerated,
  sha256, physicalRoot, HarnessError, fail,
  options, releaseCommand, runJson };
