const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

// A folder-metadata file the OS writes on its own (Finder, Explorer); never user content.
// Only a regular file: a folder or link under that name is still the user's.
function isOsMetadata(full) {
  return ['.DS_Store', 'Thumbs.db'].includes(path.basename(full))
    && fs.lstatSync(full, { throwIfNoEntry: false })?.isFile() === true;
}

// SHA-256 of a file with CRLF read as LF: Git for Windows checks text out with CRLF by
// default, and an unedited clone must still match its shipped copy.
function contentHash(file) {
  const bytes = fs.readFileSync(file).toString('latin1').replace(/\r\n/g, '\n');
  return crypto.createHash('sha256').update(bytes, 'latin1').digest('hex');
}

// Hash every entry, including empty directories and dotfiles, except OS metadata. Links and
// special files are never installer-owned.
function fingerprint(dir) {
  const entries = [];
  function visit(full, relative) {
    const stat = fs.lstatSync(full);
    if (stat.isDirectory()) {
      entries.push([relative, 'directory']);
      for (const name of fs.readdirSync(full).sort()) {
        if (isOsMetadata(path.join(full, name))) continue;
        visit(path.join(full, name), relative ? `${relative}/${name}` : name);
      }
    } else if (stat.isFile()) {
      entries.push([relative, 'file', contentHash(full)]);
    } else {
      throw new Error(`link or special file: ${full}`);
    }
  }
  if (!fs.lstatSync(dir).isDirectory()) throw new Error('not a real directory');
  visit(dir, '');
  return crypto.createHash('sha256').update(JSON.stringify(entries)).digest('hex');
}

// Use the index, not status: even files deleted locally need ownership checks.
// Inspect the repository containing this root, including global dotfiles repos.
function trackedPaths(root) {
  let cwd = root;
  while (!fs.existsSync(cwd)) cwd = path.dirname(cwd);
  const env = { ...process.env, LC_ALL: 'C' };
  for (const key of ['GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR',
    'GIT_LITERAL_PATHSPECS', 'GIT_GLOB_PATHSPECS', 'GIT_NOGLOB_PATHSPECS', 'GIT_ICASE_PATHSPECS',
    'GIT_CEILING_DIRECTORIES', 'GIT_DISCOVERY_ACROSS_FILESYSTEM']) delete env[key];
  const git = (args) => spawnSync('git', ['-C', cwd, ...args], { encoding: 'utf8', env });
  const repo = git(['rev-parse', '--show-toplevel']);
  if (repo.error?.code === 'ENOENT') return [];
  if (repo.error) throw repo.error;
  if (repo.status !== 0) {
    if (repo.status === 128 && repo.stderr.includes('not a git repository')) return [];
    throw new Error(`cannot inspect Git ownership: ${repo.stderr.trim()}`);
  }
  // Conservative case folding also protects index spellings on macOS/Windows volumes.
  const files = git(['ls-files', '--full-name', '-z', '--', `:(icase,literal)${root}`]);
  if (files.error) throw files.error;
  if (files.status !== 0) throw new Error(`cannot inspect Git index: ${files.stderr.trim()}`);
  return files.stdout.split('\0').filter(Boolean).map((file) => path.resolve(repo.stdout.trim(), file));
}

module.exports = { contentHash, fingerprint, isOsMetadata, trackedPaths };
