#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const readline = require('readline');
const { execSync } = require('child_process');

const CONFIG_SOURCE = path.join(__dirname, '..', 'config');
const AGENTS_SOURCE = path.join(__dirname, '..', 'agents-config');
const OPTIONAL_SKILLS_SOURCE = path.join(__dirname, '..', 'optional-skills');
const PKG = require('../package.json');

// Cross-CLI agent installation targets
// Each entry maps a CLI tool to where its agent instructions should be placed
const CLI_TARGETS = {
  codex: {
    name: 'Codex CLI (OpenAI)',
    instructionsFile: 'AGENTS.md',
    configDir: null, // Codex uses AGENTS.md at project root
    detect: () => fs.existsSync(path.join(process.cwd(), 'AGENTS.md')) || fs.existsSync(path.join(process.cwd(), '.codex')),
  },
  gemini: {
    name: 'Gemini CLI (Google)',
    instructionsFile: 'GEMINI.md',
    configDir: null, // Gemini uses GEMINI.md at project root
    detect: () => fs.existsSync(path.join(process.cwd(), 'GEMINI.md')) || fs.existsSync(path.join(process.cwd(), '.gemini')),
  },
  cursor: {
    name: 'Cursor',
    instructionsFile: '.cursorrules',
    configDir: '.cursor/rules',
    detect: () => fs.existsSync(path.join(process.cwd(), '.cursorrules')) || fs.existsSync(path.join(process.cwd(), '.cursor')),
  },
  copilot: {
    name: 'GitHub Copilot',
    instructionsFile: '.github/copilot-instructions.md',
    configDir: '.github/copilot/agents',
    detect: () => fs.existsSync(path.join(process.cwd(), '.github', 'copilot-instructions.md')) || fs.existsSync(path.join(process.cwd(), '.github', 'copilot')),
  },
  windsurf: {
    name: 'Windsurf',
    instructionsFile: '.windsurfrules',
    configDir: '.windsurf/rules',
    detect: () => fs.existsSync(path.join(process.cwd(), '.windsurfrules')) || fs.existsSync(path.join(process.cwd(), '.windsurf')),
  },
};

// Files removed in previous versions that should be cleaned up on upgrade
const DEPRECATED_FILES = [
  'commands/devlyn.handoff.md', // removed in v0.2.0
  'commands/devlyn.clean.md', // migrated to skills in v0.6.0
  'commands/devlyn.design-system.md',
  'commands/devlyn.design-ui.md',
  'commands/devlyn.discover-product.md',
  'commands/devlyn.evaluate.md',
  'commands/devlyn.feature-spec.md',
  'commands/devlyn.implement-ui.md',
  'commands/devlyn.product-spec.md',
  'commands/devlyn.recommend-features.md',
  'commands/devlyn.resolve.md',
  'commands/devlyn.review.md',
  'commands/devlyn.team-design-ui.md',
  'commands/devlyn.team-resolve.md',
  'commands/devlyn.team-review.md',
  'commands/devlyn.update-docs.md',
  'commands/devlyn.pencil-pull.md', // migrated to skills/devlyn:pencil-pull
  'commands/devlyn.pencil-push.md', // migrated to skills/devlyn:pencil-push
];

