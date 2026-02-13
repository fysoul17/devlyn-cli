#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const readline = require('readline');
const { execSync } = require('child_process');

const CONFIG_SOURCE = path.join(__dirname, '..', 'config');
const OPTIONAL_SKILLS_SOURCE = path.join(__dirname, '..', 'optional-skills');
const PKG = require('../package.json');

function getTargetDir() {
  try {
    return path.join(process.cwd(), '.claude');
  } catch {
    console.error('\n\x1b[33m❌ Current directory no longer exists.\x1b[0m');
    console.error('\x1b[2m   Please cd into a valid directory and try again.\x1b[0m\n');
    process.exit(1);
  }
}

const COLORS = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  magenta: '\x1b[35m',
  dim: '\x1b[2m',
  bold: '\x1b[1m',
  // Extended colors for gradient effect
  purple: '\x1b[38;5;135m',
  violet: '\x1b[38;5;99m',
  pink: '\x1b[38;5;213m',
  gray: '\x1b[38;5;240m',
};

function showLogo() {
  const p = COLORS.purple;
  const v = COLORS.violet;
  const k = COLORS.pink;
  const g = COLORS.gray;
  const r = COLORS.reset;

  // 2.5D effect using block shadows and gradient colors
  const logo = `
${v}     ██████╗ ${p}███████╗${k}██╗   ██╗${v}██╗     ${p}██╗   ██╗${k}███╗   ██╗${r}
${v}     ██╔══██╗${p}██╔════╝${k}██║   ██║${v}██║     ${p}╚██╗ ██╔╝${k}████╗  ██║${r}
${v}     ██║  ██║${p}█████╗  ${k}██║   ██║${v}██║      ${p}╚████╔╝ ${k}██╔██╗ ██║${r}
${v}     ██║  ██║${p}██╔══╝  ${k}╚██╗ ██╔╝${v}██║       ${p}╚██╔╝  ${k}██║╚██╗██║${r}
${v}     ██████╔╝${p}███████╗${k} ╚████╔╝ ${v}███████╗   ${p}██║   ${k}██║ ╚████║${r}
${g}     ╚═════╝ ╚══════╝  ╚═══╝  ╚══════╝   ╚═╝   ╚═╝  ╚═══╝${r}

${COLORS.dim}            Claude Code Config Toolkit${r}
${g}                v${PKG.version} ${COLORS.dim}· ${k}🍩 by Donut Studio${r}
`;
  console.log(logo);
}

const OPTIONAL_ADDONS = [
  // Local optional skills (copied to .claude/skills/)
  { name: 'cloudflare-nextjs-setup', desc: 'Cloudflare Workers + Next.js deployment with OpenNext', type: 'local' },
  { name: 'prompt-engineering', desc: 'Claude 4 prompt optimization using Anthropic best practices', type: 'local' },
  // External skill packs (installed via npx skills add)
  { name: 'vercel-labs/agent-skills', desc: 'React, Next.js, React Native best practices', type: 'external' },
  { name: 'supabase/agent-skills', desc: 'Supabase integration patterns', type: 'external' },
  { name: 'coreyhaines31/marketingskills', desc: 'Marketing automation and content skills', type: 'external' },
];

function log(msg, color = 'reset') {
  console.log(`${COLORS[color]}${msg}${COLORS.reset}`);
}

