<div align="center">

<br />

<picture>
  <img alt="DEVLYN" src="assets/logo.svg" width="540" />
</picture>

### Context, Harness & Loop Engineering Toolkit for AI Coding Agents

**Structured prompts, agent orchestration, and automated pipelines — debugging, code review, product specs, and more.**

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

That's it. The installer asks two things:

1. **What** — `AGENTS.md — Codex · omp · Pi · Grok` (checked) and `CLAUDE.md — Claude Code` (checked when this project already has a devlyn Claude install). Space toggles, Enter confirms.
2. **Where** — `This project` (default) or `Global — every project on this machine`.

In a project, AGENTS.md readers load the skills from `.agents/skills/`; Claude Code loads only `.claude/skills/` and reads AGENTS.md when the project has no CLAUDE.md. Global installs skills only: `~/.agents/skills/` (omp, Pi, Grok) and `~/.codex/skills/` (Codex), plus `~/.claude/skills/` for Claude Code. Every target gets the `devlyn-resolve` and `devlyn-ideate` skills plus the `devlyn-engines` utility. In Codex / omp / Pi, invoke them as skills (`$devlyn-resolve`, `$devlyn-ideate`); in Claude Code and Grok they're slash commands (`/devlyn-resolve`). Rerunning refreshes skills and the managed instruction block while preserving project rules outside it. See [Migration from earlier versions](#migration-from-earlier-versions) for legacy migration and merge recovery.

Without prompts, `npx devlyn-cli -y` installs AGENTS.md + `.agents/skills/` plus every target this project already has; add `--claude` for Claude Code. With `--global` it installs for every project on this machine, plus `~/.claude/skills/` with `--claude` or when it already has a devlyn install.

---

## How It Works — Direct Work, Full Pipeline or Loop

devlyn-cli supports direct execution for clear, low-risk work with decisive checks, a full pipeline for work that needs it, and loops that split one intent into tasks agents drain without you:

```
inspect intent  →  direct work, full resolve or an ideate loop  →  ship
```

Non-Claude agents (Codex / omp / Pi / Grok): the AGENTS.md choice installs the workflows as their skills. In Codex / omp / Pi, use `$devlyn-ideate` or `$devlyn-resolve`; in Grok, use `/devlyn-ideate` or `/devlyn-resolve`, the same slash-command form as Claude Code.

### Plan and drain loops — `/devlyn-ideate`

Give ideate an intent or a document. It writes a loop package — a meta-prompt plus self-contained task contracts with mechanical acceptance — and agents drain the tasks one by one without you.

| Command | What it does |
|---|---|
| `/devlyn-ideate plan <intent or document>` | Inspects the project, asks only what it must, and writes a validated package to `docs/specs/<loop-id>/`. Nothing is queued or run. |
| `/devlyn-ideate add <intent or package>` | Plans when needed, then appends the package's tasks to `docs/specs/queue.md` in dependency order. |
| `/devlyn-ideate status` | Pending, active, accepted and failed counts; the next runnable task; delivery and recovery blockers. |
| `/devlyn-ideate drain` | Runs the queue serially and hands-free. |

A bare intent is planned and, when your request authorizes the work, added and drained without another confirmation; no arguments shows status. Questions come only when the answer changes behavior, scope, data semantics, acceptance or delivery, each with a recommended answer; `--autonomous` plans without them, taking only scope-narrowing, reversible, non-user-visible defaults. Each task runs in its own worktree with the executor pinned by `/devlyn-engines` (default: the CLI you opened) under your installed CLAUDE.md/AGENTS.md instructions. It is marked `[x]` only when its declared checks pass on its committed source and its required reviews cover it, never on the executor's say-so; a failed task becomes `[F]` with its reason and blocks only its dependents. An interrupted drain resumes without repeating accepted work. `--local-only` (or `--no-push`) keeps delivery local.

### Choose direct execution or `/devlyn-resolve`

