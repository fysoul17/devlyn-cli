#!/usr/bin/env node
// Rung I package checks: bin/review.js against fake reviewer CLIs, and the offline project install.
// Run: node --test scripts/test-review.js
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { execFileSync, spawn, spawnSync } = require('node:child_process');
const { once } = require('node:events');

const ROOT = path.join(__dirname, '..');
const REQUEST = 'CONTRACT: lib/a.js exports 2.\nCHECKS: node --test passed (3/3).\n';
const FALLBACK_WARNING = 'review.js: warning: no refs/remotes/origin/HEAD, so the base is HEAD and committed changes are '
  + 'not reviewed; pass --base <start commit> if any of the change is committed';
const FAKES = {
  claude: {
    ok: ['{"type":"system","subtype":"init","model":"claude-opus-5-5"}',
      '{"type":"result","subtype":"success","is_error":false,"result":"No findings."}'],
    fail: ['{"type":"result","subtype":"success","is_error":true,"result":"API Error: 401 invalid credentials"}'],
    silent: ['{"type":"system","subtype":"init","model":"claude-opus-5-5"}'],
    blank: ['{"type":"result","subtype":"success","is_error":false,"result":" "}'],
    max_turns: ['{"type":"result","subtype":"error_max_turns","is_error":false,"result":"Partial review."}'],
  },
  codex: {
    ok: ['{"type":"thread.started","thread_id":"t-1"}',
      '{"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":"Reading lib/a.js first."}}',
      '{"type":"item.completed","item":{"id":"item_1","type":"agent_message","text":"1. lib/a.js:1 drops the export."}}',
      '{"type":"turn.completed","usage":{"input_tokens":10,"cached_input_tokens":0,"output_tokens":5}}'],
    fail: ['{"type":"thread.started","thread_id":"t-1"}',
      '{"type":"turn.failed","error":{"message":"unexpected status 401 Unauthorized"}}'],
    silent: ['{"type":"turn.completed","usage":{"input_tokens":1,"cached_input_tokens":0,"output_tokens":0}}'],
    blank: ['{"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":" "}}',
      '{"type":"turn.completed","usage":{"input_tokens":1,"cached_input_tokens":0,"output_tokens":1}}'],
  },
};
for (const modes of Object.values(FAKES)) modes.crash = modes.ok; // a complete answer, then exit 3
const EXIT = { fail: 1, crash: 3 };

// A temp HOME, a git repository with one commit, and fake claude/codex on PATH that log argv, stdin and cwd.
function sandbox(t) {
  const dir = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'devlyn-review-')));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  const home = path.join(dir, 'home');
  const repo = path.join(dir, 'repo');
  const bin = path.join(dir, 'bin');
  for (const d of [home, path.join(repo, 'lib'), bin]) fs.mkdirSync(d, { recursive: true });
  const git = (...args) => execFileSync('git', args, { cwd: repo, encoding: 'utf8' }).trim();
  git('init', '-q', '-b', 'main');
  for (const [key, value] of [['user.name', 'T'], ['user.email', 't@example.com'], ['commit.gpgsign', 'false']]) {
    git('config', key, value);
  }
  fs.writeFileSync(path.join(repo, 'lib/a.js'), 'module.exports = 1;\n');
  fs.writeFileSync(path.join(repo, '.gitignore'), 'ignored.txt\n');
  git('add', '-A');
  git('commit', '-qm', 'base');
  for (const [name, modes] of Object.entries(FAKES)) {
    const cases = Object.entries(modes).filter(([mode]) => mode !== 'ok')
      .map(([mode, lines]) => `  ${mode}) printf '%s\\n' ${lines.map((l) => `'${l}'`).join(' ')}; echo 'fake ${name} ${mode}' >&2; `
        + `exit ${EXIT[mode] ?? 0} ;;`).join('\n');
    fs.writeFileSync(path.join(bin, name), `#!/bin/sh\nprintf '%s\\n' "$@" > "$FAKE_LOG.args"\ncat > "$FAKE_LOG.stdin"\n`
      + `pwd -P > "$FAKE_LOG.cwd"\ncase "$FAKE_MODE" in\n${cases}\n  hang) echo $$ > "$FAKE_LOG.pid"; exec sleep 30 ;;\nesac\n`
      + `printf '%s\\n' ${modes.ok.map((l) => `'${l}'`).join(' ')}\n`, { mode: 0o755 });
  }
  const log = path.join(dir, 'fake');
  const env = (mode = 'ok', extra = {}) => ({ ...process.env, HOME: home, PATH: `${bin}:${process.env.PATH}`, LC_ALL: 'C',
    FAKE_LOG: log, FAKE_MODE: mode, ...extra });
  // The timeout turns a hung launcher into a failed test instead of a stalled suite; SIGKILL, because the launcher
  // handles SIGTERM itself.
  const review = (args, { input = REQUEST, cwd = repo, mode, env: extra } = {}) => spawnSync(process.execPath,
    [path.join(ROOT, 'bin/review.js'), ...args],
    { cwd, input, encoding: 'utf8', env: env(mode, extra), timeout: 20000, killSignal: 'SIGKILL' });
  const records = () => {
    const reviews = path.join(home, '.devlyn/reviews');
    return fs.existsSync(reviews) ? fs.readdirSync(reviews).map((name) => path.join(reviews, name)) : [];
  };
  const fake = (suffix) => fs.readFileSync(`${log}.${suffix}`, 'utf8');
  return { dir, home, repo, bin, git, log, env, review, records, fake };
}

