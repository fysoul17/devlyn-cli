<div align="center">

<br />

<picture>
  <img alt="DEVLYN" src="assets/logo.svg" width="540" />
</picture>

### Context Engineering & Harness Engineering Toolkit for Claude Code

**Structured prompts, agent orchestration, and automated pipelines — debugging, code review, UI design, product specs, and more.**

[![npm version](https://img.shields.io/npm/v/devlyn-cli.svg)](https://www.npmjs.com/package/devlyn-cli)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Claude Code](https://img.shields.io/badge/Claude_Code-compatible-blueviolet)](https://docs.anthropic.com/en/docs/claude-code)

[Get Started](#get-started) · [Commands](#commands) · [Skills](#skills) · [Workflows](#workflows) · [Optional Packs](#optional-skills--packs) · [Contributing](#contributing)

</div>

---

## Why devlyn-cli?

[Claude Code](https://docs.anthropic.com/en/docs/claude-code) is powerful out of the box — but teams need **consistent, repeatable workflows**. Without shared conventions, every developer prompts differently, reviews differently, and debugs differently.

devlyn-cli solves this with two complementary engineering approaches:

### Context Engineering

Structured prompts and role-based instructions that shape _what the AI knows and how it thinks_ for each task.

- **16 slash commands** for debugging, code review, UI design, documentation, and more
- **5 core skills** that activate automatically based on conversation context
- **Agent team workflows** that spawn specialized AI teammates with role-specific expertise
- **Product & feature spec templates** for structured planning

### Harness Engineering

Pipeline orchestration that controls _how agents execute_ — permissions, state management, multi-phase workflows, and cross-model evaluation.

- **`/devlyn:auto-resolve`** — 9-phase automated pipeline (build → browser validate → evaluate → fix loop → simplify → review → security → clean → docs)
- **`/devlyn:browser-validate`** — feature verification in a real browser with tiered fallback (Chrome MCP → Playwright → curl)
- **`bypassPermissions` mode** for autonomous subagent execution
- **File-based state machine** — agents communicate via `.devlyn/done-criteria.md`, `EVAL-FINDINGS.md`, and `BROWSER-RESULTS.md`
- **Git checkpoints** at each phase for rollback safety
- **Cross-model evaluation** via `--with-codex` flag (OpenAI Codex as independent evaluator)

**Zero dependencies. One command. Works with any project.**

## Get Started

```bash
npx devlyn-cli
```

The interactive installer walks you through setup — select optional skills, choose community packs, done.

```bash
# Non-interactive install (CI/CD friendly)
npx devlyn-cli -y

# Update to the latest version
npx devlyn-cli@latest

# See everything that's included
npx devlyn-cli list
```

### What Gets Installed

```
your-project/
├── .claude/
│   ├── commands/              # 16 slash commands
│   ├── skills/                # 5 core skills + any optional addons
│   ├── templates/             # Product spec, feature spec, prompt templates
│   ├── commit-conventions.md  # Commit message standards
│   └── settings.json          # Agent teams enabled
└── CLAUDE.md                  # Project-level AI instructions
```

## Commands

Slash commands are invoked directly in Claude Code conversations (e.g., type `/devlyn:resolve`).

### Debugging & Resolution

| Command | Description |
|---|---|
| `/devlyn:resolve` | Systematic bug fixing with root-cause analysis and test-driven validation |
| `/devlyn:team-resolve` | Spawns a full agent team — root cause analyst, test engineer, security auditor — to investigate complex issues |
| `/devlyn:auto-resolve` | Fully automated pipeline for any task — bugs, features, refactors, chores. Build → browser validate → evaluate → fix loop → simplify → review → clean → docs. One command, zero human intervention. Supports `--with-codex` for cross-model evaluation via OpenAI Codex |
| `/devlyn:browser-validate` | Verify implemented features work in a real browser — starts dev server, tests the feature end-to-end (clicks, forms, verification), with tiered fallback (Chrome MCP → Playwright → curl) |

### Code Review & Quality

| Command | Description |
|---|---|
| `/devlyn:review` | Post-implementation review — security, quality, best practices checklist |
| `/devlyn:team-review` | Multi-perspective team review with specialized reviewers (security, quality, testing, performance, product) |
| `/devlyn:evaluate` | Independent quality evaluation — assembles evaluator team to grade work against done criteria with calibrated, skeptical grading |
| `/devlyn:clean` | Detect and remove dead code, unused dependencies, complexity hotspots, and tech debt |

### UI Design & Implementation

| Command | Description |
|---|---|
| `/devlyn:design-ui` | Generate 5 radically distinct UI style explorations from a spec or reference image |
| `/devlyn:team-design-ui` | Spawns a design team — creative director, product designer, visual designer, interaction designer, accessibility designer |
| `/devlyn:design-system` | Extract design system tokens from a chosen style for exact reproduction |
| `/devlyn:implement-ui` | Team-based UI build — component architect, UX engineer, accessibility engineer, responsive engineer, visual QA |

### Product & Planning

| Command | Description |
|---|---|
| `/devlyn:product-spec` | Generate or incrementally update product spec documents |
| `/devlyn:feature-spec` | Transform product specs into implementable feature specifications |
| `/devlyn:discover-product` | Scan codebase to generate feature-oriented product documentation |
| `/devlyn:recommend-features` | Prioritize top 5 features to build next based on value and readiness |

### Documentation

| Command | Description |
|---|---|
| `/devlyn:update-docs` | Sync all project docs with current codebase — cleans stale content, preserves roadmaps, generates missing docs |

## Skills

Skills are **not invoked manually** — they activate automatically when Claude Code detects a relevant conversation context. Think of them as always-on expertise that shapes how the AI approaches specific types of work.

| Skill | When It Activates | What It Does |
|---|---|---|
| `root-cause-analysis` | Debugging conversations | Enforces 5 Whys methodology, evidence standards, and no-workaround rules |
| `code-review-standards` | Code review tasks | Applies severity framework, quality bar, and approval criteria |
| `ui-implementation-standards` | UI/frontend work | Ensures design fidelity, accessibility, animation quality, and responsive standards |
| `code-health-standards` | Code maintenance | Enforces dead code prevention, dependency discipline, and complexity thresholds |
| `workflow-routing` | Any task | SDLC phase map — guides you to the right command for your current task |

## Workflows

Commands are designed to compose. Pick the right tool based on scope, then chain them together.

### Automated Pipeline (Recommended)

One command runs the full cycle — no human intervention needed:

```bash
/devlyn:auto-resolve fix the auth bug where users see blank screen on 401
```

| Phase | What Happens |
|---|---|
| **Build** | `team-resolve` investigates and implements, writes testable done criteria |
| **Browser Validate** | For web projects: starts dev server, tests the implemented feature end-to-end in a real browser, fixes issues found |
| **Evaluate** | Independent evaluator grades against done criteria with calibrated skepticism |
| **Fix Loop** | If evaluation fails, fixes findings and re-evaluates (up to N rounds) |
| **Simplify** | Quick cleanup pass for reuse and efficiency |
| **Review** | Multi-perspective team review |
| **Security** | Dedicated OWASP-focused audit (auto-detects when changes touch auth, secrets, APIs) |
| **Clean** | Remove dead code and unused dependencies |
| **Docs** | Sync documentation with changes |

Each phase runs as a separate subagent (fresh context), communicates via files, and commits a git checkpoint for rollback safety. Skip phases with flags: `--skip-browser`, `--skip-review`, `--skip-clean`, `--skip-docs`, `--max-rounds 3`, `--with-codex` (cross-model evaluation via OpenAI Codex).

### Manual Workflow

For step-by-step control between phases:

| Step | Command | What It Does |
|---|---|---|
| 1. **Resolve** | `/devlyn:resolve` or `/devlyn:team-resolve` | Fix the issue — solo for focused bugs (1-2 modules), team for complex issues (3+ modules) |
| 2. **Evaluate** | `/devlyn:evaluate` | Independent quality evaluation — grades against done criteria written in step 1 |
| | | *If the evaluation finds issues: `/devlyn:team-resolve "Fix issues in .devlyn/EVAL-FINDINGS.md"`* |
| 3. **Simplify** | `/simplify` | Quick cleanup pass for reuse, quality, and efficiency *(built-in Claude Code command)* |
| 4. **Review** | `/devlyn:review` or `/devlyn:team-review` | Audit the changes — solo for small PRs (< 10 files), team for large PRs (10+ files) |
| 5. **Clean** | `/devlyn:clean` | Remove dead code, unused dependencies, and complexity hotspots |
| 6. **Document** | `/devlyn:update-docs` | Sync project documentation with the current codebase |

Steps 5-6 are optional — run them periodically rather than on every PR.

> **Scope matching matters.** For a simple one-file bug, `/devlyn:resolve` + `/devlyn:review` (solo) is fast. For a multi-module feature, `/devlyn:auto-resolve` handles everything. Don't over-tool simple changes.

### UI Design Pipeline

A full explore → extract → build pipeline:

| Step | Command | What It Does |
|---|---|---|
| 1. **Explore** | `/devlyn:design-ui` | Generates 5 radically distinct style options from a spec or reference image |
| 2. **Extract** | `/devlyn:design-system` | Pulls exact design tokens (colors, spacing, typography) from your chosen style |
| 3. **Build** | `/devlyn:implement-ui` | Spawns a build team (component architect, UX engineer, accessibility engineer, responsive engineer, visual QA) |

> For design exploration with a full creative team, use `/devlyn:team-design-ui` instead of step 1.

After building, follow the [recommended workflow](#recommended-workflow) starting from step 2 (simplify) to review and polish the implementation.

### Standalone Tools

These commands work independently, outside of the main workflow:

| Command | What It Does |
|---|---|
| `/devlyn:clean [focus]` | Focused cleanup — e.g., `/devlyn:clean dependencies` or `/devlyn:clean dead-code` |
| `/devlyn:update-docs [area]` | Focused doc sync — e.g., `/devlyn:update-docs API reference` |
| `/devlyn:product-spec` | Generate or update a product specification |
| `/devlyn:feature-spec` | Transform a product spec into an implementable feature spec |
| `/devlyn:discover-product` | Scan codebase to auto-generate product documentation |
| `/devlyn:recommend-features` | Prioritize top 5 features to build next |

## Optional Skills & Packs

During installation, the interactive selector lets you add optional skills and community packs.

### Skills

Copied directly into your `.claude/skills/` directory.

| Skill | Description |
|---|---|
| `cloudflare-nextjs-setup` | Cloudflare Workers + Next.js deployment with OpenNext |
| `generate-skill` | Create well-structured Claude Code skills following Anthropic best practices |
| `prompt-engineering` | Claude 4 prompt optimization using official Anthropic best practices |
| `better-auth-setup` | Production-ready Better Auth + Hono + Drizzle + PostgreSQL auth setup |
| `pyx-scan` | Check whether an AI agent skill is safe before installing |
| `dokkit` | Document template filling for DOCX/HWPX — ingest, fill, review, export |
| `devlyn:pencil-pull` | Pull Pencil designs into code with exact visual fidelity |
| `devlyn:pencil-push` | Push codebase UI to Pencil canvas for design sync |

### Community Packs

Installed via the [skills CLI](https://github.com/anthropics/skills) (`npx skills add`). These are maintained by their respective communities.

| Pack | Description |
|---|---|
| `vercel-labs/agent-skills` | React, Next.js, React Native best practices |
| `supabase/agent-skills` | Supabase integration patterns |
| `coreyhaines31/marketingskills` | Marketing automation and content skills |
| `anthropics/skills` | Official Anthropic skill-creator with eval framework and description optimizer |
| `Leonxlnx/taste-skill` | Premium frontend design skills — modern layouts, animations, and visual refinement |

### MCP Servers

Installed via `claude mcp add` during setup.

| Server | Description |
|---|---|
| `codex-cli` | Codex MCP server for cross-model evaluation via OpenAI Codex |
| `playwright` | Playwright MCP for browser testing — powers `devlyn:browser-validate` Tier 2 |

> **Want to add a pack?** Open a PR adding your pack to the `OPTIONAL_ADDONS` array in [`bin/devlyn.js`](bin/devlyn.js).

## How It Works

1. **Run `npx devlyn-cli`** in your project root
2. The CLI copies config files into `.claude/` and `CLAUDE.md` to the project root
3. Claude Code automatically reads `.claude/commands/` and `.claude/skills/` on startup
4. Invoke commands like `/devlyn:resolve` in your Claude Code session — skills activate on their own

The installation is **idempotent** — run it again anytime to update to the latest config.

## Creating Your Own Skills

Want to author custom skills for your team or the community?

1. **During install**, select the `generate-skill` optional skill — or —
2. **Install the official Anthropic skill-creator** pack:
   ```bash
   npx skills add anthropics/skills
   ```

Both provide structured templates, best practices, and eval frameworks for writing high-quality Claude Code skills.

See the [Claude Code skills documentation](https://docs.anthropic.com/en/docs/claude-code/skills) for the full specification.

## Requirements

- **Node.js 18+**
- **[Claude Code](https://docs.anthropic.com/en/docs/claude-code)** CLI installed and configured

## Contributing

Contributions are welcome! Here are some ways to get involved:

- **Add a command** — Create a new `.md` file in `config/commands/`
- **Add a skill** — Create a new directory in `config/skills/` with a `SKILL.md`
- **Add an optional skill** — Add to `optional-skills/` and the `OPTIONAL_ADDONS` array
- **Suggest a community pack** — Open a PR to add it to the pack list

### Development

1. Fork the repository
2. Create your branch (`git checkout -b feat/my-feature`)
3. Commit your changes following the included [commit conventions](config/commit-conventions.md)
4. Push to the branch (`git push origin feat/my-feature`)
5. Open a Pull Request

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=fysoul17/devlyn-cli&type=Date)](https://star-history.com/#fysoul17/devlyn-cli&Date)

## License

[MIT](LICENSE) — Donut Studio