// Skill directories renamed from devlyn-* to devlyn:* in v0.7.x
const DEPRECATED_DIRS = [
  'skills/devlyn-clean',
  'skills/devlyn-design-system',
  'skills/devlyn-design-ui',
  'skills/devlyn-discover-product',
  'skills/devlyn-evaluate',
  'skills/devlyn-feature-spec',
  'skills/devlyn-implement-ui',
  'skills/devlyn-product-spec',
  'skills/devlyn-recommend-features',
  'skills/devlyn-resolve',
  'skills/devlyn-review',
  'skills/devlyn-team-design-ui',
  'skills/devlyn-team-resolve',
  'skills/devlyn-team-review',
  'skills/devlyn-update-docs',
  'skills/devlyn-pencil-pull',
  'skills/devlyn-pencil-push',
];

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
  { name: 'generate-skill', desc: 'Create well-structured Claude Code skills following Anthropic best practices', type: 'local' },
  { name: 'prompt-engineering', desc: 'Claude 4 prompt optimization using Anthropic best practices', type: 'local' },
  { name: 'better-auth-setup', desc: 'Production-ready Better Auth + Hono + Drizzle + PostgreSQL auth setup', type: 'local' },
  { name: 'pyx-scan', desc: 'Check whether an AI agent skill is safe before installing', type: 'local' },
  { name: 'dokkit', desc: 'Document template filling for DOCX/HWPX — ingest, fill, review, export', type: 'local' },
  { name: 'devlyn:pencil-pull', desc: 'Pull Pencil designs into code with exact visual fidelity', type: 'local' },
  { name: 'devlyn:pencil-push', desc: 'Push codebase UI to Pencil canvas for design sync', type: 'local' },
  // External skill packs (installed via npx skills add)
  { name: 'vercel-labs/agent-skills', desc: 'React, Next.js, React Native best practices', type: 'external' },
  { name: 'supabase/agent-skills', desc: 'Supabase integration patterns', type: 'external' },
  { name: 'coreyhaines31/marketingskills', desc: 'Marketing automation and content skills', type: 'external' },
  { name: 'anthropics/skills', desc: 'Official Anthropic skill-creator with eval framework and description optimizer', type: 'external' },
  { name: 'Leonxlnx/taste-skill', desc: 'Premium frontend design skills — modern layouts, animations, and visual refinement', type: 'external' },
  // MCP servers (installed via claude mcp add)
  { name: 'codex-cli', desc: 'Codex MCP server for cross-model evaluation via OpenAI Codex', type: 'mcp', command: 'npx -y codex-mcp-server' },
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

  const templatesDir = path.join(CONFIG_SOURCE, 'templates');
  const skillsDir = path.join(CONFIG_SOURCE, 'skills');

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
    const tagLabel = addon.type === 'mcp' ? 'mcp' : addon.type === 'local' ? 'skill' : 'pack';
    const tagColor = addon.type === 'mcp' ? COLORS.green : addon.type === 'local' ? COLORS.magenta : COLORS.cyan;
    const tag = `${tagColor}${tagLabel}${COLORS.reset}`;
    log(`  ${COLORS.green}${addon.name}${COLORS.reset} ${COLORS.dim}[${tag}${COLORS.dim}]${COLORS.reset}`);
    log(`     ${COLORS.dim}${addon.desc}${COLORS.reset}`);
  });

  log('');
}