// What review.js prints first in a sandbox, which records no origin/HEAD: the HEAD base it fell back to, and why.
const fallback = (box) => `review base: ${box.git('rev-parse', 'HEAD')}\n${FALLBACK_WARNING}\n`;

// A PATH on which git also lists `name` as untracked: an entry that changed after git listed it. git itself never
// lists a FIFO, socket or device, and an entry deleted after the listing is gone when review.js reads it.
function listing(box, name) {
  const dir = path.join(box.dir, 'listing');
  fs.mkdirSync(dir);
  const git = execFileSync('sh', ['-c', 'command -v git'], { encoding: 'utf8' }).trim();
  fs.writeFileSync(path.join(dir, 'git'), `#!/bin/sh\n'${git}' "$@" || exit\n`
    + `case "$*" in *'ls-files --others'*) printf '%s\\0' '${name}' ;; esac\n`, { mode: 0o755 });
  return `${dir}:${box.bin}:${process.env.PATH}`;
}

function onlyRecord(box, engine) {
  const records = box.records();
  assert.equal(records.length, 1);
  assert.match(path.basename(records[0]), new RegExp(`^\\d{8}T\\d{6}\\.\\d{3}Z-${engine}$`));
  assert.deepEqual(fs.readdirSync(records[0]).sort(), ['meta.json', 'prompt.txt', 'stderr', 'stdout']);
  const meta = JSON.parse(fs.readFileSync(path.join(records[0], 'meta.json'), 'utf8'));
  assert.deepEqual(Object.keys(meta),
    ['engine', 'model', 'effort', 'base', 'head', 'reviewed_tree', 'started_at', 'ended_at', 'exit_code']);
  assert.ok(Date.parse(meta.started_at) <= Date.parse(meta.ended_at));
  return { dir: records[0], meta, read: (name) => fs.readFileSync(path.join(records[0], name), 'utf8') };
}

