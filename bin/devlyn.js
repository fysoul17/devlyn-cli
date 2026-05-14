#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const os = require('os');
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
    baseInstructionsFile: 'AGENTS.md',
    configDir: null, // Codex uses AGENTS.md at project root
    // Codex auto-loads skills from ~/.codex/skills/ (user-global). Same
    // SKILL.md format as Claude Code; descriptions must stay ≤1024 chars.
    skillsDir: path.join(os.homedir(), '.codex', 'skills'),
    skillsToInstall: ['devlyn:resolve', 'devlyn:ideate', 'devlyn:design-ui', '_shared'],
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

// Skill directories renamed from devlyn-* to devlyn:* in v0.7.x, plus
// iter-0034 Phase 4 cutover (2026-05-03): 15 user skills deleted and 3 moved
// to optional-skills/. Listed here so post-cutover `npx devlyn-cli` upgrades
// force-remove stale legacy skill dirs from downstream `~/.claude/skills/`
// even though the source dirs no longer exist (cleanManagedSkillDirs only
// removes target dirs that still exist in source — without this list,
// deleted-from-source skills persist in user installs forever).
const DEPRECATED_DIRS = [
  // v0.7.x rename: devlyn-* → devlyn:*
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
  // iter-0034 Phase 4 cutover: deleted user skills
  'skills/devlyn:auto-resolve',
  'skills/devlyn:browser-validate',
  'skills/devlyn:clean',
  'skills/devlyn:discover-product',
  'skills/devlyn:evaluate',
  'skills/devlyn:feature-spec',
  'skills/devlyn:implement-ui',
  'skills/devlyn:preflight',
  'skills/devlyn:product-spec',
  'skills/devlyn:recommend-features',
  'skills/devlyn:review',
  'skills/devlyn:team-resolve',
  'skills/devlyn:team-review',
  'skills/devlyn:update-docs',
  // iter-0034 Phase 4 cutover: moved to optional-skills/. Force-removed on
  // upgrade so users only have them if they opt in via the interactive
  // installer (matches the pencil-pull / pencil-push pattern).
  'skills/devlyn:reap',
  'skills/devlyn:design-system',
  'skills/devlyn:team-design-ui',
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
${g}                v${PKG.version} ${COLORS.dim}· ${k}🍩 by Nocodecat @ Donut Studio${r}
`;
  console.log(logo);
}

const OPTIONAL_ADDONS = [
  // Local optional skills (copied to .claude/skills/)
  { name: 'asset-creator', desc: 'AI pixel art game asset pipeline — generate, chroma-key, catalog', type: 'local' },
  { name: 'cloudflare-nextjs-setup', desc: 'Cloudflare Workers + Next.js deployment with OpenNext', type: 'local' },
  { name: 'generate-skill', desc: 'Create well-structured Claude Code skills following Anthropic best practices', type: 'local' },
  { name: 'prompt-engineering', desc: 'Claude 4 prompt optimization using Anthropic best practices', type: 'local' },
  { name: 'better-auth-setup', desc: 'Production-ready Better Auth + Hono + Drizzle + PostgreSQL auth setup', type: 'local' },
  { name: 'pyx-scan', desc: 'Check whether an AI agent skill is safe before installing', type: 'local' },
  { name: 'dokkit', desc: 'Document template filling for DOCX/HWPX — ingest, fill, review, export', type: 'local' },
  { name: 'devlyn:pencil-pull', desc: 'Pull Pencil designs into code with exact visual fidelity', type: 'local' },
  { name: 'devlyn:pencil-push', desc: 'Push codebase UI to Pencil canvas for design sync', type: 'local' },
  { name: 'devlyn:reap', desc: 'Safely reap orphaned MCP / codex / Superset child processes left behind by long Claude sessions', type: 'local' },
  { name: 'devlyn:design-system', desc: 'Extract design tokens from a chosen UI style for exact reproduction (creative power-user)', type: 'local' },
  { name: 'devlyn:team-design-ui', desc: '5 distinct UI style explorations from a full design team (creative power-user)', type: 'local' },
  // External skill packs (installed via npx skills add)
  { name: 'vercel-labs/agent-skills', desc: 'React, Next.js, React Native best practices', type: 'external' },
  { name: 'supabase/agent-skills', desc: 'Supabase integration patterns', type: 'external' },
  { name: 'coreyhaines31/marketingskills', desc: 'Marketing automation and content skills', type: 'external' },
  { name: 'anthropics/skills', desc: 'Official Anthropic skill-creator with eval framework and description optimizer', type: 'external' },
  { name: 'Leonxlnx/taste-skill', desc: 'Premium frontend design skills — modern layouts, animations, and visual refinement', type: 'external' },
  // MCP servers (installed via claude mcp add)
  // Note: the Codex integration uses the local `codex` CLI binary (not MCP).
  // Install the CLI separately per https://platform.openai.com/docs/codex — the
  // pair/risk-probe routes fail closed when Codex is required but unavailable.
  { name: 'playwright', desc: 'Playwright MCP for browser testing — powers /devlyn:resolve BUILD_GATE browser tier', type: 'mcp', command: 'npx -y @anthropic-ai/mcp-playwright' },
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
      log(`  ✕ ${relPath}/ (removed)`, 'dim');
      removed++;
    }
  }
  return removed;
}

function copyRecursive(src, dest, baseDir) {
  const stats = fs.statSync(src);

  if (stats.isDirectory()) {
    // Never install dev workspaces, even when running from source repo.
    if (UNSHIPPED_SKILL_DIRS.has(path.basename(src))) return;
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

// Dev artifacts that live under config/skills/ but must never ship or install.
// Mirrors the `!` exclusions in package.json files[].
const UNSHIPPED_SKILL_DIRS = new Set([
  'devlyn:auto-resolve-workspace',
  'devlyn:ideate-workspace',
  'preflight-workspace',
  'roadmap-archival-workspace',
]);

// Clean managed skill directories before copy to prevent stale-file drift.
// copyRecursive is a pure overlay: if a file was removed or renamed in source,
// the installed mirror keeps the old copy. For each top-level dir under
// config/skills/, remove its counterpart in target/skills/ before the copy so
// each managed skill is fully replaced on every sync. User-installed skills
// (e.g. skill-creator from optional addons) are left alone because they have
// no counterpart in source. Dev workspaces are skipped entirely.
function cleanManagedSkillDirs(sourceSkillsDir, targetSkillsDir) {
  if (!fs.existsSync(sourceSkillsDir) || !fs.existsSync(targetSkillsDir)) return 0;
  let cleaned = 0;
  for (const entry of fs.readdirSync(sourceSkillsDir, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    if (UNSHIPPED_SKILL_DIRS.has(entry.name)) continue;
    const targetPath = path.join(targetSkillsDir, entry.name);
    if (fs.existsSync(targetPath)) {
      fs.rmSync(targetPath, { recursive: true, force: true });
      cleaned++;
    }
  }
  return cleaned;
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
        const tagLabel = item.type === 'mcp' ? 'mcp' : item.type === 'local' ? 'skill' : item.type === 'cli' ? 'cli' : 'pack';
        const tagColor = item.type === 'mcp' ? COLORS.green : item.type === 'local' ? COLORS.magenta : item.type === 'cli' ? COLORS.blue : COLORS.cyan;
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

  // Mirror to every CLI skill-loader directory that already exists so optional
  // skills are picked up by Codex (and any future CLI with a skillsDir) the
  // same way required skills are. Existing dir, not new dir — we don't create
  // a Codex install just because someone opted into a Claude-side skill.
  for (const cli of Object.values(CLI_TARGETS)) {
    if (!cli.skillsDir || !fs.existsSync(cli.skillsDir)) continue;
    const cliDest = path.join(cli.skillsDir, skillName);
    if (fs.existsSync(cliDest)) fs.rmSync(cliDest, { recursive: true, force: true });
    copyRecursive(src, cliDest, cli.skillsDir);
  }
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

// Install /devlyn:resolve + /devlyn:ideate + /devlyn:design-ui + _shared skills into a CLI's
// global skills directory (e.g. ~/.codex/skills/). Returns count of skills
// copied. Skipped silently for CLIs without a skillsDir (e.g. cursor, copilot
// at the time of writing — they don't have an analogous skill-loader).
function installSkillsForCLI(cliKey) {
  const cli = CLI_TARGETS[cliKey];
  if (!cli || !cli.skillsDir || !cli.skillsToInstall) return 0;

  const sourceSkillsDir = path.join(CONFIG_SOURCE, 'skills');
  if (!fs.existsSync(sourceSkillsDir)) return 0;
  if (!fs.existsSync(cli.skillsDir)) {
    fs.mkdirSync(cli.skillsDir, { recursive: true });
  }

  let copied = 0;
  for (const skillName of cli.skillsToInstall) {
    const src = path.join(sourceSkillsDir, skillName);
    const dest = path.join(cli.skillsDir, skillName);
    if (!fs.existsSync(src)) continue;
    // Full replace per cleanManagedSkillDirs semantics: stale files in the
    // installed mirror would otherwise persist forever.
    if (fs.existsSync(dest)) {
      fs.rmSync(dest, { recursive: true, force: true });
    }
    copyRecursive(src, dest, cli.skillsDir);
    copied++;
    log(`  → ${cli.skillsDir.replace(os.homedir(), '~')}/${skillName}`, 'dim');
  }
  return copied;
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
    } else if (cli.baseInstructionsFile) {
      const baseInstructionsSrc = path.join(__dirname, '..', cli.baseInstructionsFile);
      if (fs.existsSync(baseInstructionsSrc)) {
        existing = fs.readFileSync(baseInstructionsSrc, 'utf8').trimEnd();
      }
    }

    fs.writeFileSync(destFile, existing + separator + agentContent + '\n');
    log(`  → ${cli.instructionsFile} (agent instructions appended)`, 'dim');
  }

  // If this CLI also supports a global skill-loader (currently Codex), install
  // /devlyn:resolve + /devlyn:ideate + /devlyn:design-ui + _shared so the same
  // slash commands work there. Skipped for CLIs without a skillsDir entry.
  const skillsCopied = installSkillsForCLI(cliKey);
  if (skillsCopied > 0) {
    log(`  → ${skillsCopied} skill${skillsCopied > 1 ? 's' : ''} installed (devlyn:resolve / devlyn:ideate / devlyn:design-ui / _shared)`, 'dim');
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
  const refreshed = cleanManagedSkillDirs(
    path.join(CONFIG_SOURCE, 'skills'),
    path.join(targetDir, 'skills'),
  );
  if (refreshed > 0) {
    log(`  🔄 Refreshing ${refreshed} managed skill director${refreshed === 1 ? 'y' : 'ies'}`, 'dim');
  }
  copyRecursive(CONFIG_SOURCE, targetDir, targetDir);

  // Remove deprecated files from previous versions
  const removed = cleanupDeprecated(targetDir);
  if (removed > 0) {
    log(`\n🧹 Cleaned up ${removed} deprecated file${removed > 1 ? 's' : ''}`, 'yellow');
  }

  // Copy Claude project instructions to project root. Other CLI instruction
  // files are installed only when explicitly selected below or via `agents`.
  const claudeMdSrc = path.join(__dirname, '..', 'CLAUDE.md');
  const claudeMdDest = path.join(process.cwd(), 'CLAUDE.md');
  if (fs.existsSync(claudeMdSrc)) {
    fs.copyFileSync(claudeMdSrc, claudeMdDest);
    log('  → CLAUDE.md', 'dim');
  }

  // Add .devlyn/ (pipeline state directory) to .gitignore
  const gitignorePath = path.join(process.cwd(), '.gitignore');
  const gitignoreEntry = '.devlyn/';
  let gitignoreContent = fs.existsSync(gitignorePath)
    ? fs.readFileSync(gitignorePath, 'utf8')
    : '';
  if (!gitignoreContent.split('\n').some((line) => line.trim() === gitignoreEntry || line.trim() === '.devlyn')) {
    const prefix = gitignoreContent && !gitignoreContent.endsWith('\n') ? '\n' : '';
    const header = gitignoreContent ? '\n# devlyn-cli pipeline state\n' : '# devlyn-cli pipeline state\n';
    fs.writeFileSync(gitignorePath, gitignoreContent + prefix + header + gitignoreEntry + '\n');
    log('  → .gitignore (added .devlyn/)', 'dim');
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
  // Auto-allow pipeline state directory and common git commands so resolve doesn't prompt
  if (!settings.permissions) settings.permissions = {};
  if (!settings.permissions.allow) settings.permissions.allow = [];
  const pipelinePermissions = [
    'Write(.devlyn/**)',
    'Edit(.devlyn/**)',
    'Bash(git add *)',
    'Bash(git commit *)',
    'Bash(git diff *)',
    'Bash(git status *)',
    'Bash(git log *)',
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

  // Configure global Claude Code settings (~/.claude/settings.json)
  const globalClaudeDir = path.join(os.homedir(), '.claude');
  const globalSettingsPath = path.join(globalClaudeDir, 'settings.json');
  let globalSettings = {};
  if (fs.existsSync(globalSettingsPath)) {
    try {
      globalSettings = JSON.parse(fs.readFileSync(globalSettingsPath, 'utf8'));
    } catch {
      globalSettings = {};
    }
  }
  if (!globalSettings.env) globalSettings.env = {};
  let globalSettingsChanged = false;
  if (!globalSettings.env.CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING) {
    globalSettings.env.CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING = '1';
    globalSettingsChanged = true;
  }
  if (!globalSettings.env.ENABLE_PROMPT_CACHING_1H) {
    globalSettings.env.ENABLE_PROMPT_CACHING_1H = 'true';
    globalSettingsChanged = true;
  }
  if (globalSettingsChanged) {
    if (!fs.existsSync(globalClaudeDir)) fs.mkdirSync(globalClaudeDir, { recursive: true });
    fs.writeFileSync(globalSettingsPath, JSON.stringify(globalSettings, null, 2) + '\n');
    log('  → ~/.claude/settings.json (disabled adaptive thinking, enabled 1h prompt caching)', 'dim');
  }

  log('\n✅ Core config installed!', 'green');

  // Skip prompts if -y flag or non-interactive
  if (skipPrompts || !process.stdin.isTTY) {
    log('\n💡 Add optional addons later: run `npx devlyn-cli` without -y', 'dim');
    log('   Add Codex instructions + skills later: run `npx devlyn-cli agents codex`', 'dim');
    log(`\n${COLORS.dim}   Enjoying devlyn? Star it on GitHub — it helps others find it:${COLORS.reset}`);
    log(`   ${COLORS.purple}→ https://github.com/fysoul17/devlyn-cli${COLORS.reset}\n`);
    return;
  }

  // Ask which non-Claude CLIs should receive instruction files.
  log('\n🤖 Optional AI CLI instructions:\n', 'blue');
  const cliOptions = Object.entries(CLI_TARGETS).map(([key, cli]) => {
    let desc;
    if (cli.configDir) {
      desc = `Install agents into ${cli.configDir}/`;
    } else if (cli.skillsDir) {
      desc = `Install ${cli.instructionsFile} + /devlyn:resolve + /devlyn:ideate + /devlyn:design-ui skills (~/.codex/skills/)`;
    } else {
      desc = `Install ${cli.instructionsFile}`;
    }
    return { key, name: cli.name, desc, type: 'cli' };
  });
  const selectedClis = await multiSelect(cliOptions);
  if (selectedClis.length > 0) {
    let agentsInstalled = 0;
    for (const selectedCli of selectedClis) {
      if (installAgentsForCLI(selectedCli.key)) agentsInstalled++;
    }
    log(`  ✅ Agent instructions installed for ${agentsInstalled} CLI${agentsInstalled !== 1 ? 's' : ''}`, 'green');
  } else {
    log('💡 No additional CLI instructions selected', 'dim');
    log('   Run `npx devlyn-cli agents codex` later to install Codex AGENTS.md + /devlyn skills', 'dim');
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
  log('   Run `npx devlyn-cli` again to update', 'dim');
  log(`\n${COLORS.dim}   Enjoying devlyn? Star it on GitHub — it helps others find it:${COLORS.reset}`);
  log(`   ${COLORS.purple}→ https://github.com/fysoul17/devlyn-cli${COLORS.reset}\n`);
}

