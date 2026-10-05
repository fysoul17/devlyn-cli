// Runner (not a witness): runs replay-release-m31-I0185-codex-I-r2.js in the cell image and surfaces its verdict fields via exit 2.
const { spawnSync } = require('node:child_process');
const crypto = require('node:crypto');
const r = spawnSync(process.execPath, ['/witness/replay-release-m31-I0185-codex-I-r2.js'], { encoding: 'utf8', timeout: 240000 });
let j = null; try { j = JSON.parse(r.stdout.trim().split('\n').pop()); } catch (e) { /* reported below */ }
console.log(JSON.stringify(j === null ? { exit: r.status, stdout: r.stdout.slice(-300), stderr: r.stderr.slice(-300) } : {
  exit: r.status, fired: j.fired, error: j.error && j.error.slice(0, 170), returned: j.returned, restored: j.restored, passed: j.passed,
  removals: j.removals.length, lockRemovals: j.removals.filter((x) => /lock/i.test(x.path)).length,
  outputSha256: crypto.createHash('sha256').update(r.stdout).digest('hex').slice(0, 16) }));
process.exit(2);
