const fs = require('fs');
const path = require('path');
const { verifyRelease, physicalRoot, sha256, manifestDigest, fail, options } = require('./release');

const MARKER = '.devlyn-harness-projection.json';
const SOURCE = 'native/codex/plugins/devlyn';
const marketplaceName = (release) => `devlyn-harness-v${release.version.replace(/\./g, '-')}`;
const projectionPath = (release, accountHome, paths = path) =>
  paths.join(accountHome, 'plugins', 'cache', marketplaceName(release), 'devlyn', release.version);
const markerBytes = (release) => Buffer.from(JSON.stringify({ schemaVersion: 1, release, source: SOURCE }, null, 2) + '\n');

function conflict(file) { fail('name-collision', { path: file, kind: 'codex-projection' }, 3); }

// Account homes may have physical aliases (e.g. /var on macOS). Below that
// explicitly selected root, never follow a link or adopt a foreign cache entry.
function cacheParent(accountHome, release, create) {
  let dir = physicalRoot(accountHome);
  for (const part of ['plugins', 'cache', marketplaceName(release), 'devlyn']) {
    dir = path.join(dir, part);
    if (create) {
      try { fs.mkdirSync(dir); }
      catch (error) { if (error.code !== 'EEXIST') throw error; }
    }
    const stat = fs.lstatSync(dir, { throwIfNoEntry: false });
    if (!stat && !create) return null;
    if (!stat?.isDirectory()) conflict(dir);
  }
  return dir;
}

function projectionEntries(release) {
  const manifest = JSON.parse(fs.readFileSync(path.join(release.root, 'release.json'), 'utf8'));
  if (manifest.digest?.value !== release.digest || manifestDigest(manifest) !== release.digest) {
    fail('release-source-changed', { path: release.root }, 3);
  }
  const entries = manifest.files.filter((entry) => entry.path.startsWith(`${SOURCE}/`))
    .map((entry) => ({ ...entry, path: entry.path.slice(SOURCE.length + 1) }));
  if (!entries.some((entry) => entry.path === '.codex-plugin/plugin.json')) conflict(release.root);
  return entries;
}

function verifyProjection(root, release) {
  const entries = projectionEntries(release);
  const expected = new Map(entries.map((entry) => [entry.path, entry]));
  expected.set(MARKER, { sha256: sha256(markerBytes(release)), executable: false });
  const directories = new Set(['']);
  for (const name of expected.keys()) {
    const parts = name.split('/');
    for (let i = 1; i < parts.length; i++) directories.add(parts.slice(0, i).join('/'));
  }
  const seen = new Set();
  function visit(relative) {
    const full = path.join(root, relative);
    const stat = fs.lstatSync(full, { throwIfNoEntry: false });
    if (stat?.isDirectory() && directories.has(relative)) {
      for (const name of fs.readdirSync(full)) visit(relative ? `${relative}/${name}` : name);
    } else {
      const entry = expected.get(relative);
      if (!entry || !stat?.isFile() || stat.nlink !== 1
          || sha256(fs.readFileSync(full)) !== entry.sha256
          || (process.platform !== 'win32' && Boolean(stat.mode & 0o111) !== entry.executable)) conflict(full);
      seen.add(relative);
    }
  }
  visit('');
  if (seen.size !== expected.size) conflict(root);
  return { projectionRoot: root, markerSha256: expected.get(MARKER).sha256 };
}

function inspectProjection(release, accountHome) {
  const parent = cacheParent(accountHome, release, false);
  if (!parent) return null;
  const root = path.join(parent, release.version);
  if (!fs.lstatSync(root, { throwIfNoEntry: false })) return null;
  return verifyProjection(root, release);
}

function syncProjection(releaseRoot, accountHome) {
  const release = verifyRelease(releaseRoot).release;
  const account = physicalRoot(accountHome);
  const relative = path.relative(release.root, account);
  if (!relative || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))) {
    fail('invalid-arguments', { argument: 'account-home must be outside the release' }, 2);
  }
  const parent = cacheParent(account, release, true);
  const target = path.join(parent, release.version);
  const existing = () => ({ release, ...verifyProjection(target, release), created: false });
  if (fs.lstatSync(target, { throwIfNoEntry: false })) return existing();
  // A short exclusive publication lock prevents two CLI publishers from
  // replacing each other's cache. Interrupted locks are explicit conflicts;
  // they are never guessed stale or reaped by age/PID.
  const lock = path.join(parent, `.${release.version}.lock`);
  let lockFd;
  try { lockFd = fs.openSync(lock, 'wx', 0o600); }
  catch (error) { if (error.code === 'EEXIST') conflict(lock); throw error; }
  let temp;
  try {
    if (fs.lstatSync(target, { throwIfNoEntry: false })) return existing();
    temp = fs.mkdtempSync(path.join(parent, `.${release.version}-`));
    for (const entry of projectionEntries(release)) {
      const dest = path.join(temp, entry.path);
      fs.mkdirSync(path.dirname(dest), { recursive: true });
      fs.copyFileSync(path.join(release.root, SOURCE, entry.path), dest, fs.constants.COPYFILE_EXCL);
      fs.chmodSync(dest, entry.executable ? 0o755 : 0o644);
    }
    fs.writeFileSync(path.join(temp, MARKER), markerBytes(release), { flag: 'wx', mode: 0o644 });
    verifyProjection(temp, release);
    if (fs.lstatSync(target, { throwIfNoEntry: false })) return existing();
    fs.renameSync(temp, target);
    return { release, ...verifyProjection(target, release), created: true };
  } finally {
    if (temp) fs.rmSync(temp, { recursive: true, force: true });
    fs.closeSync(lockFd);
    fs.unlinkSync(lock);
  }
}

function machineCommand(args) {
  if (args[0] !== 'sync') fail('invalid-arguments', { argument: 'machine sync' }, 2);
  const opts = options(args.slice(1), {
    'release-root': { type: 'string' }, engine: { type: 'string' }, 'account-home': { type: 'string' },
  });
  if (opts.engine !== 'codex' || !opts['release-root'] || !opts['account-home']) {
    fail('invalid-arguments', { argument: 'release-root, engine=codex and account-home required' }, 2);
  }
  return syncProjection(opts['release-root'], opts['account-home']);
}

module.exports = { MARKER, marketplaceName, projectionPath, inspectProjection, verifyProjection, syncProjection, machineCommand };