function showHelp() {
  showLogo();
  log('Usage:', 'green');
  log('  npx devlyn-cli              Install/update .claude config');
  log('  npx devlyn-cli list         List available skills & templates');
  log('  npx devlyn-cli -y           Install without prompts');
  log('  npx devlyn-cli agents       Install agents for detected CLIs');
  log('  npx devlyn-cli agents all   Install agents for all supported CLIs');
  log('  npx devlyn-cli benchmark    Run the resolve benchmark suite');
  log('  npx devlyn-cli benchmark recent              Show compact recent benchmark results');
  log('  npx devlyn-cli benchmark frontier            Show pair candidate frontier scores/triggers without providers');
  log('  npx devlyn-cli benchmark audit               Audit pair evidence readiness');
  log('  npx devlyn-cli benchmark audit-headroom      Audit failed headroom results');
  log('  npx devlyn-cli benchmark headroom <fixtures...>  Score bare vs solo_claude headroom');
  log('  npx devlyn-cli benchmark pair <fixtures...>      Score solo_claude vs pair path');
  log('  npx devlyn-cli benchmark --bless         If ship-gate passes, promote baseline');
  log('  npx devlyn-cli benchmark --dry-run       Validate suite setup without model invocation');
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

function showBenchmarkHelp() {
  log('Usage:', 'green');
  log('  npx devlyn-cli benchmark [suite] [options] [fixtures...]');
  log('  npx devlyn-cli benchmark recent [options]');
  log('  npx devlyn-cli benchmark frontier [options]');
  log('  npx devlyn-cli benchmark audit [options]');
  log('  npx devlyn-cli benchmark audit-headroom [options]');
  log('  npx devlyn-cli benchmark headroom [options] <fixtures...>');
  log('  npx devlyn-cli benchmark pair [options] <fixtures...>');
  log('');
  log('Score-focused runs:', 'green');
  log('  recent   Show compact, wrap-safe recent benchmark results');
  log('  frontier Show active rejected/evidence/unmeasured pair candidates, scores, and triggers without providers');
  log('  audit     Fail on unmeasured pair candidates and invalid headroom rejections');
  log('            Prints frontier score rows plus headroom and pair quality handoff rows');
  log('  audit-headroom  Fail on active failed or unsupported headroom rejections');
  log('  headroom  Score bare vs solo_claude before spending the pair arm');
  log('  pair      Score solo_claude vs the selected pair path and print gate tables');
  log('');
  log('Shadow suite:', 'green');
  log('  npx devlyn-cli benchmark suite --suite shadow --dry-run');
  log('            Lists shadow tasks only; use headroom/pair with explicit S* ids for real measurement');
  log('');
  log('Examples:', 'green');
  log('  npx devlyn-cli benchmark --dry-run F1-cli-trivial-flag');
  log('  npx devlyn-cli benchmark recent');
  log('  npx devlyn-cli benchmark recent --out-md /tmp/devlyn-recent-benchmark.md');
  log('  npx devlyn-cli benchmark frontier --out-md /tmp/devlyn-pair-frontier.md');
  log('  npx devlyn-cli benchmark audit --out-dir /tmp/devlyn-benchmark-audit');
  log('  npx devlyn-cli benchmark audit-headroom --out-json /tmp/devlyn-headroom-audit.json');
  log('  npx devlyn-cli benchmark headroom --min-fixtures 3 F16-cli-quote-tax-rules F23-cli-fulfillment-wave F25-cli-cart-promotion-rules');
  log('  npx devlyn-cli benchmark pair --min-fixtures 3 --max-pair-solo-wall-ratio 3 F16-cli-quote-tax-rules F23-cli-fulfillment-wave F25-cli-cart-promotion-rules');
  log('');
}

function showBenchmarkModeHelp(mode) {
  if (mode === 'recent') {
    log('Usage:', 'green');
    log('  npx devlyn-cli benchmark recent [options]');
    log('');
    log('Options:', 'green');
    log('  --out-json PATH');
    log('  --out-md PATH');
    log('  --fixtures-root PATH');
    log('  --registry PATH');
    log('  --results-root PATH');
    log('  --max-width N  default: 92');
    log('  --min-pair-margin N  default: 5');
    log('  --max-pair-solo-wall-ratio N  default: 3');
    log('');
    log('Output:', 'green');
    log('  Prints compact, wrap-safe benchmark status and pair-evidence cards without wide tables');
    log('');
    log('Example:', 'green');
    log('  npx devlyn-cli benchmark recent');
    log('  npx devlyn-cli benchmark recent --out-md /tmp/devlyn-recent-benchmark.md');
    log('');
    return;
  }
  if (mode === 'frontier') {
    log('Usage:', 'green');
    log('  npx devlyn-cli benchmark frontier [options]');
    log('');
    log('Options:', 'green');
    log('  --out-json PATH');
    log('  --out-md PATH');
    log('  --fixtures-root PATH');
    log('  --registry PATH');
    log('  --results-root PATH');
    log('  --min-pair-margin N  default: 5');
    log('  --max-pair-solo-wall-ratio N  default: 3');
    log('  --fail-on-unmeasured');
    log('');
    log('Output:', 'green');
    log('  Prints pair evidence score rows with trigger reasons; --out-md includes a Triggers column');
    log('');
    log('Example:', 'green');
    log('  npx devlyn-cli benchmark frontier --out-md /tmp/devlyn-pair-frontier.md');
    log('');
    return;
  }
  if (mode === 'audit-headroom') {
    log('Usage:', 'green');
    log('  npx devlyn-cli benchmark audit-headroom [options]');
    log('');
    log('Options:', 'green');
    log('  --out-json PATH');
    log('  --fixtures-root PATH');
    log('  --registry PATH');
    log('  --results-root PATH');
    log('');
    log('Example:', 'green');
    log('  npx devlyn-cli benchmark audit-headroom --out-json /tmp/devlyn-headroom-audit.json');
    log('');
    return;
  }
  if (mode === 'audit') {
    log('Usage:', 'green');
    log('  npx devlyn-cli benchmark audit [options]');
    log('');
    log('Options:', 'green');
    log('  --out-dir PATH');
    log('  --fixtures-root PATH');
    log('  --registry PATH');
    log('  --results-root PATH');
    log('  --min-pair-evidence N  default: 4');
    log('  --min-pair-margin N  default: 5');
    log('  --max-pair-solo-wall-ratio N  default: 3');
    log('  --require-hypothesis-trigger');
    log('');
    log('Output:', 'green');
    log('  Prints frontier score rows plus headroom_rejections=PASS/FAIL, pair_evidence_quality=PASS/FAIL, pair_trigger_reasons=PASS/FAIL, pair_evidence_hypotheses=PASS/FAIL, pair_evidence_hypothesis_triggers=PASS/WARN/FAIL, historical-alias, and hypothesis-trigger gap handoff rows');
    log('');
    log('Example:', 'green');
    log('  npx devlyn-cli benchmark audit --out-dir /tmp/devlyn-benchmark-audit');
    log('  npx devlyn-cli benchmark audit --require-hypothesis-trigger --out-dir /tmp/devlyn-benchmark-audit-strict');
    log('');
    return;
  }
  if (mode === 'headroom') {
    log('Usage:', 'green');
    log('  npx devlyn-cli benchmark headroom [options] <fixtures...>');
    log('');
    log('Options:', 'green');
    log('  --run-id ID');
    log('  --bare-max N       default: 60');
    log('  --solo-max N       default: 80');
    log('  --min-bare-headroom N  default: 5');
    log('  --min-solo-headroom N  default: 5');
    log('  --min-fixtures N   default: 2; use 3 for F16/F23/F25 proof reruns; audit requires 4 passing evidence rows');
    log('  --allow-rejected-fixtures  active-fixture diagnostics only');
    log('  --dry-run          validate args/fixtures and print replay command only');
    log('');
    log('Example:', 'green');
    log('  npx devlyn-cli benchmark headroom --min-fixtures 3 F16-cli-quote-tax-rules F23-cli-fulfillment-wave F25-cli-cart-promotion-rules');
    log('');
    return;
  }
  if (mode === 'pair') {
    log('Usage:', 'green');
    log('  npx devlyn-cli benchmark pair [options] <fixtures...>');
    log('');
    log('Options:', 'green');
    log('  --run-id ID');
    log('  --bare-max N');
    log('  --solo-max N');
    log('  --min-bare-headroom N  default: 5');
    log('  --min-solo-headroom N  default: 5');
    log('  --min-fixtures N   default: 2; use 3 for F16/F23/F25 proof reruns; audit requires 4 passing evidence rows');
    log('  --min-pair-margin N  default: 5');
    log('  --max-pair-solo-wall-ratio N  default: 3');
    log('  --pair-arm ARM  default: l2_risk_probes; l2_gated is diagnostic');
    log('  --reuse-calibrated-from RUN_ID');
    log('  --allow-rejected-fixtures  active-fixture diagnostics only');
    log('  --dry-run       validate args/fixtures and print replay command only');
    log('');
    log('Example:', 'green');
    log('  npx devlyn-cli benchmark pair --min-fixtures 3 --max-pair-solo-wall-ratio 3 F16-cli-quote-tax-rules F23-cli-fulfillment-wave F25-cli-cart-promotion-rules');
    log('');
    return;
  }
  showBenchmarkHelp();
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
  case 'benchmark':
  case 'bench': {
    const benchmarkScripts = {
      suite: 'run-suite.sh',
      recent: 'recent-benchmark-summary.py',
      frontier: 'pair-candidate-frontier.py',
      audit: 'audit-pair-evidence.py',
      'audit-headroom': 'audit-headroom-rejections.py',
      headroom: 'run-headroom-candidate.sh',
      pair: 'run-full-pipeline-pair-candidate.sh',
    };
    let forwardedArgs = args.slice(1);
    if (forwardedArgs[0] === '--help' || forwardedArgs[0] === '-h') {
      showBenchmarkHelp();
      break;
    }
    let benchmarkMode = 'suite';
    if (forwardedArgs[0] === 'suite' || forwardedArgs[0] === 'recent' || forwardedArgs[0] === 'frontier' || forwardedArgs[0] === 'audit' || forwardedArgs[0] === 'audit-headroom' || forwardedArgs[0] === 'headroom' || forwardedArgs[0] === 'pair') {
      benchmarkMode = forwardedArgs[0];
      forwardedArgs = forwardedArgs.slice(1);
    }
    if (forwardedArgs[0] === '--help' || forwardedArgs[0] === '-h') {
      showBenchmarkModeHelp(benchmarkMode);
      break;
    }
    const runnerName = benchmarkScripts[benchmarkMode];
    const runner = path.join(__dirname, '..', 'benchmark', 'auto-resolve', 'scripts', runnerName);
    if (!fs.existsSync(runner)) {
      log('❌ Benchmark suite runner missing — is this a clean devlyn-cli checkout?', 'yellow');
      log(`   Expected: ${runner}`, 'dim');
      process.exit(1);
    }
    const { spawnSync } = require('child_process');
    const env = { ...process.env, DEVLYN_BENCHMARK_CLI_SUBCOMMAND: benchmarkMode };
    const executable = (benchmarkMode === 'recent' || benchmarkMode === 'frontier' || benchmarkMode === 'audit' || benchmarkMode === 'audit-headroom') ? 'python3' : 'bash';
    const res = spawnSync(executable, [runner, ...forwardedArgs], { stdio: 'inherit', env });
    process.exit(res.status ?? 1);
    break;
  }
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