test('claude review: prompt carries request, diff and untracked files; the call is recorded', (t) => {
  const box = sandbox(t);
  fs.writeFileSync(path.join(box.repo, 'lib/a.js'), 'module.exports = 2;\n');
  fs.writeFileSync(path.join(box.repo, 'lib/new.js'), 'UNTRACKED-IN-CWD\n');
  fs.mkdirSync(path.join(box.repo, 'notes'));
  fs.writeFileSync(path.join(box.repo, 'notes/todo.txt'), 'UNTRACKED-ELSEWHERE\n');
  fs.writeFileSync(path.join(box.repo, 'ignored.txt'), 'IGNORED-CONTENT\n');
  const result = box.review(['--engine', 'claude'], { cwd: path.join(box.repo, 'lib') });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout, 'No findings.\n');
  assert.equal(result.stderr, fallback(box));
  assert.deepEqual(box.fake('args').trim().split('\n'), ['-p', '--model', 'claude-opus-5-5', '--effort', 'high',
    '--output-format', 'stream-json', '--verbose', '--tools', 'Read,Grep,Glob', '--strict-mcp-config', '--permission-mode', 'dontAsk']);
  assert.equal(box.fake('cwd').trim(), box.repo);
  const prompt = box.fake('stdin');
  assert.match(prompt, /^You are a fresh, independent reviewer/);
  assert.ok(prompt.includes(REQUEST.trim()));
  assert.ok(prompt.includes('-module.exports = 1;\n+module.exports = 2;'));
  assert.ok(prompt.includes('# Untracked file: lib/new.js\n\nUNTRACKED-IN-CWD'));
  assert.ok(prompt.includes('# Untracked file: notes/todo.txt\n\nUNTRACKED-ELSEWHERE'));
  assert.ok(!prompt.includes('IGNORED-CONTENT'));
  const record = onlyRecord(box, 'claude');
  assert.equal(record.read('prompt.txt'), prompt);
  assert.equal(record.read('stdout'), `${FAKES.claude.ok.join('\n')}\n`);
  const head = box.git('rev-parse', 'HEAD');
  assert.deepEqual({ ...record.meta, reviewed_tree: 0, started_at: 0, ended_at: 0 }, { engine: 'claude',
    model: 'claude-opus-5-5', effort: 'high', base: head, head, reviewed_tree: 0, started_at: 0, ended_at: 0, exit_code: 0 });
});

test('codex review: overrides, explicit --base for a committed change, the last agent message as answer', (t) => {
  const box = sandbox(t);
  const start = box.git('rev-parse', 'HEAD');
  fs.writeFileSync(path.join(box.repo, 'lib/a.js'), 'module.exports = 2;\n');
  box.git('commit', '-qam', 'change');
  const empty = box.review(['--engine', 'codex']);
  assert.equal(empty.status, 1);
  assert.match(empty.stderr, /^review\.js: no change against [0-9a-f]{40} to review; pass --base <start commit>/);
  assert.deepEqual(box.records(), []);
  const result = box.review(['--engine', 'codex', '--model', 'gpt-test', '--effort', 'low', '--base', start]);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout, '1. lib/a.js:1 drops the export.\n');
  assert.equal(result.stderr, `review base: ${start}\n`);
  assert.deepEqual(box.fake('args').trim().split('\n'), ['exec', '--json', '-s', 'read-only', '-m', 'gpt-test',
    '-c', 'model_reasoning_effort="low"', '-C', box.repo, '-']);
  assert.ok(box.fake('stdin').includes(`# Change: git diff ${start}\n\n`));
  assert.ok(box.fake('stdin').includes('+module.exports = 2;'));
  const record = onlyRecord(box, 'codex');
  assert.equal(record.read('stdout'), `${FAKES.codex.ok.join('\n')}\n`);
  assert.equal(record.meta.base, start);
  assert.equal(record.meta.head, box.git('rev-parse', 'HEAD'));
  assert.equal(record.meta.model, 'gpt-test');
  assert.equal(record.meta.effort, 'low');
});

test('default base is the merge-base with the remote default branch', (t) => {
  const box = sandbox(t);
  const start = box.git('rev-parse', 'HEAD');
  // The remote default branch moved on from start, so only the merge-base, not origin/HEAD itself, is start.
  const remote = box.git('commit-tree', '-p', start, '-m', 'remote work', `${start}^{tree}`);
  box.git('update-ref', 'refs/remotes/origin/trunk', remote);
  box.git('symbolic-ref', 'refs/remotes/origin/HEAD', 'refs/remotes/origin/trunk');
  fs.writeFileSync(path.join(box.repo, 'lib/a.js'), 'module.exports = 2;\n');
  box.git('commit', '-qam', 'change');
  const result = box.review(['--engine', 'codex']);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stderr, `review base: ${start}\n`);
  assert.equal(onlyRecord(box, 'codex').meta.base, start);
  assert.ok(box.fake('stdin').includes('+module.exports = 2;'));
});

