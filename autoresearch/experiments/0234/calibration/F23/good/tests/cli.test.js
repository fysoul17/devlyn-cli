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
  const file = path.join(os.tmpdir(), 'calibrate-F23-' + process.pid + '.json');
  fs.writeFileSync(file, JSON.stringify(value));
  try { return spawnSync(process.execPath, [CLI, 'fulfill-wave', '--input', file], { encoding: 'utf8' }); }
  finally { fs.rmSync(file, { force: true }); }
}
test('fulfill-wave success', () => {
  const result = probe({"warehouses": [{"id": "w", "distance": 1, "lots": [{"sku": "A", "lot": "l", "qty": 2, "expires": "2026-01-01"}]}], "orders": [{"id": "ok", "priority": 2, "submitted_at": "2026-01-01T00:00:00Z", "lines": [{"sku": "A", "qty": 1, "single_warehouse": false}]}]});
  assert.strictEqual(result.status, 0, result.stderr);
  assert.strictEqual(result.stderr, '');
  const output = JSON.parse(result.stdout);
  assert.ok(output.accepted.length === 1);
});
test('fulfill-wave validation or rejection', () => {
  const result = probe({"warehouses": [{"id": "w", "distance": 1, "lots": [{"sku": "A", "lot": "l", "qty": 2, "expires": "2026-01-01"}]}], "orders": [{"id": "bad", "priority": 2, "submitted_at": "2026-01-01T00:00:00Z", "lines": [{"sku": "A", "qty": 1, "single_warehouse": false}, {"sku": "B", "qty": 1, "single_warehouse": false}]}]});
  assert.ok(JSON.parse(result.stdout).rejected.length === 1);
});
