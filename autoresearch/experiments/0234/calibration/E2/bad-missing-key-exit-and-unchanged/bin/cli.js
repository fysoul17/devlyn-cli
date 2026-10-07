#!/usr/bin/env node
// harbor-tools — small command-line utilities for local workflows.
// Keep the core commands minimal and easy to understand.

const fs = require('fs');
const path = require('path');

const USAGE = `Usage: bench-cli <command> [options]

Commands:
  hello [--name NAME]        Print a greeting (default name: "world")
  config set <key> <value>  Save a config value
  config get <key>          Read a config value
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

const CONFIG = path.join(__dirname, '..', '.harbor', 'config.json');

function readConfig() {
  if (!fs.existsSync(CONFIG)) return {};
  return JSON.parse(fs.readFileSync(CONFIG, 'utf8'));
}

function configCommand(args) {
  const [action, key, value] = args;
  if (action === 'set' && key && value !== undefined) {
    const config = readConfig();
    config[key] = value;
    fs.mkdirSync(path.dirname(CONFIG), { recursive: true });
    fs.writeFileSync(CONFIG, JSON.stringify(config, null, 2) + '\n');
    return;
  }
  if (action === 'unset' && key) {
    const config = readConfig();
    if (!Object.hasOwn(config, key)) {
      fs.writeFileSync(CONFIG, JSON.stringify(config));
      console.error(`unknown key: ${key}`);
      process.exitCode = 1;
      return;
    }
    delete config[key];
    fs.writeFileSync(CONFIG, JSON.stringify(config, null, 2) + '\n');
    return;
  }
  if (action === 'get' && key) {
    const config = readConfig();
    if (!Object.hasOwn(config, key)) {
      console.error(`unknown key: ${key}`);
      process.exitCode = 1;
      return;
    }
    console.log(config[key]);
    return;
  }
  console.error('Usage: bench-cli config set <key> <value> | config get <key>');
  process.exitCode = 1;
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
    case 'config': {
      configCommand(rest);
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
