#!/usr/bin/env node
// bench-test-repo — tiny CLI used as the deterministic base for benchmark fixtures.
// Fixtures extend or modify this file; keep the baseline minimal and obvious.

const fs = require('fs');
const path = require('path');

const USAGE = `Usage: bench-cli <command> [options]

Commands:
  hello [--name NAME]        Print a greeting (default name: "world")
  version                    Print the CLI version from package.json
  --help, -h                 Show this help

Examples:
  bench-cli hello
  bench-cli hello --name alice
  bench-cli version
`;

function readPackageVersion() {
  const pkgPath = path.join(__dirname, '..', 'package.json');
  const raw = fs.readFileSync(pkgPath, 'utf8');
  return JSON.parse(raw).version;
}

function parseNameFlag(argv) {
  const idx = argv.indexOf('--name');
  if (idx === -1) return 'world';
  const value = argv[idx + 1];
  if (!value || value.startsWith('-')) {
    console.error('--name requires a value');
    process.exit(1);
  }
  return value;
}

function main(argv) {
  const [command, ...rest] = argv;

  if (!command || command === '--help' || command === '-h') {
    process.stdout.write(USAGE);
    return;
  }

  switch (command) {
    case 'hello': {
      const name = parseNameFlag(rest);
      console.log(`Hello, ${name}!`);
      return;
    }
    case 'version': {
      console.log(readPackageVersion());
      return;
    }
    default:
      console.error(`Unknown command: ${command}`);
      process.stderr.write(USAGE);
      process.exit(1);
  }
}

main(process.argv.slice(2));
