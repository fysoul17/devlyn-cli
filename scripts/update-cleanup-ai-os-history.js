#!/usr/bin/env node
// Re-derive the private, frozen AI OS evidence. Only hashes and provenance leave this process.
// node scripts/update-cleanup-ai-os-history.js /path/to/agent-devlyn-v1 [--check]
const fs = require('fs');
const path = require('path');
const os = require('os');
const vm = require('vm');
const crypto = require('crypto');
const { execFileSync } = require('child_process');
const { contentHash } = require('../bin/skill-ownership');
const revision = 'd251b04141134589fb811dd5a0f2e99feef701e1';
const repo = process.argv[2];
if (!repo || repo.startsWith('--')) throw new Error('Supply a local agent-devlyn-v1 checkout.');
const git = (...args) => execFileSync('git', ['-C', repo, ...args], { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
if (git('rev-parse', '--is-shallow-repository').trim() !== 'false') throw new Error('Full AI OS history required.');
const roots = ['devlyn/src', 'devlyn-cli/src', 'src/lib/jarvis/hooks-generator.ts',
  'src/worker/hooks-setup.ts', 'src/lib/jarvis/wizard/agent-installer.ts'];
const commands = {}, hooks = {}, directories = new Set(['.claude/commands', '.gemini/commands']);
const add = (map, key, value) => (map[key] ??= new Set()).add(value);
const sorted = (map) => Object.fromEntries(Object.keys(map).sort().map((key) => [key, [...map[key]].sort()]));
const canonical = (value) => Array.isArray(value) ? `[${value.map(canonical).join(',')}]`
  : value && typeof value === 'object' ? `{${Object.keys(value).sort().map((k) => `${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`
    : JSON.stringify(value);
const digest = (value) => crypto.createHash('sha256').update(canonical(value)).digest('hex');
// Evaluate only the extracted literal/function body, with no imports, filesystem or process.
const evaluate = (expression, context = {}) => vm.runInNewContext(expression, context, { timeout: 1000 });
const literal = '`(?:\\\\[\\s\\S]|[^`])*`';
const seen = new Set();
const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'devlyn-ai-os-history-'));
const hash = (name, text) => {
  const file = path.join(scratch, path.basename(name));
  fs.writeFileSync(file, text);
  return contentHash(file);
};
try {
  for (const commit of git('rev-list', revision, '--', ...roots).trim().split('\n')) {
    const entries = git('ls-tree', '-r', '-z', commit, '--', ...roots).split('\0').filter(Boolean);
    for (const entry of entries) {
      const [header, name] = entry.split('\t');
      const blob = header.split(' ')[2];
      const key = `${name}:${blob}`;
      if (seen.has(key)) continue;
      seen.add(key);
      if (/^devlyn(?:-cli)?\/src\/templates\/(?:commands|claude|antigravity)\/devlyn\.[^/]+\.md$/.test(name)) {
        add(commands, path.posix.basename(name), hash(name, git('show', blob)));
      } else if (/\/lib\/providers\.ts$/.test(name)) {
        for (const match of git('show', blob).matchAll(/outputDirectory: '([^']+)'/g)) directories.add(match[1]);
      } else if (name.endsWith('/hooks-generator.ts') || name.endsWith('/hooks-setup.ts')) {
        const source = git('show', blob);
        const filename = /const hookScriptPath = path\.join\(hooksDir, '([^']+)'\)/.exec(source)?.[1];
        const command = /const hookCommand = '([^']+)'/.exec(source)?.[1];
        const template = new RegExp(`(?:return |POST_TO_JARVIS_SCRIPT = )(${literal});`).exec(source)?.[1];
        if (!filename || !command || !template) throw new Error(`Unrecognized generator: ${commit}:${name}`);
        let port = Number(/const JARVIS_PORT = (\d+)/.exec(source)?.[1]);
        if (source.includes('DEVLYN_PORT')) {
          const constantsPath = name.startsWith('devlyn-cli/') ? 'devlyn-cli/src/lib/constants.ts' : 'src/lib/constants.ts';
          const constants = git('show', `${commit}:${constantsPath}`);
          const defaultPort = /DEVLYN_PORT = parseInt\(process\.env\.DEVLYN_PORT \|\| '(\d+)', 10\)/.exec(constants)?.[1];
          if (!defaultPort) throw new Error(`Unknown default port: ${commit}:${constantsPath}`);
          port = Number(defaultPort);
        }
        if (/\$\{(?:port|JARVIS_PORT)\}/.test(template) && !Number.isInteger(port)) throw new Error(`Unknown generator port: ${commit}:${name}`);
        const bytes = evaluate(template, { port, JARVIS_PORT: port });
        const target = `.claude/hooks/${filename}`;
        hooks[target] ??= { hashes: new Set(), entries: new Set() };
        hooks[target].hashes.add(hash(filename, bytes));
        const body = /function getHooksConfig\(hookCommand: string\): Record<string, unknown> \{([\s\S]*?)\n\}/.exec(source)?.[1];
        if (!body) throw new Error(`Unknown settings generator: ${commit}:${name}`);
        const settings = evaluate(`(function() {${body}\n})()`, { hookCommand: command });
        for (const [event, entries] of Object.entries(settings)) {
          for (const entry of entries) for (const hook of entry.hooks) hooks[target].entries.add(digest([event, entry.matcher, hook]));
        }
      } else if (name.endsWith('/wizard/agent-installer.ts')) {
        const source = git('show', blob);
        for (const match of source.matchAll(new RegExp(`'commands/(devlyn-[^']+\\.md)': (${literal})`, 'g'))) {
          add(commands, match[1], hash(match[1], evaluate(match[2])));
        }
      }
    }
  }
} finally { fs.rmSync(scratch, { recursive: true, force: true }); }
const result = {
  source: 'agent-devlyn-v1; all ancestors of revision; CLI src/templates/{commands,claude,antigravity}, desktop wizard literals, and evaluated CLI/desktop/worker hook generators at their default ports; scripts/update-cleanup-ai-os-history.js',
  revision, commandDirectories: [...directories].sort(), commands: sorted(commands),
  hooks: Object.fromEntries(Object.keys(hooks).sort().map((key) => [key, sorted(hooks[key])])),
};
const target = path.join(__dirname, 'cleanup-ai-os-history.json');
const output = JSON.stringify(result, null, 2) + '\n';
if (process.argv.includes('--check')) {
  if (fs.readFileSync(target, 'utf8') !== output) throw new Error('AI OS cleanup history drift.');
} else fs.writeFileSync(target, output);
console.log(`AI OS history: ${Object.keys(commands).length} commands (${Object.values(commands).reduce((n, v) => n + v.size, 0)} hashes), ${Object.keys(hooks).length} hooks (${Object.values(hooks).reduce((n, v) => n + v.hashes.size, 0)} hashes), ${directories.size} command directories.`);
