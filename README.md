<div align="center">

<br />

<picture>
  <img alt="DEVLYN" src="assets/logo.svg" width="540" />
</picture>

### Context Engineering & Harness Engineering Toolkit for Claude Code

**Structured prompts, agent orchestration, and automated pipelines — debugging, code review, UI design, product specs, and more.**

[![npm version](https://img.shields.io/npm/v/devlyn-cli.svg)](https://www.npmjs.com/package/devlyn-cli)
[![npm downloads](https://img.shields.io/npm/dw/devlyn-cli.svg)](https://www.npmjs.com/package/devlyn-cli)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Claude Code](https://img.shields.io/badge/Claude_Code-compatible-blueviolet)](https://docs.anthropic.com/en/docs/claude-code)

If devlyn-cli saved you time, [give it a star](https://github.com/fysoul17/devlyn-cli) — it helps others find it too.

</div>

---

## Install

```bash
npx devlyn-cli
```

That's it. The interactive installer handles everything. Run it again anytime to update.

---

## How It Works — Three Steps, Full Cycle

devlyn-cli turns Claude Code into an autonomous development pipeline. The core loop is simple:

```
ideate  →  auto-resolve  →  preflight  →  fix gaps  →  ship
```

### Step 1 — Plan with `/devlyn:ideate`

Turn a raw idea into structured, implementation-ready specs.

```
/devlyn:ideate "I want to build a habit tracking app with AI nudges"
```

This produces three documents through interactive brainstorming:

| Document | What It Contains |
|---|---|
| `docs/VISION.md` | North star, principles, anti-goals |
| `docs/ROADMAP.md` | Phased roadmap with links to each spec |
| `docs/roadmap/phase-N/*.md` | Self-contained spec per feature — ready for auto-resolve |

Need to add features later? Run ideate again — it expands the existing roadmap.

### Step 2 — Build with `/devlyn:auto-resolve`

Point it at a spec (or just describe what you want) and walk away.

```
/devlyn:auto-resolve "Implement per spec at docs/roadmap/phase-1/1.1-user-auth.md"
```

It runs a **10-phase pipeline** autonomously:

```
Build → Build Gate → Browser Test → Evaluate → Fix Loop → Simplify → Review → Security → Clean → Docs
```

- Each phase runs as a separate agent with fresh context
- Git checkpoints at every phase for safe rollback
- **Build Gate** runs your project's real compilers, typecheckers, and linters — catches type errors, cross-package drift, and Docker build failures that tests alone miss. Auto-detects project type (Next.js, Rust, Go, Solidity, Expo, Swift, and more) and Dockerfiles.
- Browser validation tests your feature end-to-end (clicks, forms, verification)
- Evaluation grades against done-criteria — if it fails, auto-fix and re-evaluate

Skip phases you don't need: `--skip-browser`, `--skip-review`, `--skip-clean`, `--skip-docs`, `--skip-build-gate`, `--max-rounds 6`
Customize the build gate: `--build-gate strict` (warnings = errors), `--build-gate no-docker` (skip Docker builds for speed)

### Step 3 — Verify with `/devlyn:preflight`

After implementing all roadmap items, run a final alignment check:

```
/devlyn:preflight
```

Reads every commitment from your vision, roadmap, and item specs, then audits the codebase evidence-based. Catches what you missed:

| Category | What It Finds |
|---|---|
| `MISSING` | In roadmap but not implemented |
| `INCOMPLETE` | Started but unfinished |
| `DIVERGENT` | Implemented differently than spec |
| `BROKEN` | Has a bug preventing it from working |
| `STALE_DOC` | Docs don't match current code |

Confirmed gaps become new roadmap items — feed them back into auto-resolve. Use `--autofix` to do this automatically, or `--phase 2` to check only one phase.

### Bonus — Dual-Model Mode with Codex

Install the Codex MCP server during setup, then:

```
/devlyn:auto-resolve "fix the auth bug" --with-codex
```

Claude builds, **OpenAI Codex evaluates independently** — two models collaborating, catching what a single model misses.

> `--with-codex evaluate` (default) · `--with-codex review` · `--with-codex both`

---

## Manual Commands

When you want step-by-step control instead of the full pipeline.

### Debugging & Resolution

| Command | Use When |
|---|---|
| `/devlyn:resolve` | Simple bugs (1-2 files) |
| `/devlyn:team-resolve` | Complex issues — spawns root-cause analyst, test engineer, security auditor |
| `/devlyn:browser-validate` | Test a web feature in a real browser (Chrome MCP → Playwright → curl fallback) |

### Code Review & Quality

| Command | Use When |
|---|---|
| `/devlyn:review` | Solo review — security, quality, best practices checklist |
| `/devlyn:team-review` | Multi-reviewer team — security, testing, performance, product perspectives |
| `/devlyn:evaluate` | Grade work against done-criteria with calibrated skepticism |
| `/devlyn:clean` | Remove dead code, unused deps, complexity hotspots |

### UI Design Pipeline

| Step | Command | What It Does |
|---|---|---|
| 1 | `/devlyn:design-ui` | Generate 5 distinct style explorations |
| 2 | `/devlyn:design-system` | Extract design tokens from chosen style |
| 3 | `/devlyn:implement-ui` | Team builds it — component architect, UX, accessibility, responsive, visual QA |

> Use `/devlyn:team-design-ui` for step 1 with a full creative team.

### Planning & Docs

| Command | What It Does |
|---|---|
| `/devlyn:preflight` | Verify codebase matches vision/roadmap — gap analysis with evidence |
| `/devlyn:product-spec` | Generate or update product specs |
| `/devlyn:feature-spec` | Turn product spec → implementable feature spec |
| `/devlyn:discover-product` | Scan codebase → auto-generate product docs |
| `/devlyn:recommend-features` | Prioritize top 5 features to build next |
| `/devlyn:update-docs` | Sync all docs with current codebase |

---

## Auto-Activated Skills

These activate automatically — no commands needed. They shape how Claude thinks during relevant tasks.

| Skill | Activates During |
|---|---|
| `root-cause-analysis` | Debugging — enforces 5 Whys, evidence standards |
| `code-review-standards` | Reviews — severity framework, approval criteria |
| `ui-implementation-standards` | UI work — design fidelity, accessibility, responsiveness |
| `code-health-standards` | Maintenance — dead code prevention, complexity thresholds |
| `workflow-routing` | Any task — guides you to the right command |

---

## Optional Add-ons

Selected during install. Run `npx devlyn-cli` again to add more.

<details>
<summary><strong>Skills</strong> — copied to <code>.claude/skills/</code></summary>

| Skill | Description |
|---|---|
| `cloudflare-nextjs-setup` | Cloudflare Workers + Next.js with OpenNext |
| `generate-skill` | Create Claude Code skills following Anthropic best practices |
| `prompt-engineering` | Claude 4 prompt optimization |
| `better-auth-setup` | Better Auth + Hono + Drizzle + PostgreSQL |
| `pyx-scan` | Check if an AI agent skill is safe before installing |
| `dokkit` | Document template filling for DOCX/HWPX |
| `devlyn:pencil-pull` | Pull Pencil designs into code |
| `devlyn:pencil-push` | Push codebase UI to Pencil canvas |

</details>

<details>
<summary><strong>Community Packs</strong> — installed via <a href="https://github.com/anthropics/skills">skills CLI</a></summary>

| Pack | Description |
|---|---|
| `vercel-labs/agent-skills` | React, Next.js, React Native best practices |
| `supabase/agent-skills` | Supabase integration patterns |
| `coreyhaines31/marketingskills` | Marketing automation and content skills |
| `anthropics/skills` | Official Anthropic skill-creator with eval framework |
| `Leonxlnx/taste-skill` | Premium frontend design skills |

</details>

<details>
<summary><strong>MCP Servers</strong> — installed via <code>claude mcp add</code></summary>

| Server | Description |
|---|---|
| `codex-cli` | Codex MCP server — enables `--with-codex` dual-model mode |
| `playwright` | Playwright MCP — powers browser-validate Tier 2 |

</details>

> **Want to add a pack?** Open a PR adding it to the `OPTIONAL_ADDONS` array in [`bin/devlyn.js`](bin/devlyn.js).

---

## Requirements

- **Node.js 18+**
- **[Claude Code](https://docs.anthropic.com/en/docs/claude-code)** installed and configured

## Contributing

- **Add a command** — `.md` file in `config/commands/`
- **Add a skill** — directory in `config/skills/` with `SKILL.md`
- **Add optional skill** — add to `optional-skills/` and `OPTIONAL_ADDONS`
- **Suggest a pack** — PR to the pack list

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=fysoul17/devlyn-cli&type=Date)](https://star-history.com/#fysoul17/devlyn-cli&Date)

## License

[MIT](LICENSE) — Nocodecat @ Donut Studio
