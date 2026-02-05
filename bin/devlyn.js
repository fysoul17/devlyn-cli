#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const CONFIG_SOURCE = path.join(__dirname, '..', 'config');
const TARGET_DIR = path.join(process.cwd(), '.claude');

const COLORS = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  dim: '\x1b[2m',
};

function log(msg, color = 'reset') {
  console.log(`${COLORS[color]}${msg}${COLORS.reset}`);
}

function copyRecursive(src, dest) {
  const stats = fs.statSync(src);

  if (stats.isDirectory()) {
    if (!fs.existsSync(dest)) {
      fs.mkdirSync(dest, { recursive: true });
    }

    for (const item of fs.readdirSync(src)) {
      copyRecursive(path.join(src, item), path.join(dest, item));
    }
  } else {
    const destDir = path.dirname(dest);
    if (!fs.existsSync(destDir)) {
      fs.mkdirSync(destDir, { recursive: true });
    }
    fs.copyFileSync(src, dest);
    log(`  → ${path.relative(TARGET_DIR, dest)}`, 'dim');
  }
}

function init() {
  log('\n🚀 devlyn-cli', 'blue');
  log('─'.repeat(40), 'dim');

  if (!fs.existsSync(CONFIG_SOURCE)) {
    log('❌ Config source not found', 'yellow');
    process.exit(1);
  }

  log('\n📁 Installing to .claude/', 'green');
  copyRecursive(CONFIG_SOURCE, TARGET_DIR);

  log('\n✅ Done!', 'green');
  log('   Run `npx devlyn-cli` again to update\n', 'dim');
}

function showHelp() {
  log('\n🚀 devlyn-cli - Claude Code config toolkit\n', 'blue');
  log('Usage:', 'green');
  log('  npx devlyn-cli          Install/update .claude config');
  log('  npx devlyn-cli init     Same as above');
  log('  npx devlyn-cli --help   Show this help\n');
}

// Main
const args = process.argv.slice(2);
const command = args[0];

switch (command) {
  case '--help':
  case '-h':
    showHelp();
    break;
  case 'init':
  case undefined:
    init();
    break;
  default:
    log(`Unknown command: ${command}`, 'yellow');
    showHelp();
    process.exit(1);
}
