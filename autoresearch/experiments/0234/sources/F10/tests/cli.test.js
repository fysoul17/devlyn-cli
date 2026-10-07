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
