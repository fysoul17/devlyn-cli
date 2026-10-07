const { test } = require('node:test');
const assert = require('node:assert');
const { execFileSync } = require('node:child_process');
const path = require('node:path');

const CLI = path.join(__dirname, '..', 'bin', 'cli.js');

function run(args) {
  return execFileSync('node', [CLI, ...args], { encoding: 'utf8' });
}

test('hello default', () => {
  const out = run(['hello']);
  assert.match(out, /Hello, world!/);
});

test('hello with --name', () => {
  const out = run(['hello', '--name', 'alice']);
  assert.match(out, /Hello, alice!/);
});

test('version prints package version', () => {
  const out = run(['version']);
  assert.match(out, /\d+\.\d+\.\d+/);
});


test('config set and get preserve other keys', () => {
  const { mkdtempSync, readFileSync, rmSync, copyFileSync, mkdirSync } = require('node:fs');
  const { tmpdir } = require('node:os');
  const dir = mkdtempSync(path.join(tmpdir(), 'bench-config-'));
  try {
    mkdirSync(path.join(dir, 'bin'));
    copyFileSync(CLI, path.join(dir, 'bin/cli.js'));
    copyFileSync(path.join(__dirname, '../package.json'), path.join(dir, 'package.json'));
    const local = path.join(dir, 'bin/cli.js');
    execFileSync('node', [local, 'config', 'set', 'alpha', 'one']);
    execFileSync('node', [local, 'config', 'set', 'beta', 'two']);
    assert.strictEqual(execFileSync('node', [local, 'config', 'get', 'alpha'], { encoding: 'utf8' }).trim(), 'one');
    assert.deepStrictEqual(JSON.parse(readFileSync(path.join(dir, '.harbor/config.json'))), { alpha: 'one', beta: 'two' });
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});


test('config unset preserves other keys and missing key leaves bytes unchanged', () => {
  const { mkdtempSync, readFileSync, rmSync, copyFileSync, mkdirSync } = require('node:fs');
  const { tmpdir } = require('node:os');
  const dir = mkdtempSync(path.join(tmpdir(), 'bench-unset-'));
  try {
    mkdirSync(path.join(dir, 'bin'));
    copyFileSync(CLI, path.join(dir, 'bin/cli.js'));
    copyFileSync(path.join(__dirname, '../package.json'), path.join(dir, 'package.json'));
    const local = path.join(dir, 'bin/cli.js');
    const invoke = (...args) => require('node:child_process').spawnSync('node', [local, 'config', ...args], { encoding: 'utf8' });
    assert.strictEqual(invoke('set', 'a', 'one').status, 0);
    assert.strictEqual(invoke('set', 'b', 'two').status, 0);
    assert.strictEqual(invoke('unset', 'a').status, 0);
    const file = path.join(dir, '.harbor/config.json');
    assert.deepStrictEqual(JSON.parse(readFileSync(file)), { b: 'two' });
    const before = readFileSync(file);
    const missing = invoke('unset', 'a');
    assert.strictEqual(missing.status, 1);
    assert.match(missing.stderr, /unknown key: a/);
    assert.ok(before.equals(readFileSync(file)));
  } finally { rmSync(dir, { recursive: true, force: true }); }
});
