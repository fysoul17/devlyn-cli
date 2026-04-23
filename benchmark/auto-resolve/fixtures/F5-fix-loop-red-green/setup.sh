#!/usr/bin/env bash
# F5 setup — install the pre-failing tests for the `count` subcommand.
set -e
cat > tests/count.test.js <<'EOF'
const { test } = require('node:test');
const assert = require('node:assert');
const { spawnSync } = require('node:child_process');
const path = require('node:path');

const CLI = path.join(__dirname, '..', 'bin', 'cli.js');

function runCount(args, stdin) {
  return spawnSync('node', [CLI, 'count', ...args], {
    input: stdin,
    encoding: 'utf8',
  });
}

test('counts whole-word, case-insensitive', () => {
  const r = runCount(['cat'], 'cat hat CAT category scattered\nCat\n');
  assert.strictEqual(r.status, 0);
  assert.strictEqual(r.stdout.trim(), '3');
});

test('whole-word only — cat does not match inside category', () => {
  const r = runCount(['cat'], 'category scattered concatenate');
  assert.strictEqual(r.status, 0);
  assert.strictEqual(r.stdout.trim(), '0');
});

test('case-insensitive — Cat, CAT, cat all match', () => {
  const r = runCount(['cat'], 'Cat CAT cat');
  assert.strictEqual(r.status, 0);
  assert.strictEqual(r.stdout.trim(), '3');
});

test('empty stdin → 0', () => {
  const r = runCount(['cat'], '');
  assert.strictEqual(r.status, 0);
  assert.strictEqual(r.stdout.trim(), '0');
});

test('missing word argument → exit 1 with stderr', () => {
  const r = spawnSync('node', [CLI, 'count'], { input: '', encoding: 'utf8' });
  assert.strictEqual(r.status, 1);
  assert.ok(r.stderr.length > 0);
});

test('trims whitespace from word argument', () => {
  const r = runCount(['  cat  '], 'cat cat');
  assert.strictEqual(r.status, 0);
  assert.strictEqual(r.stdout.trim(), '2');
});
EOF
echo "F5 setup: added tests/count.test.js (failing until count subcommand implemented)"