Inspect the requested behavior, affected callers and tests first. Default to direct work when its scope and verification are tractable, including bounded multi-file changes; honor constraints and executor pins, run risk-proportionate checks and independent review for consequential changes, then review the diff and deliver. Automatically use full `/devlyn-resolve` only for concrete interacting requirements or verification too complex to manage reliably in the current context, such as coupled durable state, concurrent ownership and failure recovery. Domain labels, file count and a spec document alone do not trigger it. Investigate or clarify missing intent/access first. Explicit resolve (including small tasks) and explicit spec-mode workflows keep the full workflow below.

```
/devlyn-resolve "fix the login bug"                                # free-form
/devlyn-resolve --spec docs/specs/2026-05-04-auth/spec.md          # spec mode
/devlyn-resolve --verify-only <diff-or-PR-ref> --spec <path>       # verify-only
```

Internal phases run sequentially with file-based handoff via `.devlyn/pipeline.state.json`:

```
PLAN  →  IMPLEMENT  →  BUILD_GATE  →  CLEANUP  →  VERIFY (fresh subagent, findings-only)
```

- **PLAN** runs in the owner context and freezes requirements, verification and the authorized file surface before implementation.
- **BUILD_GATE** runs commands in the owner context without another model invocation, using your project's real compilers, typecheckers, linters, and `python3 .claude/skills/_shared/spec-verify-check.py` (verification commands literal-match). Auto-detects Next.js, Rust, Go, Solidity, Expo, Swift, and Dockerfiles. Browser flows route through Chrome MCP → Playwright → curl tier.
- **VERIFY** runs in a fresh subagent context with no code-mutation tools — findings only, structurally independent.
- Git checkpoints at every phase for safe rollback. Fix-loop budget shared across BUILD_GATE, CLEANUP and VERIFY (`--max-rounds N`, default 4).

Common flags: `--engine claude|codex|omp` (default: the orchestrator-supported default), `--role-config <path>` (one-run worker/judge profiles, see below), `--bypass build-gate,cleanup`, `--pair-verify` (force pair-mode JUDGE in VERIFY), `--no-pair` (intentional solo VERIFY), `--risk-probes` / `--no-risk-probes`, `--perf` (per-phase timing).
`--pair-verify` and `--no-pair` are mutually exclusive; using both stops with `BLOCKED:invalid-flags`.

Each task gets its own linked worktree; accepted tasks default to scoped commit → push → PR
→ merge when the repository allows it (otherwise the PR waits for a person). After the
PR merges, the worktree and branch its session released are cleaned; anything in use is
kept. Set `git config --local devlyn.completionMode pr` to stop at the PR; `task-complete.py complete --mode auto|pr`
overrides one task. Local-only/no-push instructions take precedence; existing
branches cannot be adopted. Full runs require successful archive before delivery;
direct tasks use their actual checks and root acceptance. Verify-only never
publishes. Pending checks or unsupported merge policy retain resources and
report a receipt-based resume command separately from product verification.
See [task completion](config/skills/_shared/task-completion.md)
for allocation, acceptance, writer cessation and recovery.

### Engine roles — auto-detected, pinnable with `/devlyn-engines`

devlyn separates three engine roles:

- **Orchestrator** — the CLI you opened (Claude Code, Codex, or omp) that drives the conversation and loop. The contract is symmetric (`CLAUDE.md` ↔ `AGENTS.md`), so the same phase-gated pipeline runs whichever you launch; the file artifacts (spec, queue, state) carry over if you switch.
- **Executor** (legacy) — the worker for IMPLEMENT, its included code/doc cleanup, and their repair rounds, and the primary VERIFY judge, unless either is separately profiled (below). Defaults to the orchestrator-supported default. PLAN is orchestrator-fixed and never inherits `--engine` or an executor pin. An absent primary profile follows the legacy executor, not an opt-in worker profile.
- **Pair judge** — the first available *other* engine, default for VERIFY and conditional for risk probes.

