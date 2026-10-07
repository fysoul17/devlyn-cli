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

const fs = require('node:fs');
const os = require('node:os');
const { spawnSync } = require('node:child_process');
function probe(value) {
  const file = path.join(os.tmpdir(), 'calibrate-F16-' + process.pid + '.json');
  fs.writeFileSync(file, JSON.stringify(value));
  try { return spawnSync(process.execPath, [CLI, 'quote', '--input', file], { encoding: 'utf8' }); }
  finally { fs.rmSync(file, { force: true }); }
}
test('quote success', () => {
  const result = probe({"state": "OR", "coupon": null, "items": [{"sku": "A", "qty": 1}]});
  assert.strictEqual(result.status, 0, result.stderr);
  assert.strictEqual(result.stderr, '');
  const output = JSON.parse(result.stdout);
  assert.ok(Number.isInteger(output.total_cents));
});
test('quote validation or rejection', () => {
  const result = probe({"state": "OR", "coupon": null, "items": [{"sku": "A", "qty": 8}]});
  assert.ok(result.status === 2 && JSON.parse(result.stderr).error === 'invalid_stock');
});
