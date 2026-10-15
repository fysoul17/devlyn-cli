#!/usr/bin/env node
// Refresh offline ownership fingerprints from local mainline and tagged skill trees.
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');
const { fingerprint } = require('../bin/skill-ownership');

const root = path.join(__dirname, '..');
const historyPath = path.join(root, 'bin/skill-history.json');
const history = JSON.parse(fs.readFileSync(historyPath, 'utf8'));
const git = (...args) => execFileSync('git', args, { cwd: root, maxBuffer: 32 * 1024 * 1024 });
if (git('rev-parse', '--is-shallow-repository').toString().trim() !== 'false') {
  throw new Error('Skill history requires a complete Git checkout (fetch-depth: 0).');
}
const commits = new Set([
  ...git('log', '--first-parent', '--full-history', '--format=%H', 'HEAD', '--',
    'config/skills', 'optional-skills').toString().trim().split('\n'),
  ...git('log', '--no-walk', '--tags', '--format=%H').toString().trim().split('\n'),
].filter(Boolean));
const skills = new Map();
const fingerprints = new Map();
const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'devlyn-skill-history-'));
try {
  for (const commit of commits) {
    const trees = git('ls-tree', '-d', '-z', commit, '--', 'config/skills/', 'optional-skills/');
    for (const entry of trees.toString('utf8').split('\0').filter(Boolean)) {
      const [header, file] = entry.split('\t');
      const tree = header.split(' ')[2];
      const name = path.posix.basename(file).replace(/[:\uF03A]/g, '-');
      if (!fingerprints.has(tree)) {
        // Materialize each distinct tree once so history uses the installer's exact walker,
        // including directory entries, stamp normalization and ignored generated files.
        const dir = path.join(scratch, tree);
        const archive = path.join(scratch, `${tree}.tar`);
        fs.mkdirSync(dir);
        git('archive', '--format=tar', `--output=${archive}`, tree);
        execFileSync('tar', ['-xf', archive, '-C', dir]);
        fs.unlinkSync(archive);
        fingerprints.set(tree, fingerprint(dir));
      }
      if (!skills.has(name)) skills.set(name, new Set());
      skills.get(name).add(fingerprints.get(tree));
    }
  }
} finally {
  fs.rmSync(scratch, { recursive: true, force: true });
}
history.source = 'skills: config/skills/* and optional-skills/* trees from every first-parent HEAD commit '
  + 'touching those paths and every local tag, derived by scripts/update-skill-history.js using '
  + 'bin/skill-ownership.js normalization (LF, install-path stamps, OS metadata and Python bytecode)';
history.skills = Object.fromEntries([...skills.keys()].sort()
  .map((name) => [name, [...skills.get(name)].sort()]));
fs.writeFileSync(historyPath, JSON.stringify(history, null, 2) + '\n');
console.log(`Skill history: ${skills.size} names, ${fingerprints.size} distinct Git trees.`);
