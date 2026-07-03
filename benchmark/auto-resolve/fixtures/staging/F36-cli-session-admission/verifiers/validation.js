'use strict';
// F36 hidden verifier — validation happens before any admission decision:
// malformed capacity/session fields use `invalid_input`, duplicate ids use
// the distinct `duplicate_session_id` shape, and nothing is admitted or
// printed to stdout in either case.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const work = process.env.BENCH_WORKDIR;
const cli = path.join(work, 'bin', 'cli.js');

let callCount = 0;
function runAdmit(payload) {
  callCount += 1;
  const inputPath = path.join(os.tmpdir(), `admit-validate-${process.pid}-${callCount}.json`);
  fs.writeFileSync(inputPath, JSON.stringify(payload));
  const result = spawnSync('node', [cli, 'admit', '--input', inputPath], {
    cwd: work,
    encoding: 'utf8',
    maxBuffer: 16 * 1024 * 1024,
  });
  let err = null;
  try {
    err = JSON.parse(result.stderr);
  } catch {
    err = null;
  }
  return { result, err };
}

const failures = [];

function expectInvalidInput(label, payload) {
  const { result, err } = runAdmit(payload);
  const ok = result.status === 2 && result.stdout === '' && err !== null && err.error === 'invalid_input' && typeof err.reason === 'string';
  if (!ok) {
    failures.push({ test: label, status: result.status, stdout: result.stdout, stderr: result.stderr, err });
  }
}

// Non-positive capacity.
expectInvalidInput('capacity-zero', { capacity: 0, sessions: [{ id: 'a', start: 0, end: 1 }] });
// Non-integer capacity.
expectInvalidInput('capacity-float', { capacity: 1.5, sessions: [{ id: 'a', start: 0, end: 1 }] });
// start >= end.
expectInvalidInput('start-not-before-end', { capacity: 1, sessions: [{ id: 'a', start: 5, end: 5 }] });
// Non-integer start.
expectInvalidInput('non-integer-start', { capacity: 1, sessions: [{ id: 'a', start: 0.5, end: 5 }] });
// Missing id.
expectInvalidInput('missing-id', { capacity: 1, sessions: [{ start: 0, end: 5 }] });
// sessions not an array.
expectInvalidInput('sessions-not-array', { capacity: 1, sessions: 'nope' });

// Duplicate session id — distinct error shape.
{
  const payload = {
    capacity: 2,
    sessions: [
      { id: 'dup', start: 0, end: 1 },
      { id: 'dup', start: 2, end: 3 },
    ],
  };
  const { result, err } = runAdmit(payload);
  const ok = result.status === 2 && result.stdout === '' && err !== null && err.error === 'duplicate_session_id' && err.id === 'dup';
  if (!ok) {
    failures.push({ test: 'duplicate-session-id', status: result.status, stdout: result.stdout, stderr: result.stderr, err });
  }
}

const ok = failures.length === 0;
console.log(JSON.stringify({ ok, failures }));
process.exit(ok ? 0 : 1);
