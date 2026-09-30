const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { PassThrough } = require('node:stream');
const { test } = require('node:test');
const vm = require('node:vm');
const { Terminal } = require('@xterm/headless');
const checkbox = require('@inquirer/checkbox').default;

// Exercise the installer's real wrapper and Inquirer's real keyboard/VT renderer
// without running any of the install actions in bin/devlyn.js.
const source = readFileSync(require.resolve('../bin/devlyn.js'), 'utf8');
const wrapper = source.slice(source.indexOf('async function multiSelect('), source.indexOf('\nfunction installLocalSkill('));
const items = [
  { name: 'Claude Code', desc: '.claude/ config — skills, templates, settings, CLAUDE.md', type: 'cli' },
  { name: 'Codex CLI (OpenAI)', desc: 'AGENTS.md + devlyn skills → ~/.codex/skills', type: 'cli' },
  ...Array.from({ length: 12 }, (_, i) => ({ name: `확장 ${i} 🍩`, desc: '한글 설명과 긴 설치 경로 /a/long/path/to/skills', type: 'local' })),
];
const settle = () => new Promise((resolve) => setTimeout(resolve, 20));

async function fixture(t, columns) {
  const input = new PassThrough();
  input.isTTY = true;
  input.setRawMode = () => {};
  const output = new PassThrough();
  output.columns = columns;
  output.rows = 20;
  output.isTTY = true;
  const terminal = new Terminal({ cols: columns, rows: 20, scrollback: 100, convertEol: true, allowProposedApi: true });
  let written = Promise.resolve();
  output.on('data', (data) => {
    written = written.then(() => new Promise((resolve) => terminal.write(data, resolve)));
  });
  const cancelled = new Error('fixture exit');
  const messages = [];
  const select = vm.runInNewContext(`${wrapper}\nmultiSelect`, {
    require: () => ({ default: (config) => checkbox(config, { input, output }) }),
    console: { log: (message) => messages.push(message) },
    process: { exit: (code) => { assert.equal(code, 0); throw cancelled; } },
  });
  const answer = select(items, [0, -1, 99]);
  // Attach immediately because Ctrl+C intentionally rejects this fixture.
  answer.catch(() => {});
  t.after(async () => {
    input.end();
    output.end();
    await written;
    terminal.dispose();
  });
  await settle();
  const key = async (bytes) => { input.write(bytes); await settle(); await written; };
  const screen = () => Array.from({ length: terminal.buffer.active.length }, (_, i) => terminal.buffer.active.getLine(i).translateToString(true)).join('\n');
  return { key, answer, screen, messages, cancelled };
}

for (const width of [100, 50, 30]) {
  test(`selection redraw leaves one menu at ${width} columns`, async (t) => {
    const f = await fixture(t, width);
    for (let i = 0; i < 12; i++) await f.key(' ');
    assert.equal(f.screen().split('Claude Code').length - 1, 1);
    assert.equal(f.screen().split('Select options').length - 1, 1);
    await f.key('\x1b[B');
    await f.key(' ');
    await f.key('\r');
    const result = await f.answer;
    assert.deepEqual(Array.from(result, (item) => item.name), ['Claude Code', 'Codex CLI (OpenAI)']);
    assert.equal(result[1], items[1]);
  });
}

test('pagination keeps the last choice reachable with keyboard navigation', async (t) => {
  const f = await fixture(t, 50);
  for (let i = 1; i < items.length; i++) await f.key('j');
  assert.ok(f.screen().includes(items.at(-1).name));
  await f.key(' ');
  await f.key('\r');
  assert.deepEqual(Array.from(await f.answer, (item) => item.name), [items[0].name, items.at(-1).name]);
});

test('select all can be reversed to confirm an empty selection', async (t) => {
  const f = await fixture(t, 50);
  await f.key('a');
  await f.key('a');
  await f.key('\r');
  assert.equal((await f.answer).length, 0);
});

test('Ctrl+C visibly cancels and never resolves a selection', async (t) => {
  const f = await fixture(t, 50);
  await f.key('\x03');
  await assert.rejects(f.answer, (error) => error === f.cancelled);
  assert.deepEqual(f.messages, ['Installation cancelled.']);
});
