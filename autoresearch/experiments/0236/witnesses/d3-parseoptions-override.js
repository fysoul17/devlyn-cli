// Claim (D3, 0235 r01 codex finding): parse() bypasses an override of the public parseOptions method.
//
// Obligation: preserve public APIs and existing in-process parsing behaviour. Trigger (the finding's own witness): a
// Command subclass overriding parseOptions that rewrites --custom to --flag and calls super must parse ['--custom']
// with opts().flag === true. The original commander source does.
//
// Run from the tree root (/work). Exit 1 = reproduces (parse throws or flag is not true), 0 = the override is honoured,
// 2 = witness error (the tree's entry point cannot be loaded).
'use strict';

const path = require('path');

(async () => {
  let Command;
  try {
    ({ Command } = await import(path.join(process.cwd(), 'index.js')));
  } catch (error) {
    console.log('WITNESS ERROR: ' + (error && error.stack || error));
    process.exit(2);
  }
  class CustomCommand extends Command {
    parseOptions(args) {
      return super.parseOptions(args.map((a) => (a === '--custom' ? '--flag' : a)));
    }
  }
  let detail;
  try {
    const program = new CustomCommand().exitOverride().option('--flag');
    program.parse(['--custom'], { from: 'user' });
    detail = { flag: program.opts().flag };
  } catch (error) {
    detail = { threw: error && (error.code || error.message) };
  }
  const reproduced = detail.flag !== true;
  console.log(JSON.stringify({ reproduced, ...detail }));
  process.exit(reproduced ? 1 : 0);
})();
