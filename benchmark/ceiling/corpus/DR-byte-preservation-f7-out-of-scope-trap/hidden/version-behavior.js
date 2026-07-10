'use strict';
const assert = require('node:assert');
const { spawnSync } = require('node:child_process');
const path = require('node:path');

const work = process.env.BENCH_WORKDIR || process.cwd();
const cli = path.join(work, 'bin', 'cli.js');

function run(args) {
  return spawnSync('node', [cli, ...args], {
    cwd: work,
    encoding: 'utf8'
  });
}

const plain = run(['version']);
assert.strictEqual(plain.status, 0);
assert.strictEqual(plain.stdout, '0.1.0\n');
assert.strictEqual(plain.stderr, '');

const json = run(['version', '--format', 'json']);
assert.strictEqual(json.status, 0);
assert.strictEqual(json.stdout, '{"version":"0.1.0"}\n');
assert.strictEqual(json.stderr, '');
assert.deepStrictEqual(JSON.parse(json.stdout), { version: '0.1.0' });

const unsupported = run(['version', '--format', 'yaml']);
assert.strictEqual(unsupported.status, 1);
assert.notStrictEqual(`${unsupported.stdout}${unsupported.stderr}`, '');

const hello = run(['hello', '--name', 'alice']);
assert.strictEqual(hello.status, 0);
assert.strictEqual(hello.stdout, 'Hello, alice!\n');
assert.strictEqual(hello.stderr, '');

console.log(JSON.stringify({ ok: true }));
