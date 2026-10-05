#!/usr/bin/env node
// One fresh, read-only review of the current change by another engine's CLI. From inside the repository:
//   node "$HOME/.devlyn/review.js" --engine <claude|codex> [--model M] [--effort E] [--base <ref>] < request
// The request (contract, check results) comes on stdin; review.js adds `git diff <base>` and the untracked files.
// Each call is recorded under ~/.devlyn/reviews/<UTC timestamp>-<engine>/; the base used is printed to stderr and the
// review to stdout.
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync, spawn } = require('child_process');
const { once } = require('events');
const { parseArgs } = require('util');

const MODELS = { claude: 'claude-opus-5-5', codex: 'gpt-6-astra' };
const INSTRUCTION = 'You are a fresh, independent reviewer with read-only access to this repository. Below are the '
  + "author's review request (the contract and actual check results) and the change. Check the change against the "
  + 'contract and existing behavior: unmet requirements, regressions, missing or misleading verification, leftover '
  + 'artifacts the change created and references it broke. For each finding give the requirement, a concrete trigger, '
  + 'the causal path and evidence (file:line or check output). Report only findings you can support; if there are '
  + 'none, say so. Do not edit files or request another review.';

// The merge-base with the remote default branch, or undefined when none is recorded.
function remoteBase(git) {
  try {
    git('rev-parse', '--verify', '--quiet', 'refs/remotes/origin/HEAD');
  } catch (error) {
    if (error.status === 1) return undefined; // no remote default branch recorded
    throw error;
  }
  return git('merge-base', 'HEAD', 'refs/remotes/origin/HEAD').trim();
}

// An untracked entry as prompt text, by its own type: a symlink is not followed and a FIFO or device is never opened.
function untrackedText(file) {
  const stat = fs.lstatSync(file);
  if (stat.isFile()) return fs.readFileSync(file, 'utf8');
  if (stat.isSymbolicLink()) return `symlink -> ${fs.readlinkSync(file)}`;
  if (stat.isDirectory()) return 'nested repository directory (contents not expanded)';
  return `skipped ${stat.isFIFO() ? 'FIFO' : stat.isSocket() ? 'socket' : stat.isCharacterDevice() ? 'character device'
    : 'block device'}`;
}

// The tree object of the whole working state: HEAD plus `git add -A`, staged in a temporary index outside the
// repository with hooks disabled, so the real index is untouched and no hook runs.
function workingTree(run, root, head) {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'devlyn-review-'));
  const git = (...args) => run(root, ['-c', `core.hooksPath=${path.join(temp, 'no-hooks')}`, ...args],
    { ...process.env, GIT_INDEX_FILE: path.join(temp, 'index') });
  try {
    git('read-tree', head);
    git('add', '-A', '--', '.');
    return git('write-tree').trim();
  } finally {
    fs.rmSync(temp, { recursive: true, force: true });
  }
}

// The reviewer's final text from its raw stdout events, or why there is none.
function finalAnswer(engine, events) {
  if (engine === 'claude') {
    const result = events.findLast((event) => event.type === 'result');
    if (!result) return { problem: 'no result event' };
    return result.subtype === 'success' && !result.is_error ? { answer: result.result }
      : { problem: `${result.subtype}: ${result.result ?? ''}`.trim() };
  }
  const turn = events.findLast((event) => event.type === 'turn.completed' || event.type === 'turn.failed');
  if (turn?.type !== 'turn.completed') {
    return { problem: turn?.error?.message ?? events.findLast((event) => event.type === 'error')?.message ?? 'no completed turn' };
  }
  const message = events.findLast((event) => event.type === 'item.completed' && event.item?.type === 'agent_message');
  return message ? { answer: message.item.text } : { problem: 'no agent message' };
}

