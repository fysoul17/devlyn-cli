'use strict';
// Runs replay-release-d092-I0185-codex-A-r6.js (the 0224 rule 1 variant) in this container and prints a compact result.
// Exit 1 = the row FAILs (variant did not fire, or fired and did not pass), 0 = the row PASSes, 2 = error.
const { spawnSync } = require('node:child_process');
const done = spawnSync(process.execPath, ['/witness/replay-release-d092-I0185-codex-A-r6.js'], { encoding: 'utf8' });
try {
  const r = JSON.parse(done.stdout.trim().split('\n').pop());
  const lock = r.removals.filter((x) => /lock/i.test(x.path)).map((x) => x.method + ' ' + x.path.replace(/[0-9a-f]{64}/, '<sha256>'));
  console.log(JSON.stringify({ fired: r.fired && { method: r.fired.method, path: r.fired.path.replace(/[0-9a-f]{64}/, '<sha256>') },
    error: r.error && r.error.slice(0, 400), returned: r.returned, restored: r.restored, passed: r.passed, lockRemovals: lock }));
  process.exitCode = r.passed ? 0 : 1;
} catch (error) {
  console.log('VARIANT ERROR: ' + error + ' ' + (done.stdout + done.stderr).slice(-600));
  process.exitCode = 2;
}