test('meta records HEAD and the tree of the reviewed working state; the index and hooks are left alone', (t) => {
  const box = sandbox(t);
  const at = (name) => path.join(box.repo, name);
  fs.writeFileSync(at('lib/b.js'), 'module.exports = "b";\n');
  fs.writeFileSync(at('run.sh'), 'echo run\n');
  box.git('add', '-A');
  box.git('commit', '-qm', 'more');
  fs.writeFileSync(at('lib/a.js'), 'module.exports = 2;\n');
  fs.rmSync(at('lib/b.js'));
  fs.chmodSync(at('run.sh'), 0o755);
  fs.writeFileSync(at('staged.txt'), 'STAGED\n');
  box.git('add', 'staged.txt');
  fs.writeFileSync(at('staged.txt'), 'STAGED, THEN EDITED\n');
  fs.mkdirSync(at('notes'));
  fs.writeFileSync(at('notes/new.txt'), 'NEW\n');
  fs.symlinkSync('notes/new.txt', at('new.link'));
  fs.writeFileSync(at('ignored.txt'), 'IGNORED\n');
  const hookRuns = path.join(box.dir, 'hook-runs');
  fs.writeFileSync(at('.git/hooks/post-index-change'), `#!/bin/sh\necho "$GIT_INDEX_FILE" >> '${hookRuns}'\n`, { mode: 0o755 });
  const staged = box.git('ls-files', '--stage');
  const tmp = path.join(box.dir, 'tmp');
  fs.mkdirSync(tmp);
  const result = box.review(['--engine', 'codex'], { cwd: at('notes'), env: { TMPDIR: tmp } });
  assert.equal(result.status, 0, result.stderr);
  const { meta } = onlyRecord(box, 'codex');
  assert.equal(meta.head, box.git('rev-parse', 'HEAD'));
  assert.equal(box.git('ls-files', '--stage'), staged);
  assert.deepEqual(fs.readdirSync(tmp), []);
  // `git diff` may refresh the real index (the hook then sees no GIT_INDEX_FILE); the temporary index runs no hook.
  const runs = fs.existsSync(hookRuns) ? fs.readFileSync(hookRuns, 'utf8') : '';
  assert.ok(!runs.includes(tmp), runs);
  box.git('add', '-A'); // the same working state, staged independently in the real index
  const tree = box.git('write-tree');
  assert.notEqual(tree, box.git('rev-parse', 'HEAD^{tree}'));
  assert.equal(meta.reviewed_tree, tree);
});

test('untracked entries are shown by their own type: symlinks unfollowed, nothing but regular files read', (t) => {
  const box = sandbox(t);
  const at = (name) => path.join(box.repo, name);
  execFileSync('mkfifo', [at('pipe.fifo')]);
  fs.symlinkSync('pipe.fifo', at('link.fifo')); // reading through it blocks
  fs.symlinkSync('lib', at('lib.link'));
  fs.symlinkSync('nowhere', at('dangling'));
  fs.mkdirSync(at('nested'));
  fs.writeFileSync(at('nested/inner.txt'), 'NESTED-CONTENT\n');
  for (const args of [['init', '-q'], ['add', '-A'],
    ['-c', 'user.name=T', '-c', 'user.email=t@example.com', '-c', 'commit.gpgsign=false', 'commit', '-qm', 'nested']]) {
    execFileSync('git', args, { cwd: at('nested') });
  }
  const result = box.review(['--engine', 'claude'], { env: { PATH: listing(box, 'pipe.fifo') } });
  assert.equal(result.status, 0, result.stderr);
  const prompt = box.fake('stdin');
  for (const [entry, text] of [['dangling', 'symlink -> nowhere'], ['lib.link', 'symlink -> lib'],
    ['link.fifo', 'symlink -> pipe.fifo'], ['nested/', 'nested repository directory (contents not expanded)'],
    ['pipe.fifo', 'skipped FIFO']]) {
    assert.ok(prompt.includes(`# Untracked file: ${entry}\n\n${text}`), entry);
  }
  assert.ok(!prompt.includes('NESTED-CONTENT'));
});