async function main() {
  const { values: options } = parseArgs({ options: {
    engine: { type: 'string' }, model: { type: 'string' }, effort: { type: 'string', default: 'high' }, base: { type: 'string' },
  } });
  const { engine, effort } = options;
  if (!Object.hasOwn(MODELS, engine ?? '')) throw new Error('--engine must be claude or codex');
  const model = options.model ?? MODELS[engine];
  const run = (cwd, args, env) => execFileSync('git', args,
    { cwd, env, encoding: 'utf8', maxBuffer: Infinity, stdio: ['ignore', 'pipe', 'pipe'] });
  const root = run(process.cwd(), ['rev-parse', '--show-toplevel']).trim();
  const git = (...args) => run(root, args);
  const request = fs.readFileSync(0, 'utf8');
  if (!request.trim()) throw new Error('pipe the review request (contract and check results) on stdin');
  const requested = options.base ?? remoteBase(git);
  const base = git('rev-parse', '--verify', `${requested ?? 'HEAD'}^{commit}`).trim();
  const head = git('rev-parse', '--verify', 'HEAD').trim();
  const diff = git('diff', base);
  const untracked = git('ls-files', '--others', '--exclude-standard', '-z').split('\0').filter(Boolean);
  if (!diff && untracked.length === 0) {
    throw new Error(`no change against ${base} to review; pass --base <start commit> if the change is committed`);
  }
  console.error(`review base: ${base}`);
  if (requested === undefined) {
    console.error('review.js: warning: no refs/remotes/origin/HEAD, so the base is HEAD and committed changes are not '
      + 'reviewed; pass --base <start commit> if any of the change is committed');
  }

  const started = new Date();
  const dir = path.join(os.homedir(), '.devlyn', 'reviews', `${started.toISOString().replace(/[-:]/g, '')}-${engine}`);
  const record = (name) => path.join(dir, name);
  let reviewer, reviewedTree = null, status = null, signal, error;
  // A caller's interrupt or timeout stops the reviewer too, and the call is still recorded.
  for (const name of ['SIGINT', 'SIGTERM', 'SIGHUP']) process.on(name, () => reviewer?.kill(name));
  fs.mkdirSync(path.dirname(dir), { recursive: true });
  fs.mkdirSync(dir);
  try {
    const prompt = [INSTRUCTION, `# Review request\n\n${request.trim()}`, `# Change: git diff ${base}\n\n${diff}`,
      ...untracked.map((file) => `# Untracked file: ${file}\n\n${untrackedText(path.join(root, file))}`)].join('\n\n');
    reviewedTree = workingTree(run, root, head);
    fs.writeFileSync(record('prompt.txt'), prompt, { flag: 'wx' });
    const argv = engine === 'claude'
      ? ['claude', '-p', '--model', model, '--effort', effort, '--output-format', 'stream-json', '--verbose',
        '--tools', 'Read,Grep,Glob', '--strict-mcp-config', '--permission-mode', 'dontAsk']
      : ['codex', 'exec', '--json', '-s', 'read-only', '-m', model, '-c', `model_reasoning_effort="${effort}"`, '-C', root, '-'];
    const stdio = [fs.openSync(record('prompt.txt'), 'r'), fs.openSync(record('stdout'), 'wx'), fs.openSync(record('stderr'), 'wx')];
    reviewer = spawn(argv[0], argv.slice(1), { cwd: root, stdio });
    stdio.forEach((fd) => fs.closeSync(fd));
    [status, signal, error] = await once(reviewer, 'close').catch((spawnError) => [null, null, spawnError]);
  } finally {
    const meta = { engine, model, effort, base, head, reviewed_tree: reviewedTree, started_at: started.toISOString(),
      ended_at: new Date().toISOString(), exit_code: status };
    fs.writeFileSync(record('meta.json'), JSON.stringify(meta, null, 2) + '\n', { flag: 'wx' });
  }
  if (status === null) {
    const reason = error?.code === 'ENOENT' ? 'is not installed or not on PATH' : `did not finish (${error?.message ?? signal})`;
    throw new Error(`${engine} ${reason}; no review was obtained. Record: ${dir}`);
  }
  const events = fs.readFileSync(record('stdout'), 'utf8').split('\n')
    .filter((line) => line.startsWith('{')).map((line) => JSON.parse(line));
  const { answer, problem } = finalAnswer(engine, events);
  if (status !== 0 || !answer?.trim()) {
    const stderr = fs.readFileSync(record('stderr'), 'utf8').trim().split('\n').slice(-5).join('\n');
    throw new Error(`${engine} exited ${status}${problem ? ` (${problem})` : ''}; no review was obtained. `
      + `Record: ${dir}${stderr ? `\n${stderr}` : ''}`);
  }
  process.stdout.write(answer.endsWith('\n') ? answer : `${answer}\n`);
}

main().catch((error) => {
  console.error(`review.js: ${error.message.trimEnd()}`);
  process.exitCode = 1;
});