function cleanupDeprecated(targetDir) {
  let removed = 0;
  for (const relPath of DEPRECATED_FILES) {
    const fullPath = path.join(targetDir, relPath);
    if (fs.existsSync(fullPath)) {
      fs.unlinkSync(fullPath);
      log(`  ✕ ${relPath} (deprecated)`, 'dim');
      removed++;
    }
  }
  for (const relPath of DEPRECATED_DIRS) {
    const fullPath = path.join(targetDir, relPath);
    if (fs.existsSync(fullPath)) {
      fs.rmSync(fullPath, { recursive: true });
      log(`  ✕ ${relPath}/ (renamed)`, 'dim');
      removed++;
    }
  }
  return removed;
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
        const tagLabel = item.type === 'mcp' ? 'mcp' : item.type === 'local' ? 'skill' : 'pack';
        const tagColor = item.type === 'mcp' ? COLORS.green : item.type === 'local' ? COLORS.magenta : COLORS.cyan;
        const tag = `${tagColor}${tagLabel}${COLORS.reset}`;
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

function installMcpServer(name, command) {
  try {
    log(`\n🔌 Installing MCP server: ${name}...`, 'cyan');
    execSync(`claude mcp add ${name} -- ${command}`, { stdio: 'inherit' });
    return true;
  } catch (error) {
    log(`   ⚠️  Failed to install MCP server "${name}"`, 'yellow');
    log(`   Run manually: claude mcp add ${name} -- ${command}`, 'dim');
    return false;
  }
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
  if (addon.type === 'mcp') {
    return installMcpServer(addon.name, addon.command);
  }
  return installSkillPack(addon.name);
}

function detectOtherCLIs() {
  const detected = [];
  for (const [key, cli] of Object.entries(CLI_TARGETS)) {
    if (cli.detect()) {
      detected.push(key);
    }
  }
  return detected;
}

function installAgentsForCLI(cliKey) {
  const cli = CLI_TARGETS[cliKey];
  if (!cli) return false;
  if (!fs.existsSync(AGENTS_SOURCE)) return false;

  const agents = fs.readdirSync(AGENTS_SOURCE).filter((f) => f.endsWith('.md'));
  if (agents.length === 0) return false;

  log(`\n🤖 Installing agents for ${cli.name}...`, 'cyan');

  if (cli.configDir) {
    // CLI supports an agents directory — copy agent files there
    const destDir = path.join(process.cwd(), cli.configDir);
    if (!fs.existsSync(destDir)) {
      fs.mkdirSync(destDir, { recursive: true });
    }
    for (const file of agents) {
      const src = path.join(AGENTS_SOURCE, file);
      const dest = path.join(destDir, file);
      fs.copyFileSync(src, dest);
      log(`  → ${cli.configDir}/${file}`, 'dim');
    }
  } else {
    // CLI uses a single instructions file — append agent content
    const destFile = path.join(process.cwd(), cli.instructionsFile);
    const separator = '\n\n---\n\n# Devlyn Agent Instructions\n\n';
    const agentContent = agents.map((file) => {
      return fs.readFileSync(path.join(AGENTS_SOURCE, file), 'utf8');
    }).join('\n\n---\n\n');

    let existing = '';
    if (fs.existsSync(destFile)) {
      existing = fs.readFileSync(destFile, 'utf8');
      // Remove previous devlyn agent section if present
      const devlynMarker = '# Devlyn Agent Instructions';
      const markerIdx = existing.indexOf(devlynMarker);
      if (markerIdx > 0) {
        // Find the separator before the marker (---\n\n)
        const sepIdx = existing.lastIndexOf('---', markerIdx);
        existing = existing.slice(0, sepIdx > 0 ? sepIdx : markerIdx).trimEnd();
      }
    }

    fs.writeFileSync(destFile, existing + separator + agentContent + '\n');
    log(`  → ${cli.instructionsFile} (agent instructions appended)`, 'dim');
  }

  return true;
}

function installAgentsForAllDetected() {
  const detected = detectOtherCLIs();
  if (detected.length === 0) return 0;

  let installed = 0;
  for (const cliKey of detected) {
    if (installAgentsForCLI(cliKey)) installed++;
  }
  return installed;
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

  // Remove deprecated files from previous versions
  const removed = cleanupDeprecated(targetDir);
  if (removed > 0) {
    log(`\n🧹 Cleaned up ${removed} deprecated file${removed > 1 ? 's' : ''}`, 'yellow');
  }

  // Copy CLAUDE.md to project root
  const claudeMdSrc = path.join(__dirname, '..', 'CLAUDE.md');
  const claudeMdDest = path.join(process.cwd(), 'CLAUDE.md');
  if (fs.existsSync(claudeMdSrc)) {
    fs.copyFileSync(claudeMdSrc, claudeMdDest);
    log('  → CLAUDE.md', 'dim');
  }

  // Enable agent teams in project settings
  const settingsPath = path.join(targetDir, 'settings.json');
  let settings = {};
  if (fs.existsSync(settingsPath)) {
    try {
      settings = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
    } catch {
      settings = {};
    }
  }
  if (!settings.env) settings.env = {};
  // Auto-allow pipeline files so auto-resolve doesn't prompt for permission
  if (!settings.permissions) settings.permissions = {};
  if (!settings.permissions.allow) settings.permissions.allow = [];
  const pipelinePermissions = [
    'Write:.claude/done-criteria.md',
    'Write:.claude/EVAL-FINDINGS.md',
    'Edit:.claude/done-criteria.md',
    'Edit:.claude/EVAL-FINDINGS.md',
  ];
  let settingsChanged = false;
  for (const perm of pipelinePermissions) {
    if (!settings.permissions.allow.includes(perm)) {
      settings.permissions.allow.push(perm);
      settingsChanged = true;
    }
  }
  if (!settings.env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS) {
    settings.env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS = '1';
    settingsChanged = true;
  }
  if (settingsChanged) {
    fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2) + '\n');
    log('  → settings.json (agent teams + pipeline permissions)', 'dim');
  }

  // Install agents for other detected CLIs
  const detected = detectOtherCLIs();
  if (detected.length > 0) {
    log(`\n🔍 Detected other AI CLIs: ${detected.map((k) => CLI_TARGETS[k].name).join(', ')}`, 'blue');
    const agentsInstalled = installAgentsForAllDetected();
    if (agentsInstalled > 0) {
      log(`  ✅ Agent instructions installed for ${agentsInstalled} CLI${agentsInstalled > 1 ? 's' : ''}`, 'green');
    }
  }

  log('\n✅ Core config installed!', 'green');

  // Skip prompts if -y flag or non-interactive
  if (skipPrompts || !process.stdin.isTTY) {
    log('\n💡 Add optional addons later:', 'dim');
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
  log('  npx devlyn-cli              Install/update .claude config');
  log('  npx devlyn-cli list         List available skills & templates');
  log('  npx devlyn-cli -y           Install without prompts');
  log('  npx devlyn-cli agents       Install agents for detected CLIs');
  log('  npx devlyn-cli agents all   Install agents for all supported CLIs');
  log('  npx devlyn-cli --help       Show this help\n');
  log('Optional skills (select during install):', 'green');
  OPTIONAL_ADDONS.filter((a) => a.type === 'local').forEach((skill) => {
    log(`  ${skill.name}  ${COLORS.dim}${skill.desc}${COLORS.reset}`);
  });
  log('\nExternal skill packs:', 'green');
  OPTIONAL_ADDONS.filter((a) => a.type === 'external').forEach((pack) => {
    log(`  npx skills add ${pack.name}`);
  });
  log('\nMCP servers:', 'green');
  OPTIONAL_ADDONS.filter((a) => a.type === 'mcp').forEach((mcp) => {
    log(`  claude mcp add ${mcp.name} -- ${mcp.command}  ${COLORS.dim}${mcp.desc}${COLORS.reset}`);
  });
  log('\nSupported CLIs for agent installation:', 'green');
  for (const [key, cli] of Object.entries(CLI_TARGETS)) {
    log(`  ${key.padEnd(10)} ${cli.name}`);
  }
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
  case 'agents': {
    showLogo();
    log('─'.repeat(44), 'dim');
    const subArg = args[1];
    if (subArg === 'all') {
      // Install for all supported CLIs regardless of detection
      log('\n🤖 Installing agents for all supported CLIs...', 'blue');
      let count = 0;
      for (const cliKey of Object.keys(CLI_TARGETS)) {
        if (installAgentsForCLI(cliKey)) count++;
      }
      log(`\n✅ Agents installed for ${count} CLI${count !== 1 ? 's' : ''}`, 'green');
    } else if (subArg && CLI_TARGETS[subArg]) {
      // Install for a specific CLI
      installAgentsForCLI(subArg);
      log('\n✅ Done!', 'green');
    } else {
      // Auto-detect and install
      const detected = detectOtherCLIs();
      if (detected.length === 0) {
        log('\n🔍 No other AI CLIs detected in this project.', 'yellow');
        log('   Use `npx devlyn-cli agents all` to install for all supported CLIs', 'dim');
        log(`   Supported: ${Object.keys(CLI_TARGETS).join(', ')}`, 'dim');
      } else {
        log(`\n🔍 Detected: ${detected.map((k) => CLI_TARGETS[k].name).join(', ')}`, 'blue');
        const count = installAgentsForAllDetected();
        log(`\n✅ Agents installed for ${count} CLI${count !== 1 ? 's' : ''}`, 'green');
      }
    }
    log('');
    break;
  }
  case 'init':
  case undefined:
    init(false);
    break;
  default:
    log(`Unknown command: ${command}`, 'yellow');
    showHelp();
    process.exit(1);
}
