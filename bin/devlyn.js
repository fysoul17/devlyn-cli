#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const os = require('os');
const crypto = require('crypto');
const { execSync, spawnSync } = require('child_process');

const CONFIG_SOURCE = path.join(__dirname, '..', 'config');
const OPTIONAL_SKILLS_SOURCE = path.join(__dirname, '..', 'optional-skills');
const PKG = require('../package.json');
const { updateInstructions, InstructionError, holdsDevlynDefaults, importsAgentsMd } = require('./instructions');
const { contentHash, fingerprint, gitEnvironment, isIgnoredEntry, trackedPaths } = require('./skill-ownership');
const SKILL_HISTORY = require('./skill-history.json');
const CLEANUP_HISTORY = require('./cleanup-history.json');

// The devlyn skill bundle installed into every skill-capable agent's loader
// directory. Single source of truth so codex/omp/pi stay in lockstep — adding a
// skill here installs it everywhere.
const DEVLYN_CORE_SKILLS = ['devlyn-ideate', 'devlyn-engines', '_shared'];
// 4.0.0 renamed the colon-named skills to the Agent Skills standard (`[a-z0-9-]`, name ==
// folder): Git for Windows cannot check out a folder with ':' in its name. Installs from 3.x
// and earlier keep the old folder under either spelling (':' or npm's U+F03A extraction
// alias). Both are removed, and an optional skill that was installed is installed again
// under its new name in the same place.
const RENAMED_SKILLS = {
  'devlyn:ideate': 'devlyn-ideate',
  'devlyn:engines': 'devlyn-engines',
  'devlyn:pencil-pull': 'devlyn-pencil-pull',
  'devlyn:pencil-push': 'devlyn-pencil-push',
  'devlyn:reap': 'devlyn-reap',
};
const DEVLYN_INSTALL_MARKER = '.devlyn-install.json';
const DEVLYN_INSTALL_LOCK = '.devlyn-install.lock';
// Project settings earlier releases added for the retired pipeline.
const RETIRED_STOP_HOOK = 'python3 "$CLAUDE_PROJECT_DIR/.claude/skills/_shared/resolve-stop-hook.py"';
const RETIRED_ENV = ['CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS'];
const RETIRED_PERMISSIONS = ['Write(.devlyn/**)', 'Edit(.devlyn/**)', 'Bash(git add *)', 'Bash(git commit *)',
  'Bash(git diff *)', 'Bash(git status *)', 'Bash(git log *)'];

