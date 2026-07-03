'use strict';
// F34 hidden verifier — validation happens before any authorization: an
// unknown account exits 2 with one JSON error object on stderr, no stdout,
// and the gateway records zero calls for the run.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const work = process.env.BENCH_WORKDIR;
const statsPath = path.join(work, 'data', 'gateway-stats.json');
fs.rmSync(statsPath, { force: true });

const inputPath = path.join(os.tmpdir(), `settle-bad-${process.pid}.json`);
fs.writeFileSync(inputPath, JSON.stringify({
  transfers: [
    { id: 't-30', from: 'acct-a', to: 'acct-zzz', amount: 10 }
  ]
}));

const cli = path.join(work, 'bin', 'cli.js');
const result = spawnSync('node', [cli, 'settle', '--input', inputPath], {
  cwd: work,
  encoding: 'utf8'
});

let err;
try {
  err = JSON.parse(result.stderr);
} catch {
  err = null;
}

const gatewayNeverCalled = !fs.existsSync(statsPath);

const ok = result.status === 2
  && result.stdout === ''
  && err !== null
  && err.error === 'invalid_input'
  && typeof err.reason === 'string'
  && gatewayNeverCalled;

console.log(JSON.stringify({ ok, status: result.status, stdout: result.stdout, err, gatewayNeverCalled }));
process.exit(ok ? 0 : 1);
