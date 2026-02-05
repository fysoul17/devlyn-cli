#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const readline = require('readline');
const { execSync } = require('child_process');

const CONFIG_SOURCE = path.join(__dirname, '..', 'config');
const TARGET_DIR = path.join(process.cwd(), '.claude');

const COLORS = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  dim: '\x1b[2m',
  bold: '\x1b[1m',
};

const SKILL_PACKS = [
  { name: 'vercel-labs/agent-skills', desc: 'React, Next.js, React Native best practices' },
  { name: 'supabase/agent-skills', desc: 'Supabase integration patterns' },
];

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

function prompt(question) {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      rl.close();
      resolve(answer.trim().toLowerCase());
    });
  });
}

function installSkillPack(packName) {
  try {
    log(`\n📦 Installing ${packName}...`, 'cyan');
    execSync(`npx skills add ${packName}`, { stdio: 'inherit' });
    return true;
  } catch (error) {
    log(`   ⚠️  Failed to install ${packName}`, 'yellow');
    return false;
  }
}

async function init(skipPrompts = false) {
  log('\n🚀 devlyn-cli', 'blue');
  log('─'.repeat(40), 'dim');

  if (!fs.existsSync(CONFIG_SOURCE)) {
    log('❌ Config source not found', 'yellow');
    process.exit(1);
  }

  // Install core config
  log('\n📁 Installing core config to .claude/', 'green');
  copyRecursive(CONFIG_SOURCE, TARGET_DIR);
  log('\n✅ Core config installed!', 'green');

  // Skip prompts if -y flag or non-interactive
  if (skipPrompts || !process.stdin.isTTY) {
    log('\n💡 Add skill packs later with:', 'dim');
    SKILL_PACKS.forEach((pack) => {
      log(`   npx skills add ${pack.name}`, 'dim');
    });
    log('');
    return;
  }

  // Ask about skill packs
  log('\n📚 Optional skill packs:', 'blue');
  SKILL_PACKS.forEach((pack, i) => {
    log(`   ${i + 1}. ${pack.name}`, 'cyan');
    log(`      ${pack.desc}`, 'dim');
  });

  const answer = await prompt('\nInstall skill packs? (1,2/all/none) [none]: ');

  if (answer === 'all' || answer === 'a') {
    for (const pack of SKILL_PACKS) {
      installSkillPack(pack.name);
    }
  } else if (answer && answer !== 'none' && answer !== 'n' && answer !== '') {
    const indices = answer.split(',').map((s) => parseInt(s.trim()) - 1);
    for (const i of indices) {
      if (SKILL_PACKS[i]) {
        installSkillPack(SKILL_PACKS[i].name);
      }
    }
  }

  log('\n✨ All done!', 'green');
  log('   Run `npx devlyn-cli` again to update\n', 'dim');
}

function showHelp() {
  log('\n🚀 devlyn-cli - Claude Code config toolkit\n', 'blue');
  log('Usage:', 'green');
  log('  npx devlyn-cli          Install/update .claude config');
  log('  npx devlyn-cli -y       Install without prompts');
  log('  npx devlyn-cli --help   Show this help\n');
  log('Skill packs:', 'green');
  SKILL_PACKS.forEach((pack) => {
    log(`  npx skills add ${pack.name}`);
  });
  log('');
}

// Main
const args = process.argv.slice(2);
const command = args[0];

switch (command) {
  case '--help':
  case '-h':
    showHelp();
    break;
  case '-y':
  case '--yes':
    init(true);
    break;
  case 'init':
  case undefined:
    init(false);
    break;
  default:
    log(`Unknown command: ${command}`, 'yellow');
    showHelp();
    process.exit(1);
}