test('a failure reading an untracked entry still leaves a record', (t) => {
  const box = sandbox(t);
  fs.writeFileSync(path.join(box.repo, 'lib/a.js'), 'module.exports = 2;\n');
  const result = box.review(['--engine', 'claude'], { env: { PATH: listing(box, 'gone.txt') } });
  assert.equal(result.status, 1);
  assert.equal(result.stderr,
    `${fallback(box)}review.js: ENOENT: no such file or directory, lstat '${path.join(box.repo, 'gone.txt')}'\n`);
  const records = box.records();
  assert.equal(records.length, 1);
  assert.deepEqual(fs.readdirSync(records[0]), ['meta.json']);
  const meta = JSON.parse(fs.readFileSync(path.join(records[0], 'meta.json'), 'utf8'));
  assert.deepEqual([meta.reviewed_tree, meta.exit_code], [null, null]);
  assert.ok(!fs.existsSync(`${box.log}.args`), 'no reviewer was started');
});

for (const engine of ['claude', 'codex']) {
  test(`${engine} failure, empty answer and missing CLI exit nonzero with a clear message`, (t) => {
    const box = sandbox(t);
    fs.writeFileSync(path.join(box.repo, 'lib/a.js'), 'module.exports = 2;\n');
    const failed = box.review(['--engine', engine], { mode: 'fail' });
    assert.equal(failed.status, 1);
    assert.equal(failed.stdout, '');
    const detail = engine === 'claude' ? 'success: API Error: 401 invalid credentials' : 'unexpected status 401 Unauthorized';
    assert.ok(failed.stderr.startsWith(`${fallback(box)}review.js: ${engine} exited 1 (${detail}); no review was obtained. `
      + 'Record: '), failed.stderr);
    assert.ok(failed.stderr.includes(`fake ${engine} fail`));
    assert.equal(onlyRecord(box, engine).meta.exit_code, 1);
    fs.rmSync(path.join(box.home, '.devlyn'), { recursive: true });

    const silent = box.review(['--engine', engine], { mode: 'silent' });
    assert.equal(silent.status, 1);
    assert.equal(silent.stdout, '');
    const why = engine === 'claude' ? 'no result event' : 'no agent message';
    assert.ok(silent.stderr.startsWith(`${fallback(box)}review.js: ${engine} exited 0 (${why}); no review was obtained.`),
      silent.stderr);
    fs.rmSync(path.join(box.home, '.devlyn'), { recursive: true });

    const onlyGit = path.join(box.dir, 'only-git');
    fs.mkdirSync(onlyGit);
    fs.symlinkSync(fs.realpathSync(execFileSync('sh', ['-c', 'command -v git'], { encoding: 'utf8' }).trim()),
      path.join(onlyGit, 'git'));
    const missing = box.review(['--engine', engine], { env: { PATH: onlyGit } });
    assert.equal(missing.status, 1);
    assert.ok(missing.stderr.startsWith(`${fallback(box)}review.js: ${engine} is not installed or not on PATH; `
      + 'no review was obtained. Record: '), missing.stderr);
    assert.equal(onlyRecord(box, engine).meta.exit_code, null);
  });

  test(`${engine}: a nonzero exit or a blank answer${engine === 'claude' ? ' or a non-success result' : ''} is no review`, (t) => {
    const box = sandbox(t);
    fs.writeFileSync(path.join(box.repo, 'lib/a.js'), 'module.exports = 2;\n');
    const cases = [['crash', 'exited 3'], ['blank', 'exited 0']];
    if (engine === 'claude') cases.push(['max_turns', 'exited 0 (error_max_turns: Partial review.)']);
    for (const [mode, outcome] of cases) {
      const result = box.review(['--engine', engine], { mode });
      assert.equal(result.status, 1, mode);
      assert.equal(result.stdout, '', mode);
      assert.ok(result.stderr.startsWith(`${fallback(box)}review.js: ${engine} ${outcome}; no review was obtained.`),
        result.stderr);
    }
  });
}

test('a caller timeout stops the reviewer, and the call is still recorded', async (t) => {
  const box = sandbox(t);
  fs.writeFileSync(path.join(box.repo, 'lib/a.js'), 'module.exports = 2;\n');
  const child = spawn(process.execPath, [path.join(ROOT, 'bin/review.js'), '--engine', 'claude'],
    { cwd: box.repo, env: box.env('hang') });
  let stderr = '';
  child.stderr.on('data', (chunk) => { stderr += chunk; });
  child.stdin.end(REQUEST);
  while (!fs.existsSync(`${box.log}.pid`)) await new Promise((resolve) => setTimeout(resolve, 20));
  child.kill('SIGTERM');
  assert.equal((await once(child, 'close'))[0], 1);
  assert.ok(stderr.startsWith(`${fallback(box)}review.js: claude did not finish (SIGTERM); no review was obtained. Record: `),
    stderr);
  assert.equal(onlyRecord(box, 'claude').meta.exit_code, null);
  assert.throws(() => process.kill(Number(box.fake('pid')), 0), { code: 'ESRCH' });
});

