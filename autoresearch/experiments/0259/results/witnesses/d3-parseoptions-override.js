'use strict';

const path = require('path');
const { writeSync } = require('fs');
const timer = setTimeout(() => process.exit(2), 10000);

try {
  const { Command } = require(path.resolve('index.js'));
  if (typeof Command !== 'function') throw new Error('Command export missing');
  class RewritingCommand extends Command {
    parseOptions(args) {
      const rewritten = args.map(arg => arg === 'p0258-before' ? 'p0258-after' : arg);
      return super.parseOptions(rewritten);
    }
  }
  const command = new RewritingCommand();
  command.argument('<values...>');
  command.exitOverride();
  command.parse(['p0258-before'], { from: 'user' });
  clearTimeout(timer);
  if (JSON.stringify(command.args) === JSON.stringify(['p0258-after'])) {
    writeSync(1, 'P0258-WITNESS public\n');
    process.exit(0);
  }
  if (JSON.stringify(command.args) === JSON.stringify(['p0258-before'])) {
    writeSync(1, 'P0258-WITNESS bypass\n');
    process.exit(1);
  }
  process.exit(2);
} catch (error) {
  clearTimeout(timer);
  process.stderr.write(String(error) + '\n');
  process.exit(2);
}
