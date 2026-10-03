#!/usr/bin/env node

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const os = require('os');
const readline = require('readline');
const { execSync } = require('child_process');

const CONFIG_SOURCE = path.join(__dirname, '..', 'config');
const OPTIONAL_SKILLS_SOURCE = path.join(__dirname, '..', 'optional-skills');
const PKG = require('../package.json');
const { updateInstructions, InstructionError, holdsDevlynDefaults } = require('./instructions');

// The devlyn skill bundle installed into every skill-capable agent's loader
// directory. Single source of truth so codex/omp/pi stay in lockstep — adding a
// skill here installs it everywhere.
const DEVLYN_CORE_SKILLS = ['devlyn-resolve', 'devlyn-ideate', 'devlyn-design-ui', 'devlyn-engines', 'devlyn-queue', '_shared'];
// 4.0.0 renamed the colon-named skills to the Agent Skills standard (`[a-z0-9-]`, name ==
// folder): Git for Windows cannot check out a folder with ':' in its name. Installs from 3.x
// and earlier keep the old folder under either spelling (':' or npm's U+F03A extraction
// alias). Both are removed, and an optional skill that was installed is installed again
// under its new name in the same place.
const RENAMED_SKILLS = {
  'devlyn:resolve': 'devlyn-resolve',
  'devlyn:ideate': 'devlyn-ideate',
  'devlyn:design-ui': 'devlyn-design-ui',
  'devlyn:engines': 'devlyn-engines',
  'devlyn:queue': 'devlyn-queue',
  'devlyn:pencil-pull': 'devlyn-pencil-pull',
  'devlyn:pencil-push': 'devlyn-pencil-push',
  'devlyn:reap': 'devlyn-reap',
};
const DEVLYN_INSTALL_MARKER = '.devlyn-install.json';

// Every spelling a colon name can have on disk: its own and npm's U+F03A extraction alias.
function legacySkillPaths(root, name) {
  return [...new Set([name, name.replace(/:/g, '\uF03A')])].map((spelling) => path.join(root, spelling));
}

// SKILL.md of the pencil skills 0.6.0-0.7.1 installed under today's names, without the
// frontmatter the standard requires, hashed with LF line endings (a Windows checkout may hold
// CRLF). 3.x deleted these copies; 4.0 replaces them.
const PRE_STANDARD_SKILL_MD_SHA256 = new Set([
  'dfdd3d19ca676558bfa2bb3ce398181b0a081ab88d1feaf69c54c706a9671631', // devlyn-pencil-pull
  '5f2e8b29609cbb2af72941579823bec598265ebf29cd3a375d6aa47d95b74354', // devlyn-pencil-push
]);

// Skills devlyn-cli installed by default and later deleted or made opt-in, by SHA-256 of their
// only file, SKILL.md (LF endings): an opted-in copy or a user's own folder of the same name is
// never removed.
const RETIRED_SKILL_MD_SHA256 = {
  // 0.2.0-1.15.0; deleted in iter-0034, it still routes agents to retired commands.
  'workflow-routing': new Set([
    '7fec2bb20d808a873a975d64a6223e404bc5b328c800760bb77257ae6b2f467a',
    '8bfdaeff2ce48d5a79b5653de3bbe0d56a61a7fd750ed3ad11149fec5a502ecf',
  ]),
  // The standards skills, 0.1.0-3.2.1; 3.3.0 (0221) made them optional addons.
  'code-health-standards': new Set([
    'df2838904c938aa0306ed333cc460cfc5c2cf0ffa20bb5ade57067c6e0acf9be',
    '962a82b5ebeafac515f81f5c68494c67dbf31c3e3e453f23c4452d4725e21355',
  ]),
  'code-review-standards': new Set([
    '9c906f2b2a88c2d0aaeec9714405945da5177de6ec433f1acf520c6c4385b875',
    '3bc8587a9143487328be2470dec8df17a19cb14f94e6ec916ed58de660d0e1c4',
    '56abe5736f505c53ca9ce14087a9891cc8661be783abaec7b5b924e3f339cc2a',
    '586dde5014f9ac2f9a13d43fa1c8c257a3ae998a3fc1b867b23b3b2e44f77eca',
  ]),
  'root-cause-analysis': new Set([
    'e200ddd04196435af3162a9e13595f8eb5ac68b06465026e0155e453b1bd1c93',
    '1793dcb0f72621c78cc20c905fe5dd7a0af3115e904bf737a6a983a7b9d2c2b6',
    'aab22d1bddc66c6a798f08cdf7be9b45fbe80ccfc928b068ef5d9e2ad951bdda',
    '0eac104bfcde8bdf14d4c284be6f3f4cb243219a679bf569433c2465df84c6c3',
    'e66d15a9585c07e819acfd89c1f6d030517130f6d8f8924bda3120307949fb2e',
  ]),
  'ui-implementation-standards': new Set([
    'e2473e35474e78f2b581e225cb33a1e711bb79519a02e9780fc9606e582b878f',
    '1ff64816454171b3f879e9e5cf3c15e3d9c5f2ffc81b73262155f6bc93a1b054',
    '13c709c0e2b01ae94997c271043a685200e969192d2056534bd787c5682874e8',
  ]),
};

