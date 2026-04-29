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

### Engine selection — Claude solo by default

`--engine claude` (default) is the canonical user-facing surface. The pipeline runs entirely on Claude — every phase and team role.

`--engine auto` opts into the experimental dual-engine path (Codex builds, Claude evaluates, GAN dynamic). It is currently below the quality floor on the 9-fixture benchmark suite — pair-mode regressed L2 vs L1 by an average of 3.6 points, and 3 of 8 gated fixtures cleared the +5 margin floor (release-readiness FAIL). See [`autoresearch/iterations/0020-pair-policy-narrow.md`](autoresearch/iterations/0020-pair-policy-narrow.md) for the data. Install the Codex CLI (https://platform.openai.com/docs/codex) and pass the flag explicitly to opt in:

```
/devlyn:auto-resolve "fix the auth bug" --engine auto   # experimental, research-only
```

If Codex is absent when `--engine auto` is requested, the harness silently downgrades to `--engine claude` and emits a banner in the final report.

<details>
<summary><strong>What's new in 1.14.0</strong> — CPO lens + handoff enforcement</summary>

`/devlyn:ideate` now thinks like a world-class Product Owner, and `/devlyn:auto-resolve` finally honors the spec contract the ideate skill was already designed to produce. Validated with 19 parallel eval subagents, 1.2M tokens of evidence — Customer Frame propagation went from 0/20 to 20/20 across seven test scenarios.

- **Jobs-to-be-Done forcing in FRAME** — ideate's opening FRAME phase now requires a one-sentence JTBD statement ("When [situation], [user] wants [motivation] so they can [outcome]") before anything else. A bare problem statement is a state description, not a job — downstream specs built without this frame describe system behavior instead of customer progress.
- **Customer Frame field on every item spec** — item-spec template gains a `## Customer Frame` section between Context and Objective that carries the per-item JTBD sentence all the way through to auto-resolve's build agent. The build agent uses this line to resolve ambiguity in Requirements rather than inventing interpretations.
- **PHASE 0.5 SPEC PREFLIGHT on auto-resolve** — when the task names a `docs/roadmap/phase-N/...md` spec, auto-resolve now reads it BEFORE BUILD, verifies internal dependencies are `status: done`, and writes `.devlyn/SPEC-CONTEXT.md` so downstream phases stop re-deriving what the spec already owns. Un-done deps halt the pipeline with `BLOCKED` rather than shipping out-of-sequence code.
- **Done-criteria verbatim copy** — when PHASE 0.5 found a spec, BUILD's Phase B copies the spec's `Requirements`, `Out of Scope`, and `Verification` sections verbatim into `.devlyn/done-criteria.md`. No silent re-derivation; the ideate CHALLENGE rubric's validation is preserved through the handoff.
- **Spec-bounded exploration** — BUILD's Phase A uses the spec's `Architecture Notes` + `Dependencies` as the exploration boundary instead of re-classifying the task type open-endedly.
- **Complexity-gated team ceremony** — `complexity: low` specs with no security/auth/API/data risk keywords skip TeamCreate entirely. Medium/high complexity or risk-flagged specs still assemble the team as before.
- **Evidence discipline in ideate EXPLORE** — research phase now labels unsourced market/tech claims `[UNVERIFIED]` inline rather than presenting recall as fact. The CHALLENGE rubric's NO GUESSWORK axis fires on unlabeled authoritative claims.
- **Mode tie-break rule** — when a request matches two ideate modes (Quick Add vs Expand, Research-first vs Deep-dive), the narrowest mode wins. Deterministic selection replaces intuitive match.
- **Bloat removal** — three redundant motivational blocks deleted from ideate SKILL.md (`<why_this_matters>` rationale, duplicate CHALLENGE preamble, external engine-routing pointer). SKILL.md shrank from 529 to 519 lines despite the new features.

</details>

<details>
<summary><strong>What's new in 1.13.0</strong> — Opus 4.7 pipeline pass</summary>

Core pipeline skills (`ideate`, `auto-resolve`, `preflight`) rewritten against Anthropic's Opus 4.7 prompting guidance, validated by multi-round comprehension and quality-grading subagents.

- **4.7 prompt patterns** — `<investigate_before_answering>` on evaluator and challenge, `<coverage_over_filtering>` with per-finding confidence, 3 few-shot examples in the Challenge phase, `<orchestrator_context>` (auto-compaction + xhigh effort), `<use_parallel_tool_calls>` in ideate EXPLORE and preflight Phase 0.
- **`--with-codex` consolidated into `--engine auto`** — auto covers BUILD/FIX + team roles + ideate CHALLENGE critic. Legacy flag still accepted with a graceful handoff. *(Note: post iter-0020 close-out, `--engine auto` is experimental research-only; default is `--engine claude`.)*
- **Bug fixes** — PHASE 1.5 BLOCKED browser failures re-route correctly via PHASE 2.5; PHASE 1.4-fix and PHASE 2.5 share one global round counter; preflight PHASE 1 numbering fixed; build-gate-exhausted now produces a graceful final report.
- **CLAUDE.md refresh** (shipped to `npx` installers) — Quick Start pointing to ideate → auto-resolve → preflight, Context Window Management updated for Opus 4.7 auto-compaction, terminology refresh (TodoWrite → task tools, Task agents → Agent subagents).

</details>

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
| `asset-creator` | AI pixel art game asset pipeline — generate, chroma-key, catalog |
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
| `playwright` | Playwright MCP — powers browser-validate Tier 2 |

> `--engine auto/codex` uses the local `codex` CLI binary, not MCP. Install from https://platform.openai.com/docs/codex; the harness silently downgrades to `--engine claude` if the CLI is missing.

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