test('usage errors exit nonzero before any reviewer call', (t) => {
  const box = sandbox(t);
  fs.writeFileSync(path.join(box.repo, 'lib/a.js'), 'module.exports = 2;\n');
  const cases = [
    [['--engine', 'grok'], {}, /^review\.js: --engine must be claude or codex\n$/],
    [['--engine', 'claude'], { input: ' \n' }, /^review\.js: pipe the review request \(contract and check results\) on stdin\n$/],
    [['--engine', 'claude', '--base', 'no-such-ref'], {}, /^review\.js: Command failed: git rev-parse --verify no-such-ref\^\{commit\}\nfatal: /],
    [['--engine', 'claude'], { cwd: box.home }, /^review\.js: Command failed: git rev-parse --show-toplevel\nfatal: not a git repository/],
  ];
  for (const [args, options, message] of cases) {
    const result = box.review(args, options);
    assert.equal(result.status, 1);
    assert.match(result.stderr, message);
  }
  assert.deepEqual(box.records(), []);
});

test('each template has its owner request the review from the other engine', () => {
  for (const [name, engine] of [['CLAUDE.md', 'codex'], ['AGENTS.md', 'claude']]) {
    assert.deepEqual(fs.readFileSync(path.join(ROOT, name), 'utf8').match(/--engine \w+/g), [`--engine ${engine}`], name);
  }
});

// The managed block bin/instructions.js writes for a template into a file that did not exist.
function managedBlock(name) {
  const body = 'Project-specific instructions outside this managed block take precedence over these defaults.\n\n'
    + fs.readFileSync(path.join(ROOT, name), 'utf8');
  const sha = crypto.createHash('sha256').update(body).digest('hex');
  return `<!-- devlyn:instructions:begin sha256=${sha} -->\n${body}<!-- devlyn:instructions:end -->\n`;
}

for (const [flags, written] of [[['-y', '--claude'], ['AGENTS.md', 'CLAUDE.md']], [['-y'], ['AGENTS.md']]]) {
  test(`offline install ${flags.join(' ')} writes only ${written.join(' + ')} and the launcher`, (t) => {
    const box = sandbox(t);
    fs.mkdirSync(path.join(box.home, '.devlyn/reviews/old'), { recursive: true });
    fs.writeFileSync(path.join(box.home, '.devlyn/keep.txt'), 'user file\n');
    for (let run = 0; run < 2; run++) {
      const result = spawnSync(process.execPath, [path.join(ROOT, 'bin/devlyn.js'), ...flags],
        { cwd: box.repo, encoding: 'utf8', env: { ...process.env, HOME: box.home } });
      assert.equal(result.status, 0, result.stderr);
      assert.deepEqual(box.git('status', '--porcelain', '--untracked-files=all').split('\n'), written.map((f) => `?? ${f}`));
      for (const name of written) assert.equal(fs.readFileSync(path.join(box.repo, name), 'utf8'), managedBlock(name));
      assert.equal(fs.readFileSync(path.join(box.home, '.devlyn/review.js'), 'utf8'),
        fs.readFileSync(path.join(ROOT, 'bin/review.js'), 'utf8'));
      assert.deepEqual(fs.readdirSync(path.join(box.home, '.devlyn')).sort(), ['keep.txt', 'review.js', 'reviews']);
      assert.deepEqual(fs.readdirSync(path.join(box.home, '.devlyn/reviews')), ['old']);
      assert.equal(fs.readFileSync(path.join(box.home, '.devlyn/keep.txt'), 'utf8'), 'user file\n');
      assert.ok(!fs.existsSync(path.join(box.repo, '.claude')) && !fs.existsSync(path.join(box.repo, '.agents')));
      assert.deepEqual(fs.readdirSync(box.home).sort(), ['.devlyn']);
    }
  });
}