// Whether `dir` is a real folder whose only file (dotfiles such as .DS_Store aside) is a SKILL.md
// with an LF-normalized SHA-256 in `hashes`: an unedited copy devlyn-cli shipped, not something
// the user added to or wrote.
function isShippedCopy(dir, hashes) {
  const skill = path.join(dir, 'SKILL.md');
  return fs.lstatSync(dir, { throwIfNoEntry: false })?.isDirectory() === true
    && fs.readdirSync(dir).filter((name) => !name.startsWith('.')).length === 1
    && fs.lstatSync(skill, { throwIfNoEntry: false })?.isFile() === true
    && hashes.has(crypto.createHash('sha256')
      .update(fs.readFileSync(skill, 'utf8').replace(/\r\n/g, '\n')).digest('hex'));
}

// Skill roots of each target. In a project, `.agents/skills` serves Codex, omp, Pi and Grok,
// and Claude Code loads only `.claude/skills`. Globally Codex reads ~/.codex/skills and omp,
// Pi and Grok read ~/.agents/skills.
function skillRoots(target, global) {
  const dirs = target === 'claude' ? ['.claude'] : global ? ['.agents', '.codex'] : ['.agents'];
  return dirs.map((dir) => path.join(global ? os.homedir() : projectDir(), dir, 'skills'));
}

// A devlyn Claude install in this scope. Globally only the marker a `--global --claude` run
// writes counts; in a project also a devlyn skill (0.6.0 and later), command (0.2-0.5) or
// CLAUDE.md with devlyn defaults, which a team may commit while ignoring .claude/. An optional
// devlyn skill is not one: 4.0.1 put those into .claude/skills without the Claude target. A
// CLAUDE.md link (often to AGENTS.md) is not the Claude target's file: updateInstructions
// refuses links.
function hasDevlynClaude(global) {
  const claudeDir = path.dirname(skillRoots('claude', global)[0]);
  if (global) return fs.existsSync(path.join(claudeDir, 'skills', DEVLYN_INSTALL_MARKER));
  const names = (dir) => (fs.existsSync(dir) ? fs.readdirSync(dir) : []);
  const optional = new Set(OPTIONAL_ADDONS.map((addon) => addon.name));
  const instructions = path.join(path.dirname(claudeDir), 'CLAUDE.md');
  return names(path.join(claudeDir, 'skills')).some((name) => name === DEVLYN_INSTALL_MARKER
      || (name.startsWith('devlyn') && !optional.has(name.replace(/[:\uF03A]/g, '-'))))
    || names(path.join(claudeDir, 'commands')).some((name) => name.startsWith('devlyn.'))
    || (fs.lstatSync(instructions, { throwIfNoEntry: false })?.isFile() === true
      && holdsDevlynDefaults('CLAUDE.md', fs.readFileSync(instructions, 'utf8')));
}

