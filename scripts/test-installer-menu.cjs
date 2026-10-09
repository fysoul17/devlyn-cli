const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const Module = require('node:module');
const path = require('node:path');
const { PassThrough } = require('node:stream');
const { test } = require('node:test');
const { Terminal } = require('@xterm/headless');

// The installer's real menu wrappers, its real addon list and Inquirer's real keyboard/VT
// renderer, compiled as the installer module so its imports resolve the same way, with
// `process` and `console` bound to an emulated terminal. No install action runs.
const installer = require.resolve('../bin/devlyn.js');
const source = readFileSync(installer, 'utf8');
const between = (start, end) => {
  const from = source.indexOf(start);
  const to = source.indexOf(end, from);
  assert.ok(from !== -1 && to !== -1, `bin/devlyn.js lost ${start}`);
  return source.slice(from, to);
};
const menus = new Module(installer);
menus.filename = installer;
menus.paths = Module._nodeModulePaths(path.dirname(installer));
menus._compile(`module.exports = (process, console) => {
${between('const OPTIONAL_ADDONS = [', '\nfunction log(')}
${between('async function ask(', '\nfunction installLocalSkill(')}
return { OPTIONAL_ADDONS, multiSelect, singleSelect };
};`, installer);
const load = menus.exports;
const { OPTIONAL_ADDONS } = load();

const targets = [
  { key: 'agents', name: 'AGENTS.md — Codex · omp · Pi · Grok', desc: 'AGENTS.md + .agents/skills' },
  { key: 'claude', name: 'CLAUDE.md — Claude Code', desc: 'CLAUDE.md + .claude/ (skills, settings)' },
];
const wide = [
  ...targets,
  ...Array.from({ length: 12 }, (_, i) => ({ name: `확장 ${i} 🍩`, desc: '한글 설명과 긴 설치 경로 /a/long/path/to/skills 🍩', type: 'local' })),
];
const settle = () => new Promise((resolve) => setTimeout(resolve, 20));

// Opens `menu` on a terminal of `columns` × `rows`; `key` types into it after it has drawn.
async function open(t, { columns, rows = 20 }, menu, ...args) {
  const input = new PassThrough();
  input.isTTY = true;
  input.setRawMode = () => {};
  const output = new PassThrough();
  Object.assign(output, { columns, rows, isTTY: true });
  const terminal = new Terminal({ cols: columns, rows, scrollback: 1000, convertEol: true, allowProposedApi: true });
  let written = Promise.resolve();
  output.on('data', (data) => {
    written = written.then(() => new Promise((resolve) => terminal.write(data, resolve)));
  });
  const cancelled = new Error('fixture exit');
  const messages = [];
  const select = load({
    stdin: input,
    stdout: output,
    exit: (code) => { assert.equal(code, 0); throw cancelled; },
  }, { log: (message) => messages.push(message) })[menu];
  const drawn = new Promise((resolve) => output.once('data', resolve));
  const answer = select(...args);
  // Attached at once: Ctrl+C rejects this fixture by design.
  answer.catch(() => {});
  await drawn;
  t.after(async () => {
    input.end();
    output.end();
    await written;
    terminal.dispose();
  });
  await settle();
  await written;
  const lines = (from, to) => Array.from({ length: to - from }, (_, i) => terminal.buffer.active.getLine(from + i).translateToString(true));
  // Everything ever drawn, scrollback included, and only what is on screen now.
  const history = () => lines(0, terminal.buffer.active.length).join('\n');
  const screen = () => lines(terminal.buffer.active.viewportY, terminal.buffer.active.viewportY + rows).join('\n');
  const key = async (bytes) => { input.write(bytes); await settle(); await written; };
  return { key, answer, history, screen, messages, cancelled };
}

const count = (text, part) => text.split(part).length - 1;

