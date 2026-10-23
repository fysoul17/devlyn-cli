#!/usr/bin/env node
// Ownership evidence for retired files: derive bytes from Git, never from their names alone.
const fs = require('fs');
const path = require('path');
const os = require('os');
const { contentHash } = require('../bin/skill-ownership');
const crypto = require('crypto');
const { execFileSync } = require('child_process');
const root = path.join(__dirname, '..');
// Every place a release carried devlyn.*.md commands from: config/, and before it .claude/, commands/ and optional-commands/.
const SOURCES = ['config', 'agents-config', 'optional-skills', '.claude/commands', 'commands', 'optional-commands'];
const git = (...args) => execFileSync('git', args, { cwd: root, encoding: 'utf8', maxBuffer: 32 * 1024 * 1024 });
if (git('rev-parse', '--is-shallow-repository').trim() !== 'false') throw new Error('Cleanup history needs full Git history.');
// Release tags only: a clone's own tags must not change what ships.
const commits = new Set([
  ...git('log', '--first-parent', '--format=%H', 'HEAD', '--', ...SOURCES).trim().split('\n'),
  ...git('log', '--no-walk', '--tags=v[0-9]*', '--format=%H').trim().split('\n'),
].filter(Boolean));
const commandHashes = new Map();
const blobs = new Map(), files = {}, commands = {}, skills = {}, optionalSkills = {}, evaluators = new Map();
const add = (map, name, hash) => (map[name] ??= new Set()).add(hash);
const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'devlyn-cleanup-history-'));
try {
  for (const commit of commits) {
    const entries = git('ls-tree', '-r', '-z', commit, '--', ...SOURCES.map((source) => `${source}/`)).split('\0').filter(Boolean)
      .map((entry) => { const [header, name] = entry.split('\t'); return { name, blob: header.split(' ')[2] }; });
    for (const { name, blob } of entries) {
      if (/^(?:config\/commands|\.claude\/commands|commands|optional-commands\/[^/]+)\/devlyn\.[^/]+\.md$/.test(name)) {
        if (!commandHashes.has(blob)) {
          const file = path.join(scratch, 'command.md');
          fs.writeFileSync(file, execFileSync('git', ['show', `${commit}:${name}`], { cwd: root }));
          commandHashes.set(blob, contentHash(file));
        }
        add(commands, path.posix.basename(name).toLowerCase(), commandHashes.get(blob));
      }
      const skill = /^config\/skills\/([^/]+)\/SKILL.md$/.exec(name)?.[1];
      const optional = /^optional-skills\/([^/]+)\/SKILL.md$/.exec(name)?.[1];
      const evaluator = /^(?:config\/agents|agents-config)\/evaluator\.md$/.test(name);
      const file = /^config\/(?:templates\/|commit-conventions\.md$)/.test(name);
      if (!optional && !evaluator && !file && (!skill || skill.startsWith('devlyn')
          || entries.filter((entry) => entry.name.startsWith(`config/skills/${skill}/`)).length !== 1)) continue;
      if (!blobs.has(blob)) {
        const text = git('show', blob).replace(/\r\n/g, '\n');
        blobs.set(blob, { text, sha256: crypto.createHash('sha256').update(text).digest('hex') });
      }
      const { text, sha256 } = blobs.get(blob);
      if (skill) add(skills, skill.toLowerCase(), sha256);
      if (optional) add(optionalSkills, optional.toLowerCase(), sha256);
      if (file) add(files, '.claude/' + name.slice('config/'.length), sha256);
      if (evaluator) {
        for (const folder of ['.claude/agents', '.cursor/rules', '.github/copilot/agents', '.windsurf/rules']) {
          add(files, folder + '/evaluator.md', sha256);
        }
        const appended = '\n\n---\n\n# Devlyn Agent Instructions\n\n' + text + '\n';
        const hash = crypto.createHash('sha256').update(appended).digest('hex');
        evaluators.set(hash, { length: appended.length, sha256: hash });
      }
    }
  }
} finally { fs.rmSync(scratch, { recursive: true, force: true }); }
// Optional installs are indistinguishable from historical defaults with the same bytes.
for (const [name, hashes] of Object.entries(skills)) {
  for (const hash of optionalSkills[name] || []) hashes.delete(hash);
  if (!hashes.size) delete skills[name];
}
// Bundled upstream Vercel bytes cannot prove devlyn ownership of an independent install.
delete skills['web-design-guidelines'];
const sorted = (map) => Object.fromEntries(Object.keys(map).sort().map((name) => [name, [...map[name]].sort()]));
const result = { source: 'scripts/update-cleanup-history.js: LF-normalized Git blobs from first-parent config/agents-config/optional-skills history and release tags; excludes optional-addon hashes and third-party web-design-guidelines; commands: devlyn.*.md from config/commands, .claude/commands, commands and optional-commands/* in the same commits via skill-ownership.contentHash',
  files: sorted(files), commands: sorted(commands), skills: sorted(skills), evaluators: [...evaluators.values()].sort((a, b) => a.sha256.localeCompare(b.sha256)) };
const output = JSON.stringify(result, null, 2) + '\n';
const target = path.join(root, 'bin/cleanup-history.json');
if (process.argv.includes('--check')) {
  if (fs.readFileSync(target, 'utf8') !== output) throw new Error('Cleanup history drift; run node scripts/update-cleanup-history.js');
} else fs.writeFileSync(target, output);
console.log(`Cleanup history: ${Object.keys(files).length} files, ${Object.keys(commands).length} commands, ${Object.keys(skills).length} generic skills, ${evaluators.size} evaluator blocks.`);
