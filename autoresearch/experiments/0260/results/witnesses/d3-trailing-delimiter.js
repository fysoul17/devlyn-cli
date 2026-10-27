'use strict';
// Root's check of d017's sentence "Executable subcommands now receive the first `--` in the same place it appeared on
// the command line", run on every D3 tree for a consistent judgment. The tree's own fixture program `pm` spawns its
// executable `echo` subcommand (pm-echo.js prints its argv as JSON). A `--` with an operand after it must reach the
// child (`a -- --x`). Exit 1 when that works but a final `--` (`a --`) is dropped, 0 when the final `--` also arrives in
// place, 2 when the setup fails or the operand case itself fails.

const path = require('path');
const { execFileSync } = require('child_process');
const { writeSync } = require('fs');

function echo(args) {
  const out = execFileSync(process.execPath, [path.resolve('tests/fixtures/pm'), 'echo', ...args],
    { encoding: 'utf8', timeout: 8000 });
  return JSON.parse(out.trim().split('\n').pop());
}

try {
  const withOperand = echo(['a', '--', '--x']);
  const final = echo(['a', '--']);
  writeSync(1, JSON.stringify({ withOperand, final }) + '\n');
  if (JSON.stringify(withOperand) !== JSON.stringify(['a', '--', '--x'])) process.exit(2);
  process.exit(JSON.stringify(final) === JSON.stringify(['a', '--']) ? 0 : 1);
} catch (error) {
  process.stderr.write(String(error) + '\n');
  process.exit(2);
}
