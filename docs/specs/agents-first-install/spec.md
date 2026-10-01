# devlyn-cli 4.1.0 — AGENTS-first, project-scoped install

Status: agreed with the owner 2026-10-01 ("default is AGENTS.md; pick Claude or others with
Space; per-project install is the default, global is an option chosen second; 4.1.0, not 5.0").
The Devlyn app follows in devlyn-os-v1 `docs/specs/harnesses-reader-paths/spec.md`.

## Why
- 4.x installs Claude Code by default and puts every other engine's skills in user-global
  roots (`~/.codex/skills`, `~/.agents/skills`, `~/.grok/skills`). `npx devlyn-cli -y` never
  refreshes them, so they drift (the owner's Mac sat on 3.3.1 under 4.0.1 projects), they
  leak into isolated comparisons, and Grok loaded a stale global copy instead of the
  project's (traced 2026-10-01).
- One project copy serves most readers (measured 2026-10-01):

  | Reader | Instructions | Project skills it loads |
  |---|---|---|
  | Codex 0.159.2 | AGENTS.md | `.agents/skills` (also `~/.codex/skills`, `~/.agents/skills`) |
  | omp 16.5.0 | AGENTS.md | `.agents/skills`, `.claude/skills`, `.omp/skills` |
  | Grok 1.0.41 | AGENTS.md | `.grok/skills`, `.agents/skills`, `.claude/skills` (trusted folders) |
  | Pi | AGENTS.md | `.agents/skills` (Agent Skills convention; not traced) |
  | Claude Code 2.1.286 | CLAUDE.md, else AGENTS.md (traced) | `.claude/skills` only (`.agents/skills` not loaded, traced) |

## Contract

### Interactive (`npx devlyn-cli`)
1. What — two choices named by their instruction file (owner 2026-10-01: "everything except
   CLAUDE.md is AGENTS.md"; multi-select, Space toggles, Enter confirms):
   - `AGENTS.md — Codex · omp · Pi · Grok` (AGENTS.md + `.agents/skills`). Checked by default.
   - `CLAUDE.md — Claude Code` (CLAUDE.md + `.claude/`). Checked when this project already has
     a devlyn Claude install (skills, commands or a CLAUDE.md managed block).
   Selecting nothing installs nothing (exit 0 with a hint), as today.
2. Where (single select; Enter confirms): `This project` (default) or
   `Global — every project on this machine`.
3. Optional skills & packs (existing step). Local optional skills install into the root of
   every selected target in the chosen scope. Claude-only addons (MCP servers via
   `claude mcp add`) are offered only when the Claude target is selected.

### Non-interactive
- `npx devlyn-cli -y`: the AGENTS target plus every target already installed in this
  project, project scope. A 4.x project with `.claude/skills` keeps its Claude update and
  gains AGENTS.md + `.agents/skills`.
- `--claude` adds the Claude target; `--global` selects global scope (with `-y` or
  interactively it preselects step 2). With `-y --global`, Claude counts as installed when
  `~/.claude/skills` has a devlyn install marker. No other flags.
- `npx devlyn-cli agents …` is removed: it prints the replacement (`npx devlyn-cli` /
  `-y [--claude] [--global]`) and exits 1.

### What each target writes
- AGENTS, project: the `AGENTS.md` managed block; `.agents/skills/<core skills>` with
  `.agents/skills/.devlyn-install.json`; `.gitignore` gains `.devlyn/` and
  `.agents/skills/.devlyn-install.json`.
- Claude, project: as 4.0.1 (CLAUDE.md managed block, `.claude/skills` + marker,
  `.claude/templates`, `.claude/commit-conventions.md`, `.claude/settings.json`
  permissions/env/Stop hook, `.gitignore`), except that `ENABLE_PROMPT_CACHING_1H` is set in
  the project `.claude/settings.json` env instead of `~/.claude/settings.json`. Refused before any
  write when the project is the home folder, whose CLAUDE.md and settings apply to every project.
- Global: skills only. AGENTS → `~/.agents/skills` (omp, Pi, Grok) and `~/.codex/skills`
  (Codex); Claude → `~/.claude/skills`. No project file and no `~/.claude/settings.json`.
- Old names, retired skills and refresh rules of 4.0.1 apply only to the roots this run
  installs into. A retired skill that is now an optional addon goes only as an unedited default
  copy, never as an opted-in or user-written folder.

### Instruction template
- `AGENTS.md` (the package template) becomes engine-neutral in its title and intro only:
  `# Project Instructions`; the intro names AGENTS.md readers (Codex, omp, Pi, Grok, and
  Claude Code when the project has no CLAUDE.md). The rest of the contract is unchanged.
- Every published AGENTS.md/CLAUDE.md block version stays recognized
  (`bin/instruction-templates.json`, regenerated at publish), so upgrades replace, never stack.

### Reader isolation
- The VERIFY pair-judge and probe "must not read" lists (devlyn-resolve `SKILL.md:340`,
  `references/phases/verify.md:189`, `references/phases/probe-derive.md:27`) add
  `.agents/skills`.

### Global drift notice
- When a devlyn install marker exists in a user root that this run does not install into,
  print one line: `Global devlyn <version> in <root> — refresh it with --global, or delete it.`
  `~/.grok/skills` (4.0's Grok root, which no target writes now) gets `— delete it.`
  Nothing else changes there.

## Out of scope
- Global instruction files (`~/.codex/AGENTS.md`, `~/.claude/CLAUDE.md`).
- Merging the CLAUDE.md and AGENTS.md contracts; skill content beyond the isolation list.

## Verification
- `scripts/test-windows-portability.py`: interactive picker defaults and Space/Enter
  handling; every target × scope; `-y` on an empty project, on a 4.0.1 Claude project and on
  a 3.x project; `--claude`; `--global`; `agents` exits 1 with the replacement; no
  CLAUDE.md created unless the Claude choice is selected; prompt-caching env in the project settings and none in
  `~/.claude/settings.json`; drift notice; installed bytes = package bytes in every root
  written, before and after reinstall.
- `scripts/lint-skills.sh` passes (update its expectations where the contract changed).
- Upgrade matrix over all published versions → 4.1.0 (`-y`): no hard failures; every change
  explained.
- Real reader traces in a project installed with `-y` only: Codex, omp, Grok (trusted) run
  `devlyn-engines` from `.agents/skills`; Claude Code reads AGENTS.md and has no devlyn
  skills; after `-y --claude`, Claude Code runs `devlyn-engines` from `.claude/skills`.
- Windows CI (portability workflow) green; reviews by Astra ultra, Grok and Claude to SHIP.

## Release
- 4.1.0 is not a new major, so `publish.yml` publishes it straight to npm `latest`.
  The Devlyn app's installer runs `devlyn-cli@latest`; its Harnesses update ships with the
  next app release.