// Commands removed in previous versions; the project Claude install deletes them from .claude/.
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
// even though the source dirs no longer exist (the installer replaces only
// the skills it ships — without this list, deleted-from-source skills persist
// in user installs forever).
const DEPRECATED_DIRS = [
  // v0.7.x rename: devlyn-* → devlyn:*
  'skills/devlyn-clean',
  'skills/devlyn-design-system',
  'skills/devlyn-discover-product',
  'skills/devlyn-evaluate',
  'skills/devlyn-feature-spec',
  'skills/devlyn-implement-ui',
  'skills/devlyn-product-spec',
  'skills/devlyn-recommend-features',
  'skills/devlyn-review',
  'skills/devlyn-team-design-ui',
  'skills/devlyn-team-resolve',
  'skills/devlyn-team-review',
  'skills/devlyn-update-docs',
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
  // Deleted entirely on 2026-05-14 (devlyn:team-design-ui merged into
  // devlyn:design-ui; devlyn:design-system removed outright). Entries kept
  // so users who previously opted in get their stale copies purged on upgrade.
  'skills/devlyn:team-design-ui',
  'skills/devlyn:design-system',
];

function projectDir() {
  try {
    return process.cwd();
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

${COLORS.dim}            AI Agent Config Toolkit${r}
${g}                v${PKG.version} ${COLORS.dim}· ${k}🍩 by Nocodecat @ Donut Studio${r}
`;
  console.log(logo);
}

const OPTIONAL_ADDONS = [
  // Local optional skills (copied into every selected skill root)
  { name: 'asset-creator', desc: 'AI pixel art game asset pipeline — generate, chroma-key, catalog', type: 'local' },
  { name: 'cloudflare-nextjs-setup', desc: 'Cloudflare Workers + Next.js deployment with OpenNext', type: 'local' },
  { name: 'generate-skill', desc: 'Create well-structured Claude Code skills following Anthropic best practices', type: 'local' },
  { name: 'prompt-engineering', desc: 'Claude prompt optimization using Anthropic best practices', type: 'local' },
  { name: 'better-auth-setup', desc: 'Production-ready Better Auth + Hono + Drizzle + PostgreSQL auth setup', type: 'local' },
  { name: 'polar-billing-setup', desc: 'Polar usage-based / metered billing — correct setup + diagnose silent $0-billing failures', type: 'local' },
  { name: 'pyx-scan', desc: 'Check whether an AI agent skill is safe before installing', type: 'local' },
  { name: 'dokkit', desc: 'Document template filling for DOCX/HWPX — ingest, fill, review, export', type: 'local' },
  { name: 'devlyn-pencil-pull', desc: 'Pull Pencil designs into code with exact visual fidelity', type: 'local' },
  { name: 'devlyn-pencil-push', desc: 'Push codebase UI to Pencil canvas for design sync', type: 'local' },
  { name: 'devlyn-reap', desc: 'Safely reap orphaned MCP / codex / Superset child processes left behind by long Claude sessions', type: 'local' },
  { name: 'code-health-standards', desc: 'Maintainability standards — dead code, dependencies, complexity, naming, hygiene', type: 'local' },
  { name: 'code-review-standards', desc: 'Severity framework and approval criteria for reviewing a change', type: 'local' },
  { name: 'root-cause-analysis', desc: 'Evidence-first why-chain debugging to the actionable root cause', type: 'local' },
  { name: 'ui-implementation-standards', desc: 'UI quality bar — design tokens, WCAG 2.1 AA, state coverage, responsive layout', type: 'local' },
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
  { name: 'playwright', desc: 'Playwright MCP for browser testing — powers /devlyn-resolve BUILD_GATE browser tier', type: 'mcp', command: 'npx -y @playwright/mcp@latest' },
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

// Old and retired skills in one skill root; nothing outside it.
function cleanupDeprecated(skillsDir) {
  let removed = 0;
  const deprecated = DEPRECATED_DIRS.flatMap((relPath) =>
    legacySkillPaths(skillsDir, path.basename(relPath)).map((fullPath) => [relPath, fullPath]));
  for (const [relPath, fullPath] of deprecated) {
    if (fs.existsSync(fullPath)) {
      fs.rmSync(fullPath, { recursive: true });
      log(`  ✕ ${relPath}/ (removed)`, 'dim');
      removed++;
    }
  }
  for (const [name, hashes] of Object.entries(RETIRED_SKILL_MD_SHA256)) {
    const fullPath = path.join(skillsDir, name);
    if (isShippedCopy(fullPath, hashes)) {
      fs.rmSync(fullPath, { recursive: true });
      log(`  ✕ skills/${name}/ (removed)`, 'dim');
      removed++;
    }
  }
  return removed;
}

// Remove every old spelling of the renamed skills in `skillsDir`, after the new core skills
// are in place. An optional skill found under an old spelling is installed under its new name
// before the old copy goes, so an interrupted migration never loses it. An unedited 0.6.0-0.7.1
// copy is refreshed in place. Any other folder under a 4.0 name is the user's own; `-y` leaves it.
function retireRenamedSkills(skillsDir) {
  const optional = new Set(OPTIONAL_ADDONS.filter((addon) => addon.type === 'local').map((addon) => addon.name));
  for (const [oldName, newName] of Object.entries(RENAMED_SKILLS)) {
    const found = legacySkillPaths(skillsDir, oldName).filter((fullPath) => fs.existsSync(fullPath));
    if (found.length > 0 && optional.has(newName)) installOptionalSkillInto(skillsDir, newName);
    else if (isShippedCopy(path.join(skillsDir, newName), PRE_STANDARD_SKILL_MD_SHA256)) refreshPreStandardCopy(skillsDir, newName);
    for (const fullPath of found) {
      fs.rmSync(fullPath, { recursive: true, force: true });
      log(`  ✕ ${path.basename(fullPath)}/ (renamed to ${newName})`, 'dim');
    }
  }
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

function clearInstallMarker(skillsDir) {
  fs.rmSync(path.join(skillsDir, DEVLYN_INSTALL_MARKER), { force: true });
}

function assertCompleteSkillInstall(sourceSkillsDir, skillsDir, skillNames) {
  function complete(src, dest) {
    if (!fs.existsSync(src) || !fs.existsSync(dest)) return false;
    if (fs.statSync(src).isDirectory()) {
      return fs.statSync(dest).isDirectory() && fs.readdirSync(src).every((name) =>
        complete(path.join(src, name), path.join(dest, name)));
    }
    return fs.statSync(dest).isFile();
  }
  const missing = skillNames.filter((name) => {
    const src = path.join(sourceSkillsDir, name);
    const dest = path.join(skillsDir, name);
    return !complete(src, dest) || (name !== '_shared' && !fs.existsSync(path.join(src, 'SKILL.md')));
  });
  if (missing.length > 0) {
    throw new Error(`Incomplete devlyn skill install; missing: ${missing.join(', ')}`);
  }
}

function writeInstallMarker(skillsDir) {
  const markerPath = path.join(skillsDir, DEVLYN_INSTALL_MARKER);
  const tempPath = `${markerPath}.${process.pid}.tmp`;
  const marker = {
    schemaVersion: 1,
    package: PKG.name,
    version: PKG.version,
  };
  try {
    fs.writeFileSync(tempPath, JSON.stringify(marker, null, 2) + '\n', {
      encoding: 'utf8',
      flag: 'wx',
      mode: 0o600,
    });
    fs.renameSync(tempPath, markerPath);
  } finally {
    fs.rmSync(tempPath, { force: true });
  }
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
        const tagLabel = item.type === 'mcp' ? 'mcp' : item.type === 'local' ? 'skill' : 'pack';
        const tagColor = item.type === 'mcp' ? COLORS.green : item.type === 'local' ? COLORS.magenta : COLORS.cyan;
        const tag = `${tagColor}${tagLabel}${COLORS.reset}`;
        console.log(`${pointer} ${checkbox} ${name}${item.type ? ` ${COLORS.dim}[${tag}${COLORS.dim}]${COLORS.reset}` : ''}`);
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

// One of `items` (↑↓ move, Enter confirms); resolves to the chosen index.
function singleSelect(items, initial) {
  return new Promise((resolve) => {
    let cursor = initial;
    let drawn = false;
    const render = () => {
      if (drawn) process.stdout.write(`\x1b[${items.length + 2}A\x1b[0J`);
      drawn = true;
      console.log(`${COLORS.dim}(↑↓ navigate, enter confirm)${COLORS.reset}\n`);
      items.forEach((item, i) => console.log(i === cursor ? `${COLORS.cyan}❯ ${item}${COLORS.reset}` : `  ${item}`));
    };
    render();
    process.stdin.setRawMode(true);
    process.stdin.resume();
    process.stdin.setEncoding('utf8');
    const onKeypress = (key) => {
      if (key === '\u0003') {
        process.stdin.setRawMode(false);
        process.exit();
      }
      if (key === '\r' || key === '\n') {
        process.stdin.setRawMode(false);
        process.stdin.removeListener('data', onKeypress);
        process.stdin.pause();
        console.log('');
        resolve(cursor);
      } else if (['\x1b[A', 'k', '\x1b[B', 'j'].includes(key)) {
        cursor = (cursor + (key === '\x1b[A' || key === 'k' ? items.length - 1 : 1)) % items.length;
        render();
      }
    };
    process.stdin.on('data', onKeypress);
  });
}

function installLocalSkill(skillName, roots) {
  if (!fs.existsSync(path.join(OPTIONAL_SKILLS_SOURCE, skillName))) {
    log(`   ⚠️  Skill "${skillName}" not found`, 'yellow');
    return false;
  }
  log(`\n🛠️  Installing ${skillName}...`, 'cyan');
  for (const root of roots) installOptionalSkillInto(root, skillName);
  return true;
}

// One optional skill into one skill-loader directory, replacing any older copy of it. A
// copy under its name before the 4.0.0 rename goes only once the new one is complete.
function installOptionalSkillInto(target, skillName) {
  const dest = path.join(target, skillName);
  fs.rmSync(dest, { recursive: true, force: true });
  copyRecursive(path.join(OPTIONAL_SKILLS_SOURCE, skillName), dest, target);
  assertCompleteSkillInstall(OPTIONAL_SKILLS_SOURCE, target, [skillName]);
  const oldName = Object.keys(RENAMED_SKILLS).find((name) => RENAMED_SKILLS[name] === skillName);
  for (const fullPath of oldName ? legacySkillPaths(target, oldName) : []) {
    fs.rmSync(fullPath, { recursive: true, force: true });
  }
}

// A 0.6.0-0.7.1 copy is one SKILL.md, the file that identifies it. Renaming the new one over it is
// atomic, so an interrupted run leaves the old copy, which the retry finds again, or the new.
function refreshPreStandardCopy(target, skillName) {
  const skill = path.join(target, skillName, 'SKILL.md');
  const staged = `${skill}.${process.pid}.tmp`;
  try {
    fs.copyFileSync(path.join(OPTIONAL_SKILLS_SOURCE, skillName, 'SKILL.md'), staged);
    fs.renameSync(staged, skill);
  } finally {
    fs.rmSync(staged, { force: true });
  }
  assertCompleteSkillInstall(OPTIONAL_SKILLS_SOURCE, target, [skillName]);
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

function installAddon(addon, roots) {
  if (addon.type === 'local') {
    return installLocalSkill(addon.name, roots);
  }
  if (addon.type === 'mcp') {
    return installMcpServer(addon.name, addon.command);
  }
  return installSkillPack(addon.name);
}

// The core skills into one skill root, replacing older copies and retired skills, then the
// marker that records a complete install.
function installCoreSkills(skillsDir) {
  const sourceSkillsDir = path.join(CONFIG_SOURCE, 'skills');
  log(`\n📁 Installing devlyn skills to ${skillsDir.replace(os.homedir(), '~')}`, 'green');
  fs.mkdirSync(skillsDir, { recursive: true });
  clearInstallMarker(skillsDir);
  const removed = cleanupDeprecated(skillsDir);
  if (removed > 0) {
    log(`\n🧹 Cleaned up ${removed} deprecated file${removed > 1 ? 's' : ''}`, 'yellow');
  }
  for (const skillName of DEVLYN_CORE_SKILLS) {
    const src = path.join(sourceSkillsDir, skillName);
    const dest = path.join(skillsDir, skillName);
    if (!fs.existsSync(src)) continue;
    // Full replace: copyRecursive is an overlay, so stale files would otherwise persist.
    fs.rmSync(dest, { recursive: true, force: true });
    copyRecursive(src, dest, skillsDir);
  }
  assertCompleteSkillInstall(sourceSkillsDir, skillsDir, DEVLYN_CORE_SKILLS);
  retireRenamedSkills(skillsDir);
  writeInstallMarker(skillsDir);
}

// Keep installer-managed pipeline state and install metadata out of git.
function ignoreInGit(gitignoreEntries) {
  const gitignorePath = path.join(projectDir(), '.gitignore');
  let gitignoreContent = fs.existsSync(gitignorePath)
    ? fs.readFileSync(gitignorePath, 'utf8')
    : '';
  const gitignoreLines = gitignoreContent.split('\n').map((line) => line.trim());
  const missingGitignoreEntries = gitignoreEntries.filter((entry) =>
    !gitignoreLines.includes(entry) && !(entry === '.devlyn/' && gitignoreLines.includes('.devlyn')));
  if (missingGitignoreEntries.length > 0) {
    const prefix = gitignoreContent && !gitignoreContent.endsWith('\n') ? '\n' : '';
    const hasManagedHeader = gitignoreLines.includes('# devlyn-cli pipeline state');
    const header = hasManagedHeader ? '' : gitignoreContent ? '\n# devlyn-cli pipeline state\n' : '# devlyn-cli pipeline state\n';
    fs.writeFileSync(gitignorePath, gitignoreContent + prefix + header + missingGitignoreEntries.join('\n') + '\n');
    log(`  → .gitignore (added ${missingGitignoreEntries.join(', ')})`, 'dim');
  }
}

// With the Claude target in the same run, an AGENTS.md that links to this project's CLAUDE.md (a
// common Claude-first setup) gets its devlyn block through CLAUDE.md. Any other link is refused.
// AGENTS.md that is this project's CLAUDE.md under another name: a symlink to it, or the plain
// file Git for Windows checks out in a symlink's place when core.symlinks is off (its whole
// content is the link target). Compared by real path: a link to another hard link of CLAUDE.md
// would go stale once CLAUDE.md is replaced.
function agentsMdIsClaudeMd() {
  const agents = path.join(projectDir(), 'AGENTS.md');
  const claude = path.join(projectDir(), 'CLAUDE.md');
  const stat = fs.lstatSync(agents, { throwIfNoEntry: false });
  if (!stat || !fs.lstatSync(claude, { throwIfNoEntry: false })?.isFile()) return false;
  const target = stat.isSymbolicLink() ? agents
    : stat.isFile() && stat.size < 256 ? path.resolve(projectDir(), fs.readFileSync(agents, 'utf8'))
      : null;
  return target !== null && fs.existsSync(target) && fs.realpathSync.native(target) === fs.realpathSync.native(claude);
}

function installAgentsProject(withClaude) {
  if (!agentsMdIsClaudeMd()) {
    updateInstructions('AGENTS.md');
  } else if (withClaude) {
    log('  → AGENTS.md is CLAUDE.md here, so it gets the devlyn block written there', 'dim');
  } else {
    throw new InstructionError('AGENTS.md is CLAUDE.md under another name here. Choose CLAUDE.md as well '
      + '(npx devlyn-cli -y --claude) so the devlyn block is written once, into CLAUDE.md.');
  }
  installCoreSkills(skillRoots('agents', false)[0]);
  ignoreInGit(['.devlyn/', '.agents/skills/.devlyn-install.json']);
}

// Project CLAUDE.md and .claude/: skills, templates, commit conventions and settings.
function installClaudeCore() {
  updateInstructions('CLAUDE.md');
  const skillsDir = skillRoots('claude', false)[0];
  const targetDir = path.dirname(skillsDir);
  for (const entry of fs.readdirSync(CONFIG_SOURCE)) {
    if (entry !== 'skills') copyRecursive(path.join(CONFIG_SOURCE, entry), path.join(targetDir, entry), targetDir);
  }
  for (const relPath of DEPRECATED_FILES) {
    const fullPath = path.join(targetDir, relPath);
    if (fs.existsSync(fullPath)) {
      fs.unlinkSync(fullPath);
      log(`  ✕ ${relPath} (deprecated)`, 'dim');
    }
  }
  installCoreSkills(skillsDir);
  ignoreInGit(['.devlyn/', '.claude/skills/.devlyn-install.json']);

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
  if (!settings.env.ENABLE_PROMPT_CACHING_1H) {
    settings.env.ENABLE_PROMPT_CACHING_1H = 'true';
    settingsChanged = true;
  }
  if (!settings.env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS) {
    settings.env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS = '1';
    settingsChanged = true;
  }
  const bashMaxTimeoutMs = Number.parseInt(settings.env.BASH_MAX_TIMEOUT_MS, 10);
  if (!Number.isFinite(bashMaxTimeoutMs) || bashMaxTimeoutMs < 3600000) {
    settings.env.BASH_MAX_TIMEOUT_MS = '3600000';
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
    log('  → settings.json (agent teams + one-hour Bash max + 1h prompt caching + pipeline permissions + Stop hook)', 'dim');
  }
}

// Installs the targets in one scope; returns the skill roots written.
function install(targets, global) {
  // In the home folder CLAUDE.md, AGENTS.md (agents read a parent folder's too) and
  // .claude/settings.json (permissions, Stop hook) would apply to every project. Same folder by
  // identity, so a link or another spelling of the path is caught too.
  const home = fs.statSync(os.homedir(), { bigint: true, throwIfNoEntry: false });
  const here = fs.statSync(projectDir(), { bigint: true });
  if (!global && home?.dev === here.dev && home?.ino === here.ino) {
    throw new InstructionError('This project is your home folder, so its CLAUDE.md, AGENTS.md and .claude/settings.json '
      + 'would apply to every project. Run from a project folder, or use --global for skills only.');
  }
  const roots = targets.flatMap((target) => skillRoots(target, global));
  for (const target of targets) {
    if (global) skillRoots(target, true).forEach((root) => installCoreSkills(root));
    else if (target === 'agents') installAgentsProject(targets.includes('claude'));
    else installClaudeCore();
  }
  log(`\n✅ devlyn ${PKG.version} installed`, 'green');
  // Global installs never edit user settings, but /devlyn-resolve needs long foreground Bash calls.
  if (global && targets.includes('claude')) {
    log('Claude Code: unless your settings already allow it, add "env": {"BASH_MAX_TIMEOUT_MS": "3600000"} '
      + 'to ~/.claude/settings.json and restart; /devlyn-resolve runs foreground commands longer than the default limit.', 'yellow');
  }
  noticeGlobalDrift(roots);
  return roots;
}

// A devlyn install in a user root this run does not refresh drifts and can shadow the
// project's copy; name it without touching it.
function noticeGlobalDrift(installed) {
  for (const dir of ['.agents', '.codex', '.claude', '.grok']) {
    const root = path.join(os.homedir(), dir, 'skills');
    const marker = path.join(root, DEVLYN_INSTALL_MARKER);
    if (installed.includes(root) || !fs.existsSync(marker)) continue;
    let version;
    try {
      version = JSON.parse(fs.readFileSync(marker, 'utf8')).version;
    } catch (error) {
      version = `(unreadable marker: ${error.message})`;
    }
    // 4.0's Grok root; Grok now reads ~/.agents/skills, so --global never refreshes it.
    const advice = dir === '.grok' ? 'delete it' : 'refresh it with --global, or delete it';
    log(`Global devlyn ${version} in ${root.replace(os.homedir(), '~')} — ${advice}.`, 'yellow');
  }
}

async function init({ yes, claude, global }) {
  showLogo();
  log('─'.repeat(44), 'dim');

  if (!fs.existsSync(CONFIG_SOURCE)) {
    log('❌ Config source not found', 'yellow');
    process.exit(1);
  }

  // Without prompts: AGENTS plus every target already installed in the chosen scope.
  if (yes || !process.stdin.isTTY) {
    const targets = ['agents', ...(claude || hasDevlynClaude(global) ? ['claude'] : [])];
    install(targets, global);
    log('\n💡 Add optional addons later: run `npx devlyn-cli` without -y', 'dim');
    const hints = [
      ...(targets.includes('claude') ? [] : [`${global ? '~/.claude/skills' : 'CLAUDE.md + .claude/'} for Claude Code: add --claude`]),
      ...(global ? [] : ['every project on this machine: add --global']),
    ];
    if (hints.length > 0) log(`   ${hints.join(' · ')}`, 'dim');
    log(`\n${COLORS.dim}   Enjoying devlyn? Star it on GitHub — it helps others find it:${COLORS.reset}`);
    log(`   ${COLORS.purple}→ https://github.com/fysoul17/devlyn-cli${COLORS.reset}\n`);
    return;
  }

  log('\n🎯 What to install:\n', 'blue');
  const targetOptions = [
    { key: 'agents', name: 'AGENTS.md — Codex · omp · Pi · Grok', desc: 'AGENTS.md + .agents/skills' },
    { key: 'claude', name: 'CLAUDE.md — Claude Code', desc: 'CLAUDE.md + .claude/ (skills, templates, settings)' },
  ];
  const preselected = claude || hasDevlynClaude(false) || (global && hasDevlynClaude(true)) ? [0, 1] : [0];
  const targets = (await multiSelect(targetOptions, preselected)).map((option) => option.key);

  if (targets.length === 0) {
    log('\n💡 Nothing selected — nothing installed.', 'yellow');
    log('   Run `npx devlyn-cli` again and pick at least one.\n', 'dim');
    return;
  }

  log('📍 Where:\n', 'blue');
  const scope = await singleSelect(['This project', 'Global — every project on this machine'], global ? 1 : 0);
  const roots = install(targets, scope === 1);

  // Ask about optional addons (local skills + external packs; MCP servers belong to Claude Code)
  log('\n📚 Optional skills & packs:\n', 'blue');

  const selectedAddons = await multiSelect(OPTIONAL_ADDONS.filter((addon) => addon.type !== 'mcp' || targets.includes('claude')));

  if (selectedAddons.length > 0) {
    for (const addon of selectedAddons) {
      installAddon(addon, roots);
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
  log('  npx devlyn-cli               Install/update devlyn: choose what (AGENTS.md, CLAUDE.md) and where (this project or global)');
  log('  npx devlyn-cli -y            Without prompts: AGENTS.md + .agents/skills, plus CLAUDE.md + .claude/ if this project has them');
  log('  npx devlyn-cli -y --claude   Also install CLAUDE.md + .claude/ for Claude Code');
  log('  npx devlyn-cli -y --global   Skills only, for every project on this machine (~/.agents/skills, ~/.codex/skills; ~/.claude/skills with --claude, or when it already has a devlyn install)');
  log('  npx devlyn-cli list          List available skills & templates');
  log('  npx devlyn-cli --help        Show this help\n');
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
  log('');
}

// Main
const args = process.argv.slice(2);

const INSTALL_FLAGS = ['-y', '--yes', '--claude', '--global'];

async function main() {
const command = args[0];

switch (command) {
  case '--help':
  case '-h':
    showHelp();
    break;
  case 'list':
  case 'ls':
    listContents();
    break;
  case 'agents':
    console.error('`npx devlyn-cli agents` was removed in 4.1.0. Run `npx devlyn-cli` to choose what and where,');
    console.error('or `npx devlyn-cli -y [--claude] [--global]` without prompts.');
    process.exitCode = 1;
    break;
  default: {
    const flags = command === 'init' ? args.slice(1) : args;
    const unknown = flags.find((flag) => !INSTALL_FLAGS.includes(flag));
    if (unknown !== undefined) {
      log(`Unknown command: ${unknown}`, 'yellow');
      showHelp();
      process.exit(1);
    }
    await init({ yes: flags.includes('-y') || flags.includes('--yes'), claude: flags.includes('--claude'), global: flags.includes('--global') });
  }
}
}

main().catch((error) => {
  console.error(error instanceof InstructionError ? `\n${error.message}` : error);
  process.exitCode = 1;
});