function getDescription(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const lines = content.split('\n');

    // 1. Check if first line is a plain description (not header, not frontmatter, not empty)
    const firstLine = lines[0]?.trim();
    if (firstLine && !firstLine.startsWith('#') && !firstLine.startsWith('---') && !firstLine.startsWith('<') && !firstLine.includes('{')) {
      return firstLine.slice(0, 70);
    }

    // 2. Look for description in frontmatter
    const descMatch = content.match(/description:\s*["']?([^"'\n]+)/i);
    if (descMatch && !descMatch[1].includes('{')) {
      return descMatch[1].trim().slice(0, 70);
    }

    // 3. Look for purpose field in yaml blocks
    const purposeMatch = content.match(/purpose:\s*["']?([^"'\n{]+)/i);
    if (purposeMatch && !purposeMatch[1].includes('{')) {
      return purposeMatch[1].trim().slice(0, 70);
    }

    // 4. Get first H1 title as fallback (skip template placeholders)
    const titleMatch = content.match(/^#\s+([^{}\n]+)$/m);
    if (titleMatch && !titleMatch[1].includes('{') && !titleMatch[1].includes('[')) {
      return titleMatch[1].trim().slice(0, 70);
    }

    return '';
  } catch {
    return '';
  }
}

function listContents() {
  showLogo();
  log('─'.repeat(44), 'dim');

  const commandsDir = path.join(CONFIG_SOURCE, 'commands');
  const templatesDir = path.join(CONFIG_SOURCE, 'templates');
  const skillsDir = path.join(CONFIG_SOURCE, 'skills');

  // List commands
  if (fs.existsSync(commandsDir)) {
    const commands = fs.readdirSync(commandsDir).filter((f) => f.endsWith('.md'));
    if (commands.length > 0) {
      log('\n📋 Commands:', 'cyan');
      commands.forEach((file) => {
        const name = file.replace('.md', '').replace('devlyn.', '/');
        const desc = getDescription(path.join(commandsDir, file));
        log(`  ${COLORS.green}${name}${COLORS.reset}`);
        if (desc) log(`     ${COLORS.dim}${desc}${COLORS.reset}`);
      });
    }
  }

  // List templates
  if (fs.existsSync(templatesDir)) {
    const templates = fs.readdirSync(templatesDir).filter((f) => f.endsWith('.md'));
    if (templates.length > 0) {
      log('\n📄 Templates:', 'blue');
      templates.forEach((file) => {
        const name = file.replace('.md', '');
        const desc = getDescription(path.join(templatesDir, file));
        log(`  ${COLORS.green}${name}${COLORS.reset}`);
        if (desc) log(`     ${COLORS.dim}${desc}${COLORS.reset}`);
      });
    }
  }

  // List skills
  if (fs.existsSync(skillsDir)) {
    const skills = fs.readdirSync(skillsDir).filter((d) => {
      const stat = fs.statSync(path.join(skillsDir, d));
      return stat.isDirectory() && fs.existsSync(path.join(skillsDir, d, 'SKILL.md'));
    });
    if (skills.length > 0) {
      log('\n🛠️  Skills:', 'magenta');
      skills.forEach((skill) => {
        const desc = getDescription(path.join(skillsDir, skill, 'SKILL.md'));
        log(`  ${COLORS.green}${skill}${COLORS.reset}`);
        if (desc) log(`     ${COLORS.dim}${desc}${COLORS.reset}`);
      });
    }
  }

  // List optional addons
  log('\n📦 Optional Addons:', 'blue');
  OPTIONAL_ADDONS.forEach((addon) => {
    const tag = addon.type === 'local' ? `${COLORS.magenta}skill${COLORS.reset}` : `${COLORS.cyan}pack${COLORS.reset}`;
    log(`  ${COLORS.green}${addon.name}${COLORS.reset} ${COLORS.dim}[${tag}${COLORS.dim}]${COLORS.reset}`);
    log(`     ${COLORS.dim}${addon.desc}${COLORS.reset}`);
  });

  log('');
}

function copyRecursive(src, dest, baseDir) {
  const stats = fs.statSync(src);

  if (stats.isDirectory()) {
    if (!fs.existsSync(dest)) {
      fs.mkdirSync(dest, { recursive: true });
    }

    for (const item of fs.readdirSync(src)) {
      copyRecursive(path.join(src, item), path.join(dest, item), baseDir);
    }
  } else {
    const destDir = path.dirname(dest);
    if (!fs.existsSync(destDir)) {
      fs.mkdirSync(destDir, { recursive: true });
    }
    fs.copyFileSync(src, dest);
    log(`  → ${path.relative(baseDir, dest)}`, 'dim');
  }
}

function multiSelect(items) {
  return new Promise((resolve) => {
    const selected = new Set();
    let cursor = 0;
    let firstRender = true;

    const render = () => {
      // Move cursor up to redraw (skip on first render)
      const totalLines = items.length * 2 + 2; // 2 lines per item + header + blank
      if (!firstRender) {
        process.stdout.write(`\x1b[${totalLines}A\x1b[0J`); // Move up and clear to end of screen
      }
      firstRender = false;

      console.log(`${COLORS.dim}(↑↓ navigate, space select, enter confirm)${COLORS.reset}\n`);

      items.forEach((item, i) => {
        const checkbox = selected.has(i) ? `${COLORS.green}◉${COLORS.reset}` : `${COLORS.dim}○${COLORS.reset}`;
        const pointer = i === cursor ? `${COLORS.cyan}❯${COLORS.reset}` : ' ';
        const name = i === cursor ? `${COLORS.cyan}${item.name}${COLORS.reset}` : item.name;
        const tag = item.type === 'local' ? `${COLORS.magenta}skill${COLORS.reset}` : `${COLORS.cyan}pack${COLORS.reset}`;
        console.log(`${pointer} ${checkbox} ${name} ${COLORS.dim}[${tag}${COLORS.dim}]${COLORS.reset}`);
        console.log(`    ${COLORS.dim}${item.desc}${COLORS.reset}`);
      });
    };

    render();

    process.stdin.setRawMode(true);
    process.stdin.resume();
    process.stdin.setEncoding('utf8');

    const onKeypress = (key) => {
      // Ctrl+C
      if (key === '\u0003') {
        process.stdin.setRawMode(false);
        process.stdin.removeListener('data', onKeypress);
        process.exit();
      }

      // Enter
      if (key === '\r' || key === '\n') {
        process.stdin.setRawMode(false);
        process.stdin.removeListener('data', onKeypress);
        process.stdin.pause();
        console.log('');
        resolve([...selected].map((i) => items[i]));
        return;
      }

      // Space - toggle selection
      if (key === ' ') {
        if (selected.has(cursor)) {
          selected.delete(cursor);
        } else {
          selected.add(cursor);
        }
        render();
        return;
      }

      // Arrow up or k
      if (key === '\x1b[A' || key === 'k') {
        cursor = cursor > 0 ? cursor - 1 : items.length - 1;
        render();
        return;
      }

      // Arrow down or j
      if (key === '\x1b[B' || key === 'j') {
        cursor = cursor < items.length - 1 ? cursor + 1 : 0;
        render();
        return;
      }

      // 'a' - select all
      if (key === 'a') {
        if (selected.size === items.length) {
          selected.clear();
        } else {
          items.forEach((_, i) => selected.add(i));
        }
        render();
        return;
      }
    };

    process.stdin.on('data', onKeypress);
  });
}

function installLocalSkill(skillName) {
  const src = path.join(OPTIONAL_SKILLS_SOURCE, skillName);
  const targetDir = getTargetDir();
  const dest = path.join(targetDir, 'skills', skillName);

  if (!fs.existsSync(src)) {
    log(`   ⚠️  Skill "${skillName}" not found`, 'yellow');
    return false;
  }

  log(`\n🛠️  Installing ${skillName}...`, 'cyan');
  copyRecursive(src, dest, targetDir);
  return true;
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

function installAddon(addon) {
  if (addon.type === 'local') {
    return installLocalSkill(addon.name);
  }
  return installSkillPack(addon.name);
}

async function init(skipPrompts = false) {
  showLogo();
  log('─'.repeat(44), 'dim');

  if (!fs.existsSync(CONFIG_SOURCE)) {
    log('❌ Config source not found', 'yellow');
    process.exit(1);
  }

  // Install core config
  const targetDir = getTargetDir();
  log('\n📁 Installing core config to .claude/', 'green');
  copyRecursive(CONFIG_SOURCE, targetDir, targetDir);

  // Copy CLAUDE.md to project root
  const claudeMdSrc = path.join(__dirname, '..', 'CLAUDE.md');
  const claudeMdDest = path.join(process.cwd(), 'CLAUDE.md');
  if (fs.existsSync(claudeMdSrc)) {
    fs.copyFileSync(claudeMdSrc, claudeMdDest);
    log('  → CLAUDE.md', 'dim');
  }

  log('\n✅ Core config installed!', 'green');

  // Skip prompts if -y flag or non-interactive
  if (skipPrompts || !process.stdin.isTTY) {
    log('\n💡 Add optional skills & packs later:', 'dim');
    OPTIONAL_ADDONS.forEach((addon) => {
      if (addon.type === 'local') {
        log(`   npx devlyn-cli  (select "${addon.name}" during install)`, 'dim');
      } else {
        log(`   npx skills add ${addon.name}`, 'dim');
      }
    });
    log('');
    return;
  }

  // Ask about optional addons (local skills + external packs)
  log('\n📚 Optional skills & packs:\n', 'blue');

  const selectedAddons = await multiSelect(OPTIONAL_ADDONS);

  if (selectedAddons.length > 0) {
    for (const addon of selectedAddons) {
      installAddon(addon);
    }
  } else {
    log('💡 No optional addons selected', 'dim');
    log('   Run again to add them later\n', 'dim');
  }

  log('\n✨ All done!', 'green');
  log('   Run `npx devlyn-cli` again to update\n', 'dim');
}

function showHelp() {
  showLogo();
  log('Usage:', 'green');
  log('  npx devlyn-cli          Install/update .claude config');
  log('  npx devlyn-cli list     List available commands & templates');
  log('  npx devlyn-cli -y       Install without prompts');
  log('  npx devlyn-cli --help   Show this help\n');
  log('Optional skills (select during install):', 'green');
  OPTIONAL_ADDONS.filter((a) => a.type === 'local').forEach((skill) => {
    log(`  ${skill.name}  ${COLORS.dim}${skill.desc}${COLORS.reset}`);
  });
  log('\nExternal skill packs:', 'green');
  OPTIONAL_ADDONS.filter((a) => a.type === 'external').forEach((pack) => {
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
  case 'list':
  case 'ls':
    listContents();
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
