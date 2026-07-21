#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const os = require('os');
const readline = require('readline');
const { execSync } = require('child_process');

const CONFIG_SOURCE = path.join(__dirname, '..', 'config');
const OPTIONAL_SKILLS_SOURCE = path.join(__dirname, '..', 'optional-skills');
const PKG = require('../package.json');

// The devlyn skill bundle installed into every skill-capable agent's loader
// directory. Single source of truth so codex/omp/pi stay in lockstep — adding a
// skill here installs it everywhere. Standards skills (code-*, root-cause-*,
// ui-*) stay Claude-core-only, matching the pre-existing Codex bundle.
const DEVLYN_CORE_SKILLS = ['devlyn:resolve', 'devlyn:ideate', 'devlyn:design-ui', 'devlyn:engines', 'devlyn:queue', '_shared'];
const DEVLYN_SKILL_DIR_STAMP = '__DEVLYN_SKILL_DIR__';

// Cross-agent shared skills directory read by BOTH oh-my-pi and Pi. Verified
// from the omp binary's skill-provider strings ("skills from .agents/skills —
// project walk-up + user home") and Pi's docs ("~/.agents/skills/"). Installing
// the bundle here once covers both agents — the de-dup driver writes it a single
// time even when both are selected.
const SHARED_AGENTS_SKILLS_DIR = path.join(os.homedir(), '.agents', 'skills');