// Every spelling a colon name can have on disk: its own and npm's U+F03A extraction alias.
function legacySkillPaths(root, name) {
  const spellings = new Set([name, name.replace(/:/g, '\uF03A')]);
  if (fs.lstatSync(root, { throwIfNoEntry: false })?.isDirectory()) {
    for (const entry of fs.readdirSync(root)) {
      if ([...spellings].some((spelling) => spelling.toLowerCase() === entry.toLowerCase())) spellings.add(entry);
    }
  }
  return [...spellings].map((spelling) => path.join(root, spelling));
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
const RETIRED_SKILL_MD_SHA256 = Object.fromEntries(
  Object.entries(CLEANUP_HISTORY.skills).map(([name, hashes]) => [name, new Set(hashes)]));

// Whether `dir` is a real folder whose only file, besides generated metadata, is a SKILL.md
// with an LF-normalized SHA-256 in `hashes`: an unedited copy devlyn-cli shipped, not something
// the user added to or wrote.
function isShippedCopy(dir, hashes) {
  const skill = path.join(dir, 'SKILL.md');
  return fs.lstatSync(dir, { throwIfNoEntry: false })?.isDirectory() === true
    && fs.readdirSync(dir).filter((name) => !isIgnoredEntry(path.join(dir, name))).length === 1
    && fs.lstatSync(skill, { throwIfNoEntry: false })?.isFile() === true
    && hashes.has(crypto.createHash('sha256').update(fs.readFileSync(skill).toString('latin1').replace(/\r\n/g, '\n'), 'latin1').digest('hex'));
}

// Skill roots of each target. In a project, `.agents/skills` serves Codex, omp, Pi and Grok,
// and Claude Code loads only `.claude/skills`. Globally Codex reads ~/.codex/skills and omp,
// Pi and Grok read ~/.agents/skills.
function skillRoots(target, global) {
  const dirs = target === 'claude' ? ['.claude'] : global ? ['.agents', '.codex'] : ['.agents'];
  return dirs.map((dir) => path.join(global ? os.homedir() : projectDir(), dir, 'skills'));
}

// Core and historical skills count, as does an install in progress. _shared is not
// unique to devlyn, and a marker alone can outlive its skills; optional addons stand alone.
function hasDevlynInstall(root) {
  try {
    const stat = (name) => fs.lstatSync(name, { throwIfNoEntry: false });
    if (!stat(root)?.isDirectory()) return false;
    const optional = new Set(OPTIONAL_ADDONS.map((addon) => addon.name));
    const names = [...DEVLYN_CORE_SKILLS,
      ...Object.keys(RENAMED_SKILLS)].filter((name) => name.startsWith('devlyn')
        && !optional.has(name.replace(/[:\uF03A]/g, '-')));
    return !!stat(path.join(root, DEVLYN_INSTALL_LOCK))
      || names.some((name) => [...legacySkillPaths(root, name.replace(/^devlyn-/, 'devlyn:')),
        path.join(root, name.replace(/:/g, '-'))].some((full) => stat(full)?.isDirectory()))
      || hasHistoricalRetiredSkill(root)
      || (!!stat(path.join(root, DEVLYN_INSTALL_MARKER)) && stat(path.join(root, '_shared'))?.isDirectory());
  } catch (error) {
    if (error.code === 'ENOTDIR') return false;
    throw new InstructionError(`Cannot inspect ${root}: ${error.message}. Check its permissions and run again.`);
  }
}

// A devlyn Claude install in this scope. Globally only the marker a `--global --claude` run
// writes counts; in a project also a devlyn skill (0.6.0 and later), command (0.2-0.5) or
// CLAUDE.md with devlyn defaults, held or imported from AGENTS.md, which a team may commit
// while ignoring .claude/. An optional devlyn skill is not one: 4.0.1 put those into
// .claude/skills without the Claude target. A CLAUDE.md link (often to AGENTS.md) is not the
// Claude target's file: updateInstructions refuses links.
function hasDevlynClaude(global) {
  const claudeDir = path.dirname(skillRoots('claude', global)[0]);
  if (global) return fs.existsSync(path.join(claudeDir, 'skills', DEVLYN_INSTALL_MARKER));
  const names = (dir) => (fs.existsSync(dir) ? fs.readdirSync(dir) : []);
  const optional = new Set(OPTIONAL_ADDONS.map((addon) => addon.name));
  const instructions = path.join(path.dirname(claudeDir), 'CLAUDE.md');
  const claude = fs.lstatSync(instructions, { throwIfNoEntry: false })?.isFile() ? fs.readFileSync(instructions, 'utf8') : '';
  const root = path.join(claudeDir, 'skills');
  const deprecated = new Set([...deprecatedSkillPaths(root)].map((full) => path.basename(full).toLowerCase()));
  return names(root).some((name) => {
    if (deprecated.has(name.toLowerCase())) return historicalSkill(path.join(root, name));
    return name === DEVLYN_INSTALL_MARKER
      || (name.startsWith('devlyn') && !optional.has(name.replace(/[:\uF03A]/g, '-')));
  })
    || names(path.join(claudeDir, 'commands')).some((name) => name.startsWith('devlyn.'))
    || holdsDevlynDefaults('CLAUDE.md', claude) || importsAgentsDefaults(claude);
}

// Exact Devlyn command names removed by previous versions, in either scope.
const DEPRECATED_FILES = [
  'commands/devlyn.ui.md',
  'commands/devlyn.team-ui.md',
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
// remove these exact retired skill names from downstream skill roots
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
  // Retired after 4.1.0 (design-ui deleted; the intent queue moved into
  // devlyn-ideate; resolve retired). All were core skills, so their 3.x and
  // 4.x folders go.
  'skills/devlyn-design-ui',
  'skills/devlyn:design-ui',
  'skills/devlyn-queue',
  'skills/devlyn:queue',
  'skills/devlyn-resolve',
  'skills/devlyn:resolve',
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
  { name: 'playwright', desc: 'Playwright MCP for browser testing', type: 'mcp', command: 'npx -y @playwright/mcp@latest' },
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

  const skillsDir = path.join(CONFIG_SOURCE, 'skills');

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

// Remove every old spelling of the renamed skills in `skillsDir`, after the new core skills
// are in place. An optional skill found under an old spelling is installed under its new name
// before the old copy goes, so an interrupted migration never loses it. An unedited 0.6.0-0.7.1
// copy is refreshed in place. Any other folder under a 4.0 name is the user's own; `-y` leaves it.
function refreshRenamedSkills(skillsDir, installedSkills) {
  const optional = new Set(OPTIONAL_ADDONS.filter((addon) => addon.type === 'local').map((addon) => addon.name));
  const refreshed = [];
  for (const [oldName, newName] of Object.entries(RENAMED_SKILLS)) {
    const found = legacySkillPaths(skillsDir, oldName).filter((fullPath) => fs.existsSync(fullPath));
    if (found.length > 0 && optional.has(newName) && canRefreshRenamed(skillsDir, newName)) {
      installOptionalSkillInto(skillsDir, newName, installedSkills);
      refreshed.push(newName);
    } else if (isShippedCopy(path.join(skillsDir, newName), PRE_STANDARD_SKILL_MD_SHA256)) {
      refreshPreStandardCopy(skillsDir, newName);
      installedSkills.set(path.join(skillsDir, newName), [path.join(skillsDir, newName, 'SKILL.md')]);
      refreshed.push(newName);
    }
  }
  return refreshed;
}

function copyRecursive(src, dest, baseDir, files = []) {
  const stats = fs.statSync(src);

  if (stats.isDirectory()) {
    if (!fs.existsSync(dest)) {
      fs.mkdirSync(dest, { recursive: true });
    }

    for (const item of fs.readdirSync(src)) {
      copyRecursive(path.join(src, item), path.join(dest, item), baseDir, files);
    }
  } else {
    const destDir = path.dirname(dest);
    if (!fs.existsSync(destDir)) {
      fs.mkdirSync(destDir, { recursive: true });
    }
    fs.copyFileSync(src, dest);
    files.push(dest);
    log(`  → ${path.relative(baseDir, dest)}`, 'dim');
  }
  return files;
}

function clearInstallMarker(skillsDir) {
  fs.rmSync(path.join(skillsDir, DEVLYN_INSTALL_MARKER), { force: true });
}

function readInstallManifest(root) {
  const markerPath = path.join(root, DEVLYN_INSTALL_MARKER);
  const stat = fs.lstatSync(markerPath, { throwIfNoEntry: false });
  if (!stat) return {};
  if (!stat.isFile()) throw new Error(`not a regular install marker: ${markerPath}`);
  const marker = JSON.parse(fs.readFileSync(markerPath, 'utf8'));
  if (marker?.package !== PKG.name || marker.schemaVersion !== 1) {
    throw new Error('not a devlyn-cli install marker');
  }
  return marker.skills || {};
}

// A retired optional name must not make a foreign copy under its new name an install conflict.
function canRefreshRenamed(root, name) {
  const dest = path.join(root, name);
  if (!fs.lstatSync(dest, { throwIfNoEntry: false })) return true;
  try { verifySkill(dest, name, readInstallManifest(root)); return true; }
  catch { return false; } // No ownership proof: preserve the new-name entry without installing over it.
}

// Enumerate every directory this install may replace, migrate or remove, before
// touching any target. Optional addons must be selected before this preflight too.
function plannedSkills(root, optionalNames = []) {
  const names = new Set([...DEVLYN_CORE_SKILLS, ...optionalNames]);
  for (const [oldName, newName] of Object.entries(RENAMED_SKILLS)) {
    const oldPaths = legacySkillPaths(root, oldName);
    if ((oldPaths.some((full) => fs.lstatSync(full, { throwIfNoEntry: false })) && canRefreshRenamed(root, newName))
        || isShippedCopy(path.join(root, newName), PRE_STANDARD_SKILL_MD_SHA256)) names.add(newName);
  }
  return names;
}

function verifySkill(dest, name, manifest) {
  const actual = fingerprint(dest);
  const logicalName = name.replace(/[:\uF03A]/g, '-');
  const source = path.join(DEVLYN_CORE_SKILLS.includes(logicalName)
    ? path.join(CONFIG_SOURCE, 'skills') : OPTIONAL_SKILLS_SOURCE, logicalName);
  const current = fs.existsSync(source) && fingerprint(source) === actual;
  const historical = SKILL_HISTORY.skills[logicalName]?.includes(actual);
  const hashes = RETIRED_SKILL_MD_SHA256[name.toLowerCase()] || PRE_STANDARD_SKILL_MD_SHA256;
  const singleFile = isShippedCopy(dest, hashes);
  if (!current && !historical && !singleFile && manifest[name] !== actual) {
    throw new Error(manifest[name] ? 'modified contents (install manifest fingerprint mismatch)'
      : fs.existsSync(source) || SKILL_HISTORY.skills[logicalName]?.length
        ? 'fingerprint mismatch with known shipped copies'
        : 'unknown installer ownership (no fingerprint history for this copy)');
  }
}

// Discovery keeps its historical ownership boundary; cleanup below uses exact retired names.
function deprecatedSkillPaths(root) {
  return new Set(DEPRECATED_DIRS.flatMap((relative) => {
    const name = path.basename(relative);
    return [...legacySkillPaths(root, name.replace(/^devlyn-/, 'devlyn:')),
      path.join(root, name.replace(/:/g, '-'))];
  }));
}

function historicalSkill(dest) {
  try {
    return SKILL_HISTORY.skills[path.basename(dest).toLowerCase().replace(/[:\uF03A]/g, '-')]?.includes(fingerprint(dest)) === true;
  } catch {
    // A link, unreadable or partial tree is not evidence of an install to refresh.
    return false;
  }
}

function hasHistoricalRetiredSkill(root) {
  return [...deprecatedSkillPaths(root)].some(historicalSkill);
}

// Validate only paths this run installs; removal-only names never refuse an install.
function preflightSkills(roots, optionalNames = []) {
  const conflicts = [];
  for (const root of roots) {
    try {
      // Do not follow an agent-directory or skill-root link into another installation.
      for (const dir of [path.dirname(root), root]) {
        const stat = fs.lstatSync(dir, { throwIfNoEntry: false });
        if (stat && !stat.isDirectory()) throw new Error(`not a real directory: ${dir}`);
      }
      const tracked = trackedPaths(root);
      let manifest;
      try {
        manifest = readInstallManifest(root);
      } catch (error) {
        conflicts.push(`${path.join(root, DEVLYN_INSTALL_MARKER)}: ${error.message}`);
        continue;
      }
      for (const name of plannedSkills(root, optionalNames)) {
        const dest = path.join(root, name);
        const isTracked = tracked.some((file) => file.toLowerCase() === dest.toLowerCase()
          || file.toLowerCase().startsWith(dest.toLowerCase() + path.sep));
        try {
          if (!fs.lstatSync(dest, { throwIfNoEntry: false })) {
            if (isTracked) throw new Error('missing contents; cannot verify installer ownership');
            continue;
          }
          verifySkill(dest, name, manifest);
        } catch (error) {
          conflicts.push(`${dest}: ${isTracked ? 'git-tracked; ' : ''}${error.message}`);
        }
      }
    } catch (error) {
      conflicts.push(`${root}: ${error.message}`);
    }
  }
  if (conflicts.length) {
    throw new InstructionError('Installation refused; nothing was changed:\n'
      + conflicts.map((conflict) => `  - ${conflict}`).join('\n')
      + '\nMove these out of the install path, or back them up and remove them, then rerun.'
      + '\nFor tracked paths, also remove them from the Git index.'
      + '\nRerun the same command after resolving every conflict; -y does not bypass this check.');
  }
  return {};
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

function writeInstallMarker(skillsDir, names, previous) {
  const markerPath = path.join(skillsDir, DEVLYN_INSTALL_MARKER);
  const tempPath = `${markerPath}.${process.pid}.tmp`;
  const marker = {
    schemaVersion: 1,
    package: PKG.name,
    version: PKG.version,
    skills: { ...previous, ...Object.fromEntries(names.map((name) => [name, fingerprint(path.join(skillsDir, name))])) },
  };
  const fd = fs.openSync(tempPath, 'wx', 0o600);
  try {
    try {
      fs.writeFileSync(fd, JSON.stringify(marker, null, 2) + '\n', 'utf8');
    } finally {
      fs.closeSync(fd);
    }
    fs.renameSync(tempPath, markerPath);
  } finally {
    fs.rmSync(tempPath, { force: true });
  }
}

// One Inquirer menu, imported only when shown (Inquirer is ESM). The page gets the terminal
// rows left after everything else the menu draws, so a redraw never scrolls it into
// duplicates. Ctrl+C cancels the install.
async function ask(module, help, config) {
  const { default: prompt } = await import(module);
  const { stdin: input, stdout: output } = process;
  const columns = output.columns || 80;
  // Most rows a text wraps to: an ASCII character takes one cell, any other at most two.
  const rows = (text = '') => Math.ceil([...text].reduce((cells, c) => cells + (c.codePointAt(0) < 0x80 ? 1 : 2), 0) / columns);
  // Message, blank line, the active choice's description, key help, and the line Inquirer
  // adds when the help exactly fills the width.
  const reserved = rows(`? ${config.message}`) + 1 + Math.max(...config.choices.map((choice) => rows(choice.description))) + rows(help) + 1;
  try {
    return await prompt({
      ...config,
      pageSize: Math.max(1, (output.rows || 24) - reserved),
      theme: { keybindings: ['vim'], style: { keysHelpTip: () => help } },
    }, { input, output });
  } catch (error) {
    if (error.name !== 'ExitPromptError') throw error;
    console.log('Installation cancelled.');
    process.exit(0);
  }
}

// Checkbox menu (space toggles, a toggles all); resolves to the chosen items.
function multiSelect(message, items, preselectedIndices = []) {
  return ask('@inquirer/checkbox', '↑↓ navigate · space select · a all · enter confirm', {
    message,
    choices: items.map((item, index) => ({
      name: item.type ? `${item.name} [${item.type === 'mcp' ? 'mcp' : item.type === 'local' ? 'skill' : 'pack'}]` : item.name,
      short: item.name,
      description: item.desc,
      value: item,
      checked: preselectedIndices.includes(index),
    })),
  });
}

// One of `items`; resolves to the chosen index.
function singleSelect(message, items, initial) {
  return ask('@inquirer/select', '↑↓ navigate · enter confirm', {
    message,
    choices: items.map((name, index) => ({ name, value: index })),
    default: initial,
  });
}

// After preflight has cleared every selected addon before any change.
function installLocalSkill(skillName, roots, installedSkills = new Map()) {
  if (!fs.existsSync(path.join(OPTIONAL_SKILLS_SOURCE, skillName))) {
    log(`   ⚠️  Skill "${skillName}" not found`, 'yellow');
    return false;
  }
  log(`\n🛠️  Installing ${skillName}...`, 'cyan');
  for (const root of roots) {
    installOptionalSkillInto(root, skillName, installedSkills);
    writeInstallMarker(root, [skillName], readInstallManifest(root));
  }
  return true;
}

// One optional skill into one skill-loader directory, replacing any older copy of it. A
// copy under its name before the 4.0.0 rename goes only once the new one is complete.
function installOptionalSkillInto(target, skillName, installedSkills) {
  const dest = path.join(target, skillName);
  const stage = fs.mkdtempSync(path.join(target, '.devlyn-skill-'));
  const stagedSkill = path.join(stage, skillName);
  try {
    const files = copyRecursive(path.join(OPTIONAL_SKILLS_SOURCE, skillName), stagedSkill, stage);
    assertCompleteSkillInstall(OPTIONAL_SKILLS_SOURCE, stage, [skillName]);
    fs.rmSync(dest, { recursive: true, force: true });
    fs.renameSync(stagedSkill, dest);
    installedSkills.set(dest, files.map((file) => path.join(dest, path.relative(stagedSkill, file))));
  } finally {
    fs.rmSync(stage, { recursive: true, force: true });
  }

}

// A 0.6.0-0.7.1 copy is one SKILL.md, the file that identifies it. A failed swap leaves
// that copy for the retry; a successful refresh discards its generated metadata too.
function refreshPreStandardCopy(target, skillName) {
  const dir = path.join(target, skillName);
  const skill = path.join(dir, 'SKILL.md');
  const staged = `${skill}.${process.pid}.tmp`;
  try {
    fs.copyFileSync(path.join(OPTIONAL_SKILLS_SOURCE, skillName, 'SKILL.md'), staged);
    for (const name of fs.readdirSync(dir)) {
      const file = path.join(dir, name);
      if (isIgnoredEntry(file)) fs.rmSync(file, { recursive: true });
    }
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

function installAddon(addon) {
  if (addon.type === 'mcp') {
    return installMcpServer(addon.name, addon.command);
  }
  return installSkillPack(addon.name);
}

// The core skills into one skill root, replacing older copies and retired skills, then the
// marker that records a complete install.
function installCoreSkills(skillsDir, installedSkills = new Map()) {
  const sourceSkillsDir = path.join(CONFIG_SOURCE, 'skills');
  log(`\n📁 Installing devlyn skills to ${skillsDir.replace(os.homedir(), '~')}`, 'green');
  fs.mkdirSync(skillsDir, { recursive: true });
  const previous = readInstallManifest(skillsDir);
  clearInstallMarker(skillsDir);
  for (const skillName of DEVLYN_CORE_SKILLS) {
    const src = path.join(sourceSkillsDir, skillName);
    const dest = path.join(skillsDir, skillName);
    if (!fs.existsSync(src)) continue;
    // Full replace: copyRecursive is an overlay, so stale files would otherwise persist.
    fs.rmSync(dest, { recursive: true, force: true });
    installedSkills.set(dest, copyRecursive(src, dest, skillsDir));
  }
  assertCompleteSkillInstall(sourceSkillsDir, skillsDir, DEVLYN_CORE_SKILLS);
  const refreshed = refreshRenamedSkills(skillsDir, installedSkills);
  writeInstallMarker(skillsDir, [...DEVLYN_CORE_SKILLS, ...refreshed], previous);
}

function readProjectGitignore() {
  const gitignorePath = path.join(projectDir(), '.gitignore');
  const stat = fs.lstatSync(gitignorePath, { throwIfNoEntry: false });
  // Refuse symlinks and hardlinks even when no rules need changing, before any installation write.
  if (stat && (!stat.isFile() || stat.nlink !== 1)) {
    throw new InstructionError(`Cannot update ${gitignorePath}: not a regular file with a single link (links are refused).`);
  }
  return stat ? fs.readFileSync(gitignorePath) : Buffer.alloc(0);
}

// Ignore runtime state; let the project's install marker travel with its skills.
function updateProjectGitignore(markerEntry) {
  const gitignorePath = path.join(projectDir(), '.gitignore');
  const original = readProjectGitignore();
  const marker = Buffer.from(markerEntry);
  const managedHeader = Buffer.from('# devlyn-cli pipeline state');
  const runtimeRules = [Buffer.from('.devlyn/'), Buffer.from('.devlyn')];
  const lines = [];
  for (let start = 0; start < original.length;) {
    const lf = original.indexOf(0x0a, start);
    const end = lf === -1 ? original.length : lf + 1;
    const patternEnd = lf === -1 ? end : original[lf - 1] === 0x0d ? lf - 1 : lf;
    lines.push({ raw: original.subarray(start, end), pattern: original.subarray(start, patternEnd) });
    start = end;
  }
  const kept = lines.filter(({ pattern }, index) => {
    if (pattern.equals(marker)) return false;
    if (!pattern.equals(managedHeader)) return true;
    // A header owns contiguous patterns until a blank/comment; remove it only when marker removal empties that block.
    const entries = [];
    for (let next = index + 1; next < lines.length; next++) {
      const entry = lines[next].pattern;
      if (!entry.length || entry[0] === 0x23) break;
      entries.push(entry);
    }
    return !entries.some((entry) => entry.equals(marker)) || entries.some((entry) => !entry.equals(marker));
  });
  let gitignoreContent = Buffer.concat(kept.map((line) => line.raw));
  if (!kept.some(({ pattern }) => runtimeRules.some((rule) => pattern.equals(rule)))) {
    const lf = original.indexOf(0x0a);
    const eol = lf > 0 && original[lf - 1] === 0x0d ? '\r\n' : '\n';
    const prefix = gitignoreContent.length && gitignoreContent.at(-1) !== 0x0a ? eol : '';
    const header = kept.some(({ pattern }) => pattern.equals(managedHeader))
      ? '' : `${gitignoreContent.length ? eol : ''}${managedHeader}${eol}`;
    gitignoreContent = Buffer.concat([gitignoreContent, Buffer.from(`${prefix}${header}.devlyn/${eol}`)]);
  }
  if (!gitignoreContent.equals(original)) {
    fs.writeFileSync(gitignorePath, gitignoreContent);
    log('  → .gitignore (updated project install rules)', 'dim');
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

function installAgentsProject(withClaude, installedSkills = new Map()) {
  if (!agentsMdIsClaudeMd()) {
    updateInstructions('AGENTS.md');
  } else if (withClaude) {
    log('  → AGENTS.md is CLAUDE.md here, so it gets the devlyn block written there', 'dim');
  } else {
    throw new InstructionError('AGENTS.md is CLAUDE.md under another name here. Choose CLAUDE.md as well '
      + '(npx devlyn-cli -y --claude) so the devlyn block is written once, into CLAUDE.md.');
  }
  installCoreSkills(skillRoots('agents', false)[0], installedSkills);
  updateProjectGitignore('.agents/skills/.devlyn-install.json');
}

// Whether Claude Code reads the devlyn defaults of AGENTS.md through an `@AGENTS.md` import in this CLAUDE.md text.
// An AGENTS.md that is CLAUDE.md under another name holds CLAUDE.md's own defaults.
function importsAgentsDefaults(claude) {
  const agents = path.join(projectDir(), 'AGENTS.md');
  return importsAgentsMd(claude) && !agentsMdIsClaudeMd() && fs.statSync(agents, { throwIfNoEntry: false })?.isFile() === true
    && holdsDevlynDefaults('AGENTS.md', fs.readFileSync(agents, 'utf8'));
}

// Claude Code reads AGENTS.md only where no CLAUDE.md exists, or through a CLAUDE.md that imports it. So a new
// CLAUDE.md imports an existing AGENTS.md, and a CLAUDE.md importing an AGENTS.md that holds devlyn defaults holds no
// copy of its own, not even one it got while AGENTS.md lacked the block. Only the AGENTS.md target updates those defaults,
// together with .agents/skills, so the Claude target stops while they need an update.
function installClaudeInstructions() {
  const file = path.join(projectDir(), 'CLAUDE.md');
  const stat = fs.lstatSync(file, { throwIfNoEntry: false });
  const initial = !stat && fs.statSync(path.join(projectDir(), 'AGENTS.md'), { throwIfNoEntry: false })?.isFile() ? '@AGENTS.md\n' : '';
  const imported = importsAgentsDefaults(stat?.isFile() ? fs.readFileSync(file, 'utf8') : initial);
  if (imported && updateInstructions('AGENTS.md', '', true, false)) {
    throw new InstructionError('Claude Code reads AGENTS.md here, and its devlyn defaults need an update. Codex, omp, Pi and Grok '
      + 'read them too, with .agents/skills, so choose AGENTS.md as well (npx devlyn-cli -y --claude) to update both together.');
  }
  updateInstructions('CLAUDE.md', initial, !imported);
  if (imported) log('  → CLAUDE.md imports AGENTS.md, which holds the devlyn block', 'dim');
}

// Project CLAUDE.md and .claude/: skills and settings.
function installClaudeCore(installedSkills = new Map()) {
  const skillsDir = skillRoots('claude', false)[0];
  const targetDir = path.dirname(skillsDir);
  // Read before any write, so settings this install cannot merge leave the Claude target as it was.
  const settingsPath = path.join(targetDir, 'settings.json');
  const unmergeable = (reason) => new InstructionError(`Cannot merge .claude/settings.json: ${reason}. `
    + 'CLAUDE.md and .claude/ are unchanged; fix the file and rerun the same install command.');
  const settingsStat = fs.lstatSync(settingsPath, { throwIfNoEntry: false });
  if (settingsStat && !settingsStat.isFile()) throw unmergeable('not a regular file');
  let settings = {};
  if (fs.existsSync(settingsPath)) {
    try {
      // Claude Code accepts a leading byte order mark.
      settings = JSON.parse(fs.readFileSync(settingsPath, 'utf8').replace(/^\uFEFF/, ''));
    } catch (error) {
      throw unmergeable(error.message);
    }
  }
  if (!settings || typeof settings !== 'object' || Array.isArray(settings)) {
    throw unmergeable('root must be a JSON object');
  }
  if (Object.prototype.hasOwnProperty.call(settings, 'env')
      && (!settings.env || typeof settings.env !== 'object' || Array.isArray(settings.env))) {
    throw unmergeable('env must be a JSON object');
  }
  installClaudeInstructions();
  installCoreSkills(skillsDir, installedSkills);
  updateProjectGitignore('.claude/skills/.devlyn-install.json');

  // One-hour foreground Bash calls and one-hour prompt caching serve a drain host that waits in the foreground.
  let settingsChanged = false;
  if (!Object.prototype.hasOwnProperty.call(settings, 'env')) {
    settings.env = {};
    settingsChanged = true;
  }
  if (!Object.prototype.hasOwnProperty.call(settings.env, 'ENABLE_PROMPT_CACHING_1H')) {
    settings.env.ENABLE_PROMPT_CACHING_1H = 'true';
    settingsChanged = true;
  }
  if (!Object.prototype.hasOwnProperty.call(settings.env, 'BASH_MAX_TIMEOUT_MS')) {
    settings.env.BASH_MAX_TIMEOUT_MS = '3600000';
    settingsChanged = true;
  }
  settingsChanged = cleanRetiredSettings(settings) || settingsChanged;
  if (settingsChanged) {
    replaceFile(settingsPath, JSON.stringify(settings, null, 2) + '\n');
    log('  → settings.json', 'dim');
  }
  // Their ownership cannot be established, so the other retired settings stay; name the ones present.
  const retired = [
    ...RETIRED_ENV.filter((key) => Object.prototype.hasOwnProperty.call(settings.env, key)),
    ...RETIRED_PERMISSIONS.filter((rule) => Array.isArray(settings.permissions?.allow) && settings.permissions.allow.includes(rule)),
  ];
  if (retired.length > 0) {
    log(`  Retired devlyn settings may remain in .claude/settings.json: ${retired.join(', ')} — delete those you did not add yourself.`, 'yellow');
  }
}

// Replace this directory entry, never a hardlink's other names.
function replaceFile(file, text) {
  const temp = `${file}.${crypto.randomUUID()}.tmp`;
  try {
    const mode = fs.lstatSync(file, { throwIfNoEntry: false })?.mode & 0o777;
    fs.writeFileSync(temp, text, { flag: 'wx', mode: mode || 0o600 });
    fs.renameSync(temp, file);
  } finally {
    fs.rmSync(temp, { force: true });
  }
}

function cleanRetiredSettings(settings) {
  let changed = false;
  // Remove exactly the retired Stop hook command, and its entry only when nothing else is left in it.
  const retiredHook = (hook) => hook?.type === 'command' && hook.command === RETIRED_STOP_HOOK;
  const stop = Array.isArray(settings.hooks?.Stop) ? settings.hooks.Stop : [];
  for (let i = stop.length - 1; i >= 0; i--) {
    const hooks = stop[i]?.hooks;
    if (!Array.isArray(hooks) || !hooks.some(retiredHook)) continue;
    stop[i].hooks = hooks.filter((hook) => !retiredHook(hook));
    if (stop[i].hooks.length === 0 && Object.keys(stop[i]).length === 1) stop.splice(i, 1);
    log('  ✕ settings.json Stop hook of the retired pipeline (removed)', 'dim');
    changed = true;
  }
  return changed;
}

// Shared user roots need one writer from ownership checks through the last addon write.
// Never reap a foreign lock: PID reuse and slow installs make age/liveness unsafe evidence.
const heldSkillLocks = new Set();
function withUserSkillLocks(roots, action, { existingOnly = false } = {}) {
  const locks = [];
  const createdDirs = [];
  try {
    for (const root of roots) {
      const lock = path.join(root, DEVLYN_INSTALL_LOCK);
      try {
        for (const dir of [path.dirname(root), root]) {
          const stat = fs.lstatSync(dir, { throwIfNoEntry: false });
          if (stat && !stat.isDirectory()) throw new Error(`not a real directory: ${dir}`);
        }
        if (existingOnly && !fs.lstatSync(root, { throwIfNoEntry: false })?.isDirectory()) return;
        if (!existingOnly) {
          const missing = [];
          for (let dir = root; !fs.existsSync(dir); dir = path.dirname(dir)) {
            missing.push(dir);
            if (path.dirname(dir) === dir) break;
          }
          fs.mkdirSync(root, { recursive: true });
          createdDirs.push(...missing);
        }
        const token = crypto.randomBytes(16).toString('hex');
        const fd = fs.openSync(lock, 'wx', 0o600);
        try {
          fs.writeFileSync(fd, JSON.stringify({ pid: process.pid, token }) + '\n');
          locks.push({ lock, token });
          heldSkillLocks.add(root);
        } catch (error) {
          // A failed initial write may not leave parseable JSON; verify the open file's identity.
          const opened = fs.fstatSync(fd);
          const current = fs.lstatSync(lock, { throwIfNoEntry: false });
          if (current?.dev === opened.dev && current?.ino === opened.ino) fs.unlinkSync(lock);
          throw error;
        } finally {
          fs.closeSync(fd);
        }
      } catch (error) {
        if (error.code === 'EEXIST') {
          let owner;
          try {
            owner = `pid ${JSON.parse(fs.readFileSync(lock, 'utf8')).pid}`;
          } catch (readError) {
            owner = `cannot read lock owner: ${readError.message}`;
          }
          throw new InstructionError(`Another devlyn-cli is changing ${root} (${owner}). `
            + `If none is running, delete ${lock} and run again.`);
        }
        throw new InstructionError(`Cannot lock ${root}: ${error.message}. Check ${lock} and run again.`);
      }
    }
    return action();
  } finally {
    const errors = [];
    for (const { lock, token } of locks.reverse()) {
      heldSkillLocks.delete(path.dirname(lock));
      try {
        if (JSON.parse(fs.readFileSync(lock, 'utf8')).token === token) fs.unlinkSync(lock);
      } catch (error) {
        if (error.code !== 'ENOENT') errors.push(`${lock}: ${error.message}`);
      }
    }
    // Refusal must not leave empty roots created just to acquire their locks.
    for (const dir of createdDirs) {
      try {
        fs.rmdirSync(dir);
      } catch (error) {
        if (!['ENOTEMPTY', 'EEXIST', 'ENOENT'].includes(error.code)) errors.push(`${dir}: ${error.message}`);
      }
    }
    if (errors.length) throw new InstructionError(`Cannot release install locks; check these paths:\n${errors.join('\n')}`);
  }
}

// Installs the targets in one scope; returns the installed skill roots.
function install(targets, global, optionalNames = [], plan, afterInstall = () => {}) {
  // In the home folder CLAUDE.md, AGENTS.md (agents read a parent folder's too) and
  // .claude/settings.json would apply to every project. Same folder by identity, so a link or
  // another spelling of the path is caught too.
  const home = fs.statSync(os.homedir(), { bigint: true, throwIfNoEntry: false });
  const here = fs.statSync(projectDir(), { bigint: true });
  if (!global && home?.dev === here.dev && home?.ino === here.ino) {
    throw new InstructionError('This project is your home folder, so its CLAUDE.md, AGENTS.md and .claude/settings.json '
      + 'would apply to every project. Run from a project folder, or use --global for skills only.');
  }
  const roots = targets.flatMap((target) => skillRoots(target, global));
  return withUserSkillLocks(global ? roots : [], () => {
    const installedSkills = new Map();
    if (!global) readProjectGitignore();
    plan ??= preflightSkills(roots, optionalNames);
    // AGENTS.md first, whatever order the menu gave: a new CLAUDE.md holds the block only when AGENTS.md does not.
    for (const target of ['agents', 'claude'].filter((name) => targets.includes(name))) {
      if (global) skillRoots(target, true).forEach((root) => installCoreSkills(root, installedSkills));
      else if (target === 'agents') installAgentsProject(targets.includes('claude'), installedSkills);
      else installClaudeCore(installedSkills);
    }
    for (const name of optionalNames) installLocalSkill(name, roots, installedSkills);
    afterInstall();
    log(`\n✅ devlyn ${PKG.version} installed`, 'green');
    if (global) log('The principles block installs per project: run npx devlyn-cli in the project without --global.');
    noticeGlobalDrift(roots);
    cleanupScope(global ? os.homedir() : projectDir(), global,
      global ? [] : targets.map((target) => target === 'agents' ? 'AGENTS.md' : 'CLAUDE.md'));
    if (!global) noticeIgnoredInstallFiles(installedSkills);
    return roots;
  });
}

// Cleanup visits existing paths in the command's scope; it never creates an install.
function cleanupScope(base, global, activeInstructions = []) {
  const warned = new Set();
  let found = false;
  const warning = (file, error) => {
    if (!warned.has(file)) log(`Cannot clean up ${file}: ${error.message}`, 'yellow');
    warned.add(file);
  };
  const attempt = (file, action) => {
    try { return action(); } catch (error) { warning(file, error); return false; }
  };
  const realParents = (file) => {
    let dir = base;
    if (!fs.lstatSync(dir, { throwIfNoEntry: false })?.isDirectory()) return false;
    for (const part of path.relative(base, path.dirname(file)).split(path.sep).filter(Boolean)) {
      if (part === '..') return false;
      dir = path.join(dir, part);
      if (!fs.lstatSync(dir, { throwIfNoEntry: false })?.isDirectory()) return false;
    }
    return true;
  };
  const remove = (file) => attempt(file, () => {
    if (!realParents(file) || !fs.lstatSync(file, { throwIfNoEntry: false })) return false;
    found = true;
    fs.rmSync(file, { recursive: true }); // lstat/realParents never follows a link; rm removes the link itself.
    log(`  ✕ ${path.relative(base, file)} (removed)`, 'dim');
    return true;
  });
  const hash = (file) => crypto.createHash('sha256')
    .update(fs.readFileSync(file).toString('latin1').replace(/\r\n/g, '\n'), 'latin1').digest('hex');
  for (const dir of global ? ['.agents', '.codex', '.claude', '.grok'] : ['.agents', '.claude']) {
    const root = path.join(base, dir, 'skills');
    attempt(root, () => {
      if (!realParents(root) || !fs.lstatSync(root, { throwIfNoEntry: false })?.isDirectory()) return;
      const retiredRoot = dir === '.grok';
      const clean = () => {
        const marker = path.join(root, DEVLYN_INSTALL_MARKER);
        let manifest;
        if (fs.lstatSync(marker, { throwIfNoEntry: false })?.isFile()) {
          try {
            const data = JSON.parse(fs.readFileSync(marker, 'utf8'));
            if (data && data.package === PKG.name && data.schemaVersion === 1
                && (data.skills === undefined || (data.skills && typeof data.skills === 'object' && !Array.isArray(data.skills)))) manifest = data.skills || {};
          } catch (error) {
            if (!(error instanceof SyntaxError)) throw error;
            // A malformed/foreign marker is not ownership evidence and stays in place.
          }
        }
        const exact = new Set([...deprecatedSkillPaths(root),
          ...Object.keys(RENAMED_SKILLS).flatMap((name) => legacySkillPaths(root, name))]
          .map((file) => path.basename(file).toLowerCase()));
        if (retiredRoot) for (const name of [...DEVLYN_CORE_SKILLS, ...Object.values(RENAMED_SKILLS)]
          .filter((name) => name.startsWith('devlyn'))) exact.add(name);
        const removed = new Set();
        for (const name of fs.readdirSync(root)) {
          const file = path.join(root, name);
          attempt(file, () => {
            const listed = manifest && Object.prototype.hasOwnProperty.call(manifest, name);
            let owned = exact.has(name.toLowerCase()) || (retiredRoot && listed && /^devlyn[-:\uF03A]/i.test(name));
            if (!owned && RETIRED_SKILL_MD_SHA256[name.toLowerCase()]) owned = isShippedCopy(file, RETIRED_SKILL_MD_SHA256[name.toLowerCase()]);
            if (!owned && retiredRoot && name.toLowerCase() === '_shared') owned = historicalSkill(file);
            if (!owned && retiredRoot && listed && fs.lstatSync(file).isDirectory()) {
              try { owned = fingerprint(file) === manifest[name]; }
              catch { /* Links or special files cannot prove a generic tree is an unedited copy. */ }
            }
            if (owned && remove(file)) removed.add(name);
          });
        }
        if (retiredRoot && manifest) {
          if (![...warned].some((file) => path.dirname(file) === root)) remove(marker);
        } else if (manifest && [...removed].some((name) => Object.prototype.hasOwnProperty.call(manifest, name))) {
          // Keep current markers accurate after cleaning a previously listed retired entry.
          attempt(marker, () => {
            const data = JSON.parse(fs.readFileSync(marker, 'utf8'));
            for (const name of removed) delete data.skills[name];
            replaceFile(marker, JSON.stringify(data, null, 2) + '\n');
          });
        }
      };
      if (heldSkillLocks.has(root)) clean();
      else withUserSkillLocks([root], clean, { existingOnly: true });
    });
  }
  const commands = path.join(base, '.claude', 'commands');
  attempt(commands, () => {
    if (!realParents(commands) || !fs.lstatSync(commands, { throwIfNoEntry: false })?.isDirectory()) return;
    const names = new Set(DEPRECATED_FILES.map((file) => path.basename(file).toLowerCase()));
    for (const name of fs.readdirSync(commands)) if (names.has(name.toLowerCase())) remove(path.join(commands, name));
  });
  for (const [name, hashes] of global ? [] : Object.entries(CLEANUP_HISTORY.files)) {
    const file = path.join(base, name);
    attempt(file, () => {
      if (realParents(file) && fs.lstatSync(file, { throwIfNoEntry: false })?.isFile() && hashes.includes(hash(file))) remove(file);
    });
  }
  const settingsFile = path.join(base, '.claude', 'settings.json');
  attempt(settingsFile, () => {
    if (!realParents(settingsFile) || !fs.lstatSync(settingsFile, { throwIfNoEntry: false })?.isFile()) return;
    let settings;
    try { settings = JSON.parse(fs.readFileSync(settingsFile, 'utf8').replace(/^\uFEFF/, '')); }
    catch (error) { if (error instanceof SyntaxError) return; throw error; }
    if (settings && typeof settings === 'object' && cleanRetiredSettings(settings)) {
      found = true;
      replaceFile(settingsFile, JSON.stringify(settings, null, 2) + '\n');
      log('  ✕ .claude/settings.json retired entries (removed)', 'dim');
    }
  });
  const instructions = global ? [] : ['CLAUDE.md', 'AGENTS.md', 'GEMINI.md', '.cursorrules', '.windsurfrules', '.github/copilot-instructions.md'];
  for (const name of instructions.filter((name) => !activeInstructions.includes(name))) {
    const file = path.join(base, name);
    attempt(file, () => {
      if (!realParents(file) || !fs.lstatSync(file, { throwIfNoEntry: false })?.isFile()) return;
      const evaluatorOnly = ['CLAUDE.md', 'AGENTS.md'].includes(name);
      if (!updateInstructions(name, '', false, false, base, evaluatorOnly)) return;
      found = true;
      updateInstructions(name, '', false, true, base, evaluatorOnly);
    });
  }
  return found;
}

// Advisory only: check files this run copied, grouped by skill; a wholly ignored skill
// folder is deliberate. check-ignore omits tracked files, and Git failures stay silent.
function noticeIgnoredInstallFiles(installedSkills) {
  const cwd = projectDir();
  const groups = [...installedSkills.values()].map((files) =>
    files.map((file) => path.relative(cwd, file).split(path.sep).join('/')));
  const files = groups.flat();
  if (!files.length) return;
  const env = { ...gitEnvironment(), GIT_OPTIONAL_LOCKS: '0' };
  const git = (args, input) => spawnSync('git', ['-C', cwd, ...args], { encoding: 'utf8', env, input });
  const result = git(['check-ignore', '-z', '--stdin'], files.join('\0') + '\0');
  if (result.error || ![0, 1].includes(result.status)) return;
  const matches = new Set(result.stdout.split('\0').filter(Boolean));
  const ignored = [...new Set(groups.flatMap((group) => {
    const hidden = group.filter((file) => matches.has(file));
    return hidden.length === group.length ? [] : hidden;
  }))];
  if (!ignored.length) return;
  const verbose = git(['check-ignore', '-v', '-z', '--stdin'], ignored[0] + '\0');
  if (verbose.error || verbose.status !== 0) return;
  const [source, line, pattern] = verbose.stdout.split('\0');
  log(`Git ignores ${ignored.length} installed file${ignored.length === 1 ? '' : 's'} (example rule: ${source}:${line}: ${pattern}).`, 'dim');
}

// A devlyn install in a user root this run does not refresh drifts and can shadow the
// project's copy; name it without touching it.
function noticeGlobalDrift(installed) {
  for (const dir of ['.agents', '.codex', '.claude']) {
    const root = path.join(os.homedir(), dir, 'skills');
    const marker = path.join(root, DEVLYN_INSTALL_MARKER);
    if (installed.includes(root) || !fs.existsSync(marker)) continue;
    let version;
    try {
      version = JSON.parse(fs.readFileSync(marker, 'utf8')).version;
    } catch (error) {
      version = `(unreadable marker: ${error.message})`;
    }
    if (version === PKG.version) continue;
    const advice = 'refresh it with --global, or delete it';
    log(`Global devlyn ${version} in ${root.replace(os.homedir(), '~')} — ${advice}.`, 'yellow');
  }
}

// Skip project setup in the home folder, where instructions would affect every project.
// Lock user roots, preflight all roots, check versions, then write.
function update() {
  showLogo();
  log('─'.repeat(44), 'dim');

  const userCandidates = [...skillRoots('agents', true), ...skillRoots('claude', true)];
  const linkedRoots = new Set();
  const linkNotices = [];
  for (const root of new Set([...userCandidates, ...skillRoots('agents', false), ...skillRoots('claude', false)])) {
    try {
      if (![path.dirname(root), root].some((dir) => fs.lstatSync(dir, { throwIfNoEntry: false })?.isSymbolicLink())) continue;
      linkedRoots.add(root);
      // Follow only for discovery; linked roots never enter the write/lock/preflight paths.
      if (!fs.statSync(root, { throwIfNoEntry: false })?.isDirectory()) continue;
      if (!fs.statSync(path.join(root, DEVLYN_INSTALL_MARKER), { throwIfNoEntry: false })
          && !fs.readdirSync(root).some((name) => name.startsWith('devlyn')
            && fs.statSync(path.join(root, name), { throwIfNoEntry: false })?.isDirectory())) continue;
      const notice = `Not updated: ${root} is a link — devlyn-cli does not write through links. `
        + 'Update the folder it points to, or replace the link with a folder.';
      linkNotices.push(notice);
      log(notice, 'yellow');
    } catch (error) {
      if (error.code === 'ENOTDIR') continue;
      throw new InstructionError(`Cannot inspect ${root}: ${error.message}. Check its permissions and run again.`);
    }
  }
  const userRoots = userCandidates.filter((root) => !linkedRoots.has(root) && hasDevlynInstall(root));
  const home = fs.statSync(os.homedir(), { bigint: true, throwIfNoEntry: false });
  const here = fs.statSync(projectDir(), { bigint: true });
  const targets = [];
  if (home?.dev !== here.dev || home?.ino !== here.ino) {
    if (!linkedRoots.has(skillRoots('agents', false)[0]) && hasDevlynInstall(skillRoots('agents', false)[0])) targets.push('agents');
    if (!linkedRoots.has(skillRoots('claude', false)[0]) && hasDevlynClaude(false)) targets.push('claude');
  }
  const projectRoots = targets.flatMap((target) => skillRoots(target, false));
  const roots = [...userRoots, ...projectRoots];
  if (!roots.length) {
    const userCleanup = cleanupScope(os.homedir(), true);
    const projectCleanup = (home?.dev !== here.dev || home?.ino !== here.ino) && cleanupScope(projectDir(), false);
    if (userCleanup || projectCleanup) return;
    throw new InstructionError(['No devlyn install here to update. Run npx devlyn-cli to install.', ...linkNotices].join('\n'));
  }

  return withUserSkillLocks(userRoots, () => {
    if (targets.length) readProjectGitignore();
    const plan = preflightSkills(roots);
    // Ownership preflight has already refused unreadable or invalid markers.
    const current = PKG.version.split('.').map(BigInt);
    const newer = roots.flatMap((root) => {
      const marker = path.join(root, DEVLYN_INSTALL_MARKER);
      if (!fs.existsSync(marker)) return [];
      const { version } = JSON.parse(fs.readFileSync(marker, 'utf8'));
      // SemVer 2.0.0's numbered-group regex: https://semver.org/#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string
      const parsed = typeof version === 'string' && version.match(/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$/);
      if (!parsed || parsed[0] !== version) {
        throw new InstructionError(`Update refused; nothing was changed. ${root}: cannot tell which devlyn-cli wrote it `
          + '(missing or malformed marker version). Restore the original install marker and run again.');
      }
      // This package is a plain release: equal-core prereleases are older, and build metadata is ignored.
      const parts = parsed.slice(1, 4).map(BigInt);
      const difference = parts.findIndex((part, index) => part !== current[index]);
      return difference !== -1 && parts[difference] > current[difference] ? [`  - ${root}: ${version}`] : [];
    });
    if (newer.length) {
      throw new InstructionError('Update refused; nothing was changed. Newer devlyn installs:\n'
        + newer.join('\n') + '\nRun npx devlyn-cli@latest update.');
    }

    userRoots.forEach((root) => installCoreSkills(root));
    if (targets.length) install(targets, false, [], plan, () => cleanupScope(os.homedir(), true));
    else {
      cleanupScope(os.homedir(), true);
      log(`\n✅ devlyn ${PKG.version} installed`, 'green');
      noticeGlobalDrift(userRoots);
    }
    if (!targets.length && (home?.dev !== here.dev || home?.ino !== here.ino)) {
      cleanupScope(projectDir(), false);
    }
  });
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

  const targetOptions = [
    { key: 'agents', name: 'AGENTS.md — Codex · omp · Pi · Grok', desc: 'AGENTS.md + .agents/skills' },
    { key: 'claude', name: 'CLAUDE.md — Claude Code', desc: 'CLAUDE.md + .claude/ (skills, settings)' },
  ];
  const preselected = claude || hasDevlynClaude(false) || (global && hasDevlynClaude(true)) ? [0, 1] : [0];
  const targets = (await multiSelect('What to install', targetOptions, preselected)).map((option) => option.key);

  if (targets.length === 0) {
    log('\n💡 Nothing selected — nothing installed.', 'yellow');
    log('   Run `npx devlyn-cli` again and pick at least one.\n', 'dim');
    return;
  }

  const scope = await singleSelect('Where', ['This project', 'Global — every project on this machine'], global ? 1 : 0);
  // Ask about optional addons (local skills + external packs; MCP servers belong to Claude Code)
  const selectedAddons = await multiSelect('Optional skills & packs', OPTIONAL_ADDONS.filter((addon) => addon.type !== 'mcp' || targets.includes('claude')));
  install(targets, scope === 1, selectedAddons.filter((addon) => addon.type === 'local').map((addon) => addon.name));

  if (selectedAddons.length > 0) {
    for (const addon of selectedAddons.filter((addon) => addon.type !== 'local')) {
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
  log('  npx devlyn-cli               Install/update devlyn: choose what (AGENTS.md, CLAUDE.md) and where (this project or global)');
  log('  npx devlyn-cli update        Update every devlyn install already here (this project and your global skill folders) to this version; installs nothing new');
  log('  npx devlyn-cli -y            Without prompts: AGENTS.md + .agents/skills, plus CLAUDE.md + .claude/ if this project has them');
  log('  npx devlyn-cli -y --claude   Also install CLAUDE.md + .claude/ for Claude Code');
  log('  npx devlyn-cli -y --global   Skills only, for every project on this machine (~/.agents/skills, ~/.codex/skills; ~/.claude/skills with --claude, or when it already has a devlyn install)');
  log('  npx devlyn-cli list          List available skills');
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
    const flags = command === 'init' || command === 'update' ? args.slice(1) : args;
    const unknown = command === 'update' ? flags[0] : flags.find((flag) => !INSTALL_FLAGS.includes(flag));
    if (unknown !== undefined) {
      log(`Unknown command: ${unknown}`, 'yellow');
      showHelp();
      process.exit(1);
    }
    if (command === 'update') {
      update();
      break;
    }
    await init({ yes: flags.includes('-y') || flags.includes('--yes'), claude: flags.includes('--claude'), global: flags.includes('--global') });
  }
}
}

main().catch((error) => {
  console.error(error instanceof InstructionError ? `\n${error.message}` : error);
  process.exitCode = 1;
});