`--engine <name>` sets the legacy executor for one run as an engine-only entry (it clears any lower-precedence profile's model/effort). PLAN stays in the owner context; BUILD_GATE/CLEANUP run owner commands; risk-probe derivation keeps its existing route. VERIFY/JUDGE runs pair mode by default when the OTHER engine is available.

Pin roles durably with `/devlyn-engines` (no args shows the role table + detected engines; `executor <name>` / `pair <name>,...` / `role <worker|primary_judge|pair_judge> <JSON object>` / `role <name> clear` manage the pins, stored machine-local in `.devlyn/engines.json`; `clear` removes all legacy and role pins, preserves unrelated keys, and deletes an empty file). Pins fail closed: an unavailable pinned engine stops with `BLOCKED:<engine>-unavailable`, and a name with no `_shared/adapters/<name>.md` adapter stops with `BLOCKED:invalid-engine-config`. New engines plug in by shipping an adapter file — no skill changes.

#### Explicit worker and judge profiles

`.devlyn/engines.json` may add a `roles` object with `worker`, `primary_judge`, and `pair_judge` entries. Each entry requires `engine` and accepts an optional exact `model` ID and `effort`; unknown fields, aliases (`default`, `auto`, `opus`, `sonnet`, `fable`, `codex` as a model), null/empty values, and duplicate keys stop with `BLOCKED:invalid-engine-config`. Only the project's own `.devlyn/engines.json` is read — no parent or global lookup. Example (an example, not a default or ranking):

```json
{
  "executor": "codex",
  "pair_judge_priority": ["claude"],
  "roles": {
    "worker": {"engine": "codex", "model": "gpt-6-astra", "effort": "xhigh"},
    "primary_judge": {"engine": "codex", "model": "gpt-6-astra", "effort": "high"},
    "pair_judge": {"engine": "claude", "model": "claude-fable-5-1", "effort": "medium"}
  }
}
```

`--role-config <path>` supplies the same `{"roles": {...}}` object for one run only, with no other top-level keys; the flag may appear once.

- **Precedence** — an entry replaces the lower one as a whole; model/effort never merge across engines. Worker and primary judge: run `--role-config` entry > `--engine` (engine-only) > project role entry > legacy executor/default. Pair judge: run entry > project entry > `pair_judge_priority` / the OTHER-engine complement. A missing `model`/`effort` keeps that route's current default and is shown as inherited/unresolved.
- **Boundaries** — `worker` covers IMPLEMENT, its included code/doc cleanup, and their repair rounds; `primary_judge` and `pair_judge` cover VERIFY only. PLAN stays orchestrator-fixed, BUILD_GATE/CLEANUP run owner commands, and risk-probe derivation stays outside these controls. OTHER must differ from the primary by engine: an explicit same-engine pair is `BLOCKED:invalid-engine-config`. `--no-pair` is unchanged — explicit solo VERIFY; an unused pair entry is neither dispatched nor availability-checked.
- **Initial explicit routes** — Codex worker/primary/pair accept exact `model` + `effort` (dispatched as `-m` / `-c model_reasoning_effort=`, validated against the installed Codex CLI's native model metadata for its version). Claude primary/pair judges pass an exact `model` as `--model` and validate native result identity; model-only selection needs no source update for a new ID. Explicit `effort` separately requires the adapter's version/model support declaration. The Claude worker stays the native `Agent` route and is engine-only: explicit `model`/`effort` on a Claude worker is `BLOCKED:unsupported-role-option` — a supported-route boundary, not a claim that Claude cannot implement. Other adapters (omp, grok) are engine-only for their eligible roles.
- **Errors** — `BLOCKED:unsupported-role-option` names the role, engine and field with guidance; there is no clamp, fallback, substituted model, or weaker retry. An explicitly selected engine (flag, pin, or profile) that is unavailable stops with `BLOCKED:<engine>-unavailable`. A native warning that a requested option was ignored is a failed promise even at exit 0.
- **Requested vs observed** — `/devlyn-engines` status prints each role's requested engine/model/effort, source and dispatch channel before dispatch; it describes a request and does not prove a native invocation happened. Effective model is reported only with native evidence; a Codex worker receipt binds requested dispatch and leaves effective model unknown. A reported worker model reroute blocks completion even at exit 0. SURFACE_CLOSE inherits native Claude model settings and records the model from its required JSON result. Effective effort stays unknown unless native evidence establishes it — invocation arguments prove dispatch, not provider-internal reasoning.

`--engine codex` routes IMPLEMENT and its included code/doc cleanup to Codex as a supported engine-only route (exact model/effort via the profiles above). Historical record: iter-0020 closed Codex BUILD/IMPLEMENT below the quality floor on the 9-fixture suite (L2 vs L1 = −3.6, 3/8 gated fixtures cleared the +5 margin floor — release-readiness FAIL). Separately, PLAN-pair remains research-only: iter-0033g + iter-0034 closed it with explicit unblock conditions (container/sandbox infra OR production telemetry capturing positive evidence of subagent introspection). Install the Codex CLI (https://platform.openai.com/docs/codex) and pass the flag explicitly to opt in:

```
/devlyn-resolve "fix the auth bug" --engine codex
```

If an engine is absent when explicitly selected by flag, pin, or role profile, or OTHER engine is absent under `--pair-verify`, the harness stops with `BLOCKED:<engine>-unavailable` and prints setup guidance. Automatic VERIFY absence is a reported solo route. Use `--no-pair` only when intentionally accepting solo VERIFY; use `--no-risk-probes` only when intentionally disabling automatic high-risk probes.

### Migration from earlier versions

Reinstall with the new version to refresh instructions and skills for the selected
targets. Claude uses `CLAUDE.md`; Codex, Grok, omp and Pi share `AGENTS.md`.
Devlyn updates its checksum-marked instruction block and preserves project-specific
rules outside it. Keep custom rules outside the block; they take precedence over
its defaults. Exact pre-update backups are saved in `.devlyn/instructions/`.
When recovery is needed, pre-existing symlinks or non-directory entries at `.devlyn/` or
`.devlyn/instructions/` stop installation without replacing the instruction file.

Older and mixed-version templates migrate automatically. Within recognizable
Devlyn sections, exact historical paragraphs and list items are replaced;
modified or unknown text and its headings are preserved outside the new block.
Edits inside an existing managed block are preserved outside it too. Plain custom
files and rules outside managed blocks retain their contents. Unknown old text
is kept conservatively, even when it may contain obsolete defaults.
Malformed or duplicate managed markers still stop with an exact `.backup`, new
defaults in `.incoming`, and a `.merge.md` guide; the original remains unchanged.
Release packaging refreshes the offline fingerprints from Git history using
`node scripts/update-instruction-templates.js`; installation needs no Git or network.
Use 3.1.3 or newer consistently: older installers still overwrite `CLAUDE.md`.

Upgrading to 4.1.0: `npx devlyn-cli -y` in a 4.x project keeps its Claude Code install
current and adds `AGENTS.md` + `.agents/skills/`. Earlier releases put the Codex, omp, Pi
and Grok skills in `~/.codex/skills`, `~/.agents/skills` and `~/.grok/skills`; a project
install no longer refreshes them and names each one it finds. Refresh them with `--global`
or delete them; delete `~/.grok/skills`, since Grok now reads `~/.agents/skills`.
`npx devlyn-cli agents` was removed.

<!-- legacy-surface-map:begin — retired command names below are documented as OLD, not current; lint Check 10c skips this block -->
Upgrading to 4.0.0: every devlyn skill is renamed to the Agent Skills standard
(`/devlyn:resolve` → `/devlyn-resolve`; the full list is in the table below). Run the
installer in each project that has devlyn (`npx devlyn-cli`, or `-y` with `--claude` and
`--global` as needed): each run removes the old folders
where it installs and keeps an optional skill you had under its new name. A 3.x installer run
afterwards brings the old `devlyn:*` folders back beside some new ones and drops opted-in
pencil skills; run the 4.x installer again to repair it, and re-add those pencil skills from
its menu. An agent setting that disables a
devlyn skill by its old name or path (for example Codex `[[skills.config]]` or omp
`disabledExtensions`) needs the new name. A project that committed the old `devlyn:*`
folders checks out on Windows once that re-sync is committed.

Earlier versions of devlyn-cli shipped 16+ slash commands. The iter-0034 Phase 4 cutover (2026-05-04) and the 2026-05-14 follow-up consolidated them down to the three current commands, and 4.0.0 renamed every devlyn skill to the Agent Skills naming standard (`devlyn-<name>`: lowercase, digits and hyphens, the same as its folder). Upgrades automatically purge the legacy skill directories.

| Old command | Now use |
|---|---|
| `/devlyn:auto-resolve`, `/devlyn:preflight`, `/devlyn:evaluate`, `/devlyn:review`, `/devlyn:team-resolve`, `/devlyn:team-review`, `/devlyn:clean`, `/devlyn:update-docs`, `/devlyn:browser-validate`, `/devlyn:implement-ui` | `/devlyn-resolve` (folds them into PLAN → IMPLEMENT → BUILD_GATE → CLEANUP → VERIFY) |
| `/devlyn:product-spec`, `/devlyn:feature-spec`, `/devlyn:recommend-features`, `/devlyn:discover-product` | `/devlyn-ideate` |
| `/devlyn:design-system` | Removed 2026-05-14 — no replacement |
| `/devlyn:resolve`, `/devlyn:ideate`, `/devlyn:engines`, `devlyn:pencil-pull`, `devlyn:pencil-push`, `devlyn:reap` (3.x and earlier) | `/devlyn-resolve`, `/devlyn-ideate`, `/devlyn-engines`, `devlyn-pencil-pull`, `devlyn-pencil-push`, `devlyn-reap` (4.0.0) |
| `/devlyn:queue` (3.x and earlier), `/devlyn-queue` (4.0.0–4.1.0) | `/devlyn-ideate add`, `status` and `drain` |
| `/devlyn-ideate --quick`, `--from-spec`, `--project` (4.1.0 and earlier) | `/devlyn-ideate plan`; `--autonomous` replaces `--quick` |
| `/devlyn:team-design-ui`, `/devlyn:design-ui` (3.x and earlier), `/devlyn-design-ui` (4.0.0–4.1.0) | Retired — no replacement |
<!-- legacy-surface-map:end -->

---

## Optional Add-ons

Selected during install. Run `npx devlyn-cli` again to add more.

<details>
<summary><strong>Skills</strong> — copied into every skill root the install writes</summary>

| Skill | Description |
|---|---|
| `asset-creator` | AI pixel art game asset pipeline — generate, chroma-key, catalog |
| `cloudflare-nextjs-setup` | Cloudflare Workers + Next.js with OpenNext |
| `generate-skill` | Create Claude Code skills following Anthropic best practices |
| `prompt-engineering` | Claude prompt optimization |
| `better-auth-setup` | Better Auth + Hono + Drizzle + PostgreSQL |
| `pyx-scan` | Check if an AI agent skill is safe before installing |
| `dokkit` | Document template filling for DOCX/HWPX |
| `devlyn-pencil-pull` | Pull Pencil designs into code |
| `devlyn-pencil-push` | Push codebase UI to Pencil canvas |
| `devlyn-reap` | Safely reap orphaned MCP / codex / Superset child processes |
| `code-health-standards` | Maintainability standards — dead code, dependencies, complexity, naming |
| `code-review-standards` | Severity framework and approval criteria for reviews |
| `root-cause-analysis` | Evidence-first why-chain debugging |
| `ui-implementation-standards` | UI quality bar — design tokens, accessibility, state coverage, responsive layout |

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
<summary><strong>MCP Servers</strong> — installed via <code>claude mcp add</code>, offered with the CLAUDE.md choice</summary>

| Server | Description |
|---|---|
| `playwright` | Playwright MCP — powers `/devlyn-resolve` BUILD_GATE browser tier (Chrome MCP → Playwright → curl fallback) |

> `--engine codex` and default-when-available VERIFY pair mode use the local `codex` CLI binary, not MCP. Install from https://platform.openai.com/docs/codex, run the current Codex auth/login flow, verify `codex --version`, then rerun.

</details>

> **Want to add a pack?** Open a PR adding it to the `OPTIONAL_ADDONS` array in [`bin/devlyn.js`](bin/devlyn.js).

---

## Requirements

- **Node.js 18+** and npm
- **Python 3.11+** available as `python3`, and Git for the harness
- **An agent CLI** installed and configured: Codex, omp, Pi or Grok (AGENTS.md), or [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (CLAUDE.md)

On native Windows, use native Node/npm and Python plus Git for Windows Bash for the shipped shell wrapper. Run `npx devlyn-cli -y` in the project (add `--claude` for Claude Code). Skill folders follow the Agent Skills naming standard (for example `devlyn-resolve`), so a project that commits them checks out on Windows. Harness text is UTF-8 without requiring `PYTHONUTF8`.

Windows completion preserves the workspace, owned refs and recovery receipt when writer cessation cannot be proved, even after merge; resume guidance and delivery status remain separate from product verification. The portability workflow checks out the repository on native Windows and tests the POSIX-packed npm artifact there. A POSIX pass alone does not establish Windows support: acceptance requires the passing Windows job for the exact source SHA/artifact hashes.

## Contributing

- **Add a skill** — directory in `config/skills/` with `SKILL.md`
- **Add optional skill** — add to `optional-skills/` and `OPTIONAL_ADDONS` in [`bin/devlyn.js`](bin/devlyn.js)
- **Suggest a pack** — PR to the pack list

## Supercharge it — pair devlyn with persistent agent memory

devlyn-cli gives your agent a world-class **harness**. Give it a world-class **memory** and the loop compounds — decisions, corrections, and hard-won context survive across sessions instead of resetting every conversation.

> [!TIP]
> ### 🧠 [pyx-memory](https://memory.pyxmate.com) — world-class agentic memory (hybrid RAG) for coding agents
> Durable facts, corrections, and project state your agent recalls and reinforces — so every run starts smarter than the last. → **[memory.pyxmate.com](https://memory.pyxmate.com)**

- **Remembers across sessions** — decisions, gotchas, preferences, and project state, not just this conversation
- **Hybrid retrieval** — semantic *and* graph recall: find by meaning *and* by relationship
- **Learns the loop** — reinforces what works, records corrections when it doesn't

**Harness (devlyn) + Memory (pyx-memory) = agents that don't just execute — they improve.** Wire up **pyx-memory** as an MCP server and `/devlyn-resolve` recalls prior decisions before it plans and stores what it learns after it ships.

## Support & Attribution

devlyn-cli is built and maintained in the open. If it earns a place in your workflow, two small things keep it alive and help others find it:

- ⭐️ **Star the repo** — [give it a star](https://github.com/fysoul17/devlyn-cli) if it saved you time. It's the single biggest signal that keeps the project going.
- 🔗 **Leave a credit** — if devlyn-cli helped ship your project, a small attribution is genuinely appreciated (kindly requested, never required — the MIT license asks nothing of you here). Drop this badge in your README:

  ```md
  [![Built with devlyn-cli](https://img.shields.io/badge/built%20with-devlyn--cli-blueviolet)](https://github.com/fysoul17/devlyn-cli)
  ```

  Renders as [![Built with devlyn-cli](https://img.shields.io/badge/built%20with-devlyn--cli-blueviolet)](https://github.com/fysoul17/devlyn-cli)

Thank you for using devlyn — it genuinely means a lot. 🙏

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=fysoul17/devlyn-cli&type=Date)](https://star-history.com/#fysoul17/devlyn-cli&Date)

## License

[MIT](LICENSE) — Nocodecat @ Donut Studio