for (const columns of [100, 50, 30]) {
  test(`checkbox redraw leaves one menu at ${columns} columns, wide characters included`, async (t) => {
    const f = await open(t, { columns }, 'multiSelect', 'What to install', wide, [0, -1, 99]);
    for (let i = 0; i < 12; i++) await f.key(' ');
    await f.key('j');
    await f.key('\x1b[B');
    await f.key(' ');
    assert.equal(count(f.history(), 'What to install'), 1);
    await f.key('\r');
    const result = await f.answer;
    assert.deepEqual(result, [wide[0], wide[2]]);
    assert.equal(count(f.history(), 'What to install'), 1);
  });

  test(`select redraw leaves one menu at ${columns} columns`, async (t) => {
    const f = await open(t, { columns }, 'singleSelect', 'Where', ['이 프로젝트 🍩', 'Global — every project on this machine 🌍'], 0);
    for (let i = 0; i < 5; i++) await f.key('j');
    assert.equal(count(f.history(), 'Where'), 1);
    await f.key('\r');
    assert.equal(await f.answer, 1);
  });
}

for (const columns of [100, 50, 30]) {
  test(`all ${OPTIONAL_ADDONS.length} addons are reachable on a 10-row terminal at ${columns} columns`, async (t) => {
    assert.equal(OPTIONAL_ADDONS.length, 21);
    const f = await open(t, { columns, rows: 10 }, 'multiSelect', 'Optional skills & packs', OPTIONAL_ADDONS);
    for (const [i, addon] of OPTIONAL_ADDONS.entries()) {
      if (i > 0) await f.key('j');
      // The whole menu stays on screen: its message is drawn once and never scrolls away.
      assert.equal(count(f.history(), 'Optional skills & packs'), 1, `after moving to ${addon.name}`);
      assert.ok(f.screen().includes('? Optional skills & packs'), `message off screen at ${addon.name}`);
      assert.ok(f.screen().replace(/\n/g, '').includes(addon.name.slice(0, columns - 4)), `${addon.name} not shown`);
    }
    await f.key(' ');
    await f.key('k');
    await f.key(' ');
    await f.key('\r');
    assert.deepEqual(await f.answer, OPTIONAL_ADDONS.slice(-2));
  });
}

test('preselected choices are checked and out-of-range indices ignored', async (t) => {
  const f = await open(t, { columns: 80 }, 'multiSelect', 'What to install', targets, [1, -1, 2, 99]);
  await f.key('\r');
  assert.deepEqual(await f.answer, [targets[1]]);
});

test('select all toggles back to an empty selection', async (t) => {
  const f = await open(t, { columns: 50 }, 'multiSelect', 'What to install', targets, [0]);
  await f.key('a');
  await f.key('a');
  await f.key('\r');
  assert.deepEqual(await f.answer, []);
});

test('select all checks every choice', async (t) => {
  const f = await open(t, { columns: 50 }, 'multiSelect', 'What to install', targets, [0]);
  await f.key('a');
  await f.key('\r');
  assert.deepEqual(await f.answer, targets);
});

test('select starts at its initial choice and moves with arrows and vim keys', async (t) => {
  const items = ['This project', 'Global — every project on this machine'];
  const initial = await open(t, { columns: 80 }, 'singleSelect', 'Where', items, 1);
  await initial.key('\r');
  assert.equal(await initial.answer, 1);
  const moved = await open(t, { columns: 80 }, 'singleSelect', 'Where', items, 0);
  await moved.key('\x1b[B');
  await moved.key('k');
  await moved.key('k');
  await moved.key('\r');
  assert.equal(await moved.answer, 1);
});

for (const menu of ['multiSelect', 'singleSelect']) {
  test(`Ctrl+C in ${menu} cancels the install visibly and resolves nothing`, async (t) => {
    const args = menu === 'multiSelect' ? [targets, [0]] : [['This project', 'Global'], 0];
    const f = await open(t, { columns: 50 }, menu, 'Menu', ...args);
    await f.key('\x03');
    await assert.rejects(f.answer, (error) => error === f.cancelled);
    assert.deepEqual(f.messages, ['Installation cancelled.']);
  });
}