// Cross-CLI agent installation targets
// Each entry maps a CLI tool to where its agent instructions should be placed
const CLI_TARGETS = {
  codex: {
    name: 'Codex CLI (OpenAI)',
    instructionsFile: 'AGENTS.md',
    baseInstructionsFile: 'AGENTS.md',
    // Codex auto-loads skills from ~/.codex/skills/ (user-global). Same
    // SKILL.md format as Claude Code; descriptions must stay ≤1024 chars.
    skillsDir: path.join(os.homedir(), '.codex', 'skills'),
    skillsToInstall: DEVLYN_CORE_SKILLS,
    detect: () => fs.existsSync(path.join(process.cwd(), 'AGENTS.md')) || fs.existsSync(path.join(process.cwd(), '.codex')),
  },
  omp: {
    name: 'oh-my-pi (omp)',
    instructionsFile: 'AGENTS.md',
    baseInstructionsFile: 'AGENTS.md',
    // omp loads skills from ~/.agents/skills (user home) — shared with Pi.
    skillsDir: SHARED_AGENTS_SKILLS_DIR,
    skillsToInstall: DEVLYN_CORE_SKILLS,
    // Project-scoped only: machine-level ~/.omp must not auto-trigger a project
    // AGENTS.md write via `npx devlyn-cli agents` in an unrelated repo.
    detect: () => fs.existsSync(path.join(process.cwd(), '.omp')) || fs.existsSync(path.join(process.cwd(), '.agents')),
  },
  pi: {
    name: 'Pi (earendil-works)',
    instructionsFile: 'AGENTS.md',
    baseInstructionsFile: 'AGENTS.md',
    // Pi loads skills from ~/.agents/skills — shared with oh-my-pi.
    skillsDir: SHARED_AGENTS_SKILLS_DIR,
    skillsToInstall: DEVLYN_CORE_SKILLS,
    // Project-scoped only (see omp): machine-level ~/.pi must not auto-trigger.
    detect: () => fs.existsSync(path.join(process.cwd(), '.pi')) || fs.existsSync(path.join(process.cwd(), '.agents')),
  },
  grok: {
    name: 'Grok Build CLI (xAI)',
    instructionsFile: 'AGENTS.md',
    baseInstructionsFile: 'AGENTS.md',
    // Grok discovers same-format SKILL.md skills from ./.grok/skills >
    // <repo_root>/.grok/skills > ~/.grok/skills > ~/.claude/skills
    // (Claude-compatible); skills are slash-invocable in the Grok TUI.
    skillsDir: path.join(os.homedir(), '.grok', 'skills'),
    skillsToInstall: DEVLYN_CORE_SKILLS,
    // Project-scoped only: machine-level ~/.grok must not auto-trigger a project
    // AGENTS.md write via `npx devlyn-cli agents` in an unrelated repo.
    detect: () => fs.existsSync(path.join(process.cwd(), '.grok')),
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
  // Deleted entirely on 2026-05-14 (devlyn:team-design-ui merged into
  // devlyn:design-ui; devlyn:design-system removed outright). Entries kept
  // so users who previously opted in get their stale copies purged on upgrade.
  'skills/devlyn:team-design-ui',
  'skills/devlyn:design-system',
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
  { name: 'prompt-engineering', desc: 'Claude prompt optimization using Anthropic best practices', type: 'local' },
  { name: 'better-auth-setup', desc: 'Production-ready Better Auth + Hono + Drizzle + PostgreSQL auth setup', type: 'local' },
  { name: 'polar-billing-setup', desc: 'Polar usage-based / metered billing — correct setup + diagnose silent $0-billing failures', type: 'local' },
  { name: 'pyx-scan', desc: 'Check whether an AI agent skill is safe before installing', type: 'local' },
  { name: 'dokkit', desc: 'Document template filling for DOCX/HWPX — ingest, fill, review, export', type: 'local' },
  { name: 'devlyn:pencil-pull', desc: 'Pull Pencil designs into code with exact visual fidelity', type: 'local' },
  { name: 'devlyn:pencil-push', desc: 'Push codebase UI to Pencil canvas for design sync', type: 'local' },
  { name: 'devlyn:reap', desc: 'Safely reap orphaned MCP / codex / Superset child processes left behind by long Claude sessions', type: 'local' },
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
  { name: 'playwright', desc: 'Playwright MCP for browser testing — powers /devlyn:resolve BUILD_GATE browser tier', type: 'mcp', command: 'npx -y @playwright/mcp@latest' },
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

function shellDoubleQuoteDefault(value) {
  if (value.includes('\n')) {
    throw new Error(`Cannot stamp skill path with newline: ${value}`);
  }
  return value.replace(/[\\$"`}]/g, '\\$&');
}

function stampInstalledSkillDir(rootDir, skillDir) {
  // Stamp ONLY the assignment-default occurrence. The sentinel comparison
  // literal on the guard line must stay intact: stamping it makes the guard
  // compare the stamped default to itself and false-positive
  // BLOCKED:shared-dir-unresolved on every codex/omp run that executes the
  // block (CLAUDE_SKILL_DIR unset) — iter-0040 R3 latent finding.
  const assignmentStamp = '${CLAUDE_SKILL_DIR:-' + DEVLYN_SKILL_DIR_STAMP + '}';
  const stampedAssignment = '${CLAUDE_SKILL_DIR:-' + shellDoubleQuoteDefault(skillDir) + '}';

  function visit(current) {
    const stats = fs.statSync(current);
    if (stats.isDirectory()) {
      for (const item of fs.readdirSync(current)) {
        visit(path.join(current, item));
      }
      return;
    }
    if (path.extname(current) !== '.md') return;

    const content = fs.readFileSync(current, 'utf8');
    if (!content.includes(assignmentStamp)) return;
    fs.writeFileSync(current, content.split(assignmentStamp).join(stampedAssignment));
  }

  visit(rootDir);
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

function multiSelect(items, preselectedIndices = []) {
  return new Promise((resolve) => {
    const selected = new Set(preselectedIndices.filter((i) => i >= 0 && i < items.length));
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
  // skills are picked up by Codex/omp/Pi (and any future CLI with a skillsDir)
  // the same way required skills are. Existing dir, not new dir — we don't
  // create an agent install just because someone opted into a Claude-side skill.
  // De-dup by directory: omp and Pi share ~/.agents/skills, so the mirror runs
  // once per unique destination.
  const mirrored = new Set();
  for (const cli of Object.values(CLI_TARGETS)) {
    if (!cli.skillsDir || mirrored.has(cli.skillsDir) || !fs.existsSync(cli.skillsDir)) continue;
    mirrored.add(cli.skillsDir);
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

// Install devlyn:resolve + devlyn:ideate + devlyn:design-ui + _shared skills into a CLI's
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

  const removed = cleanupDeprecated(path.dirname(cli.skillsDir));
  if (removed > 0) {
    log(`\n🧹 Cleaned up ${removed} deprecated file${removed > 1 ? 's' : ''}`, 'yellow');
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
    stampInstalledSkillDir(dest, dest);
    copied++;
    log(`  → ${cli.skillsDir.replace(os.homedir(), '~')}/${skillName}`, 'dim');
  }
  return copied;
}

// Strip the legacy "# Devlyn Agent Instructions" block (the retired evaluator
// agent) that earlier installs appended to instruction files, so upgrades scrub
// it instead of carrying it forever. Anchors on the LAST marker so user content
// above a stray copy of the block is preserved.
const DEVLYN_AGENTS_MARKER = '# Devlyn Agent Instructions';
function stripManagedBlock(content) {
  const markerIdx = content.lastIndexOf(DEVLYN_AGENTS_MARKER);
  if (markerIdx > 0) {
    const sepIdx = content.lastIndexOf('\n---', markerIdx);
    return content.slice(0, sepIdx > 0 ? sepIdx : markerIdx).trimEnd();
  }
  return content.trimEnd();
}

// One-line description of exactly what selecting a CLI target installs, so the
// unified selector stays honest.
function targetDesc(cli) {
  if (cli.skillsDir) {
    return `${cli.instructionsFile} + devlyn skills → ${cli.skillsDir.replace(os.homedir(), '~')}`;
  }
  return `${cli.instructionsFile} instructions only`;
}

// Install the packaged base instruction file for a CLI (project AGENTS.md for
// codex/omp/pi). Creates it from the packaged base when missing; on existing
// files, scrubs the legacy appended block and otherwise leaves user content
// untouched. Returns true when the destination was written.
function installInstructionsForCLI(cliKey) {
  const cli = CLI_TARGETS[cliKey];
  if (!cli || !cli.baseInstructionsFile) return false;

  const destFile = path.join(process.cwd(), cli.instructionsFile);
  let content = null;
  if (fs.existsSync(destFile)) {
    const current = fs.readFileSync(destFile, 'utf8');
    if (current.includes(DEVLYN_AGENTS_MARKER)) {
      content = stripManagedBlock(current) + '\n';
    }
  } else {
    const baseInstructionsSrc = path.join(__dirname, '..', cli.baseInstructionsFile);
    if (fs.existsSync(baseInstructionsSrc)) {
      content = fs.readFileSync(baseInstructionsSrc, 'utf8');
    }
  }
  if (content === null) return false;

  log(`\n🤖 Installing instructions for ${cli.name}...`, 'cyan');
  fs.writeFileSync(destFile, content);
  log(`  → ${cli.instructionsFile}`, 'dim');
  return true;
}

// Install both instructions and skills for a single CLI. Used by the
// `agents <cli>` command; multi-target paths use installSelectedCLITargets.
function installAgentsForCLI(cliKey) {
  const instr = installInstructionsForCLI(cliKey);
  const skillsCopied = installSkillsForCLI(cliKey);
  if (skillsCopied > 0) {
    log(`  → ${skillsCopied} skill${skillsCopied > 1 ? 's' : ''} installed (devlyn:resolve / devlyn:ideate / devlyn:design-ui / _shared)`, 'dim');
  }
  return instr || skillsCopied > 0;
}

// Install instructions + skills for a set of selected CLI targets, writing each
// unique destination exactly once. omp and Pi share project AGENTS.md and the
// ~/.agents/skills dir, so selecting both does not duplicate writes — this is
// the researched "group the common" model: targets are the user's selection,
// destinations are the unit of work.
function installSelectedCLITargets(cliKeys) {
  const instrDone = new Set();
  const skillsDone = new Set();
  let count = 0;
  for (const cliKey of cliKeys) {
    const cli = CLI_TARGETS[cliKey];
    if (!cli) continue;
    const instrKey = cli.instructionsFile;
    if (!instrDone.has(instrKey)) {
      installInstructionsForCLI(cliKey);
      instrDone.add(instrKey);
    }
    if (cli.skillsDir && !skillsDone.has(cli.skillsDir)) {
      const copied = installSkillsForCLI(cliKey);
      if (copied > 0) {
        log(`  → ${copied} skill${copied > 1 ? 's' : ''} → ${cli.skillsDir.replace(os.homedir(), '~')}`, 'dim');
      }
      skillsDone.add(cli.skillsDir);
    }
    count++;
  }
  return count;
}

function installAgentsForAllDetected() {
  const detected = detectOtherCLIs();
  if (detected.length === 0) return 0;
  return installSelectedCLITargets(detected);
}

// Install the Claude Code core config: project .claude/ (skills, templates,
// settings, CLAUDE.md, .gitignore) plus global ~/.claude/settings.json tweaks.
// Extracted so the unified target selector installs it only when "Claude Code"
// is chosen. Behavior is unchanged from the previous unconditional core install.
function installClaudeCore() {
  const targetDir = getTargetDir();
  log('\n📁 Installing Claude Code config to .claude/', 'green');
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
    } catch (error) {
      throw new Error(`Cannot merge .claude/settings.json: ${error.message}`);
    }
  }
  if (!settings || typeof settings !== 'object' || Array.isArray(settings)) {
    throw new Error('Cannot merge .claude/settings.json: root must be a JSON object');
  }
  const hasOwnSetting = (key) => Object.prototype.hasOwnProperty.call(settings, key);
  let settingsChanged = false;
  if (!hasOwnSetting('env')) {
    settings.env = {};
    settingsChanged = true;
  }
  if (!settings.env || typeof settings.env !== 'object' || Array.isArray(settings.env)) {
    throw new Error('Cannot merge .claude/settings.json: env must be a JSON object');
  }
  // Auto-allow pipeline state directory and common git commands so resolve doesn't prompt
  if (!hasOwnSetting('permissions')) {
    settings.permissions = {};
    settingsChanged = true;
  }
  if (!settings.permissions || typeof settings.permissions !== 'object' || Array.isArray(settings.permissions)) {
    throw new Error('Cannot merge .claude/settings.json: permissions must be a JSON object');
  }
  if (!Object.prototype.hasOwnProperty.call(settings.permissions, 'allow')) {
    settings.permissions.allow = [];
    settingsChanged = true;
  }
  if (!Array.isArray(settings.permissions.allow)) {
    throw new Error('Cannot merge .claude/settings.json: permissions.allow must be an array');
  }
  const pipelinePermissions = [
    'Write(.devlyn/**)',
    'Edit(.devlyn/**)',
    'Bash(git add *)',
    'Bash(git commit *)',
    'Bash(git diff *)',
    'Bash(git status *)',
    'Bash(git log *)',
  ];
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
  if (!hasOwnSetting('hooks')) {
    settings.hooks = {};
    settingsChanged = true;
  }
  if (!settings.hooks || typeof settings.hooks !== 'object' || Array.isArray(settings.hooks)) {
    throw new Error('Cannot merge .claude/settings.json: hooks must be a JSON object');
  }
  if (!Object.prototype.hasOwnProperty.call(settings.hooks, 'Stop')) {
    settings.hooks.Stop = [];
    settingsChanged = true;
  }
  if (!Array.isArray(settings.hooks.Stop)) {
    throw new Error('Cannot merge .claude/settings.json: hooks.Stop must be an array');
  }
  const stopHookCommand = 'python3 "$CLAUDE_PROJECT_DIR/.claude/skills/_shared/resolve-stop-hook.py"';
  const stopHookInstalled = settings.hooks.Stop.some((entry) => (
    entry && Array.isArray(entry.hooks) && entry.hooks.some((hook) => (
      hook && hook.type === 'command' && hook.command === stopHookCommand
    ))
  ));
  if (!stopHookInstalled) {
    settings.hooks.Stop.push({
      hooks: [{ type: 'command', command: stopHookCommand, timeout: 30 }],
    });
    settingsChanged = true;
  }
  if (settingsChanged) {
    fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2) + '\n');
    log('  → settings.json (agent teams + pipeline permissions + Stop hook)', 'dim');
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

  log('\n✅ Claude Code config installed!', 'green');
}

async function init(skipPrompts = false) {
  showLogo();
  log('─'.repeat(44), 'dim');

  if (!fs.existsSync(CONFIG_SOURCE)) {
    log('❌ Config source not found', 'yellow');
    process.exit(1);
  }

  // Non-interactive / -y: preserve historical behavior — install Claude core
  // only. Multi-target selection needs a TTY; scripted runs add other agents
  // via `npx devlyn-cli agents <cli>`.
  if (skipPrompts || !process.stdin.isTTY) {
    installClaudeCore();
    log('\n💡 Add optional addons later: run `npx devlyn-cli` without -y', 'dim');
    log('   Add another agent (Codex / omp / Pi / …) later: `npx devlyn-cli agents <cli>`', 'dim');
    log(`\n${COLORS.dim}   Enjoying devlyn? Star it on GitHub — it helps others find it:${COLORS.reset}`);
    log(`   ${COLORS.purple}→ https://github.com/fysoul17/devlyn-cli${COLORS.reset}\n`);
    return;
  }

  // Pick every agent to install devlyn into, up front. Claude Code is
  // pre-checked (the happy path); every other agent is an explicit opt-in so a
  // bare Enter never mutates a project's AGENTS.md or a shared skills dir for an
  // agent the user didn't choose.
  log('\n🎯 Select the agents to install devlyn into:\n', 'blue');
  const targetOptions = [
    { key: 'claude', name: 'Claude Code', desc: '.claude/ config — skills, templates, settings, CLAUDE.md', type: 'cli' },
    ...Object.entries(CLI_TARGETS).map(([key, cli]) => ({ key, name: cli.name, desc: targetDesc(cli), type: 'cli' })),
  ];
  const preselected = [targetOptions.findIndex((o) => o.key === 'claude')];
  const selectedKeys = (await multiSelect(targetOptions, preselected)).map((t) => t.key);

  if (selectedKeys.length === 0) {
    log('\n💡 No agents selected — nothing installed.', 'yellow');
    log('   Run `npx devlyn-cli` again and pick at least one agent.\n', 'dim');
    return;
  }

  if (selectedKeys.includes('claude')) {
    installClaudeCore();
  }
  const cliKeys = selectedKeys.filter((k) => k !== 'claude');
  if (cliKeys.length > 0) {
    const installed = installSelectedCLITargets(cliKeys);
    log(`\n  ✅ Installed devlyn into ${installed} agent${installed !== 1 ? 's' : ''}`, 'green');
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
  log('  npx devlyn-cli              Install/update devlyn (pick agents: Claude / Codex / omp / Pi / …)');
  log('  npx devlyn-cli list         List available skills & templates');
  log('  npx devlyn-cli -y           Install Claude core without prompts');
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
      // Install for all supported CLIs regardless of detection. De-duped so the
      // shared ~/.agents/skills dir (omp + Pi) and shared AGENTS.md write once.
      log('\n🤖 Installing agents for all supported CLIs...', 'blue');
      const count = installSelectedCLITargets(Object.keys(CLI_TARGETS));
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
