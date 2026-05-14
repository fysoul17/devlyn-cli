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

That's it. The interactive installer handles everything. Claude Code config is installed by default; optional AI CLI instructions can be selected during install. Choose **Codex CLI (OpenAI)** to install `AGENTS.md` and the `devlyn:resolve`, `devlyn:ideate`, and `devlyn:design-ui` skills into `~/.codex/skills/`. In Codex, invoke them as skills with `$devlyn:resolve`, `$devlyn:ideate`, or `$devlyn:design-ui` rather than Claude Code slash commands. Run it again anytime to update.

---

## How It Works — Two Skills, Full Cycle

devlyn-cli turns Claude Code into a hands-free development pipeline. The pipeline surface is two skills, with `/devlyn:design-ui` installed as the required creative UI surface:

```
ideate (optional)  →  resolve  →  ship
```

Codex note: when the optional Codex install is selected, these workflows are installed as Codex skills. Use `$devlyn:ideate`, `$devlyn:resolve`, or `$devlyn:design-ui` in Codex; the `/devlyn:*` slash-command form is for Claude Code.

### Step 1 (optional) — Plan with `/devlyn:ideate`

Turn a raw idea into a verifiable spec — single-feature, multi-feature, or "normalize this external doc".

```
/devlyn:ideate "I want to build a habit tracking app with AI nudges"
```

Default mode produces a `docs/specs/<id>-<slug>/spec.md` plus `spec.expected.json` (mechanical verification block) that `/devlyn:resolve --spec` consumes directly. Modes:

| Mode | When to use |
|---|---|
| `default` | One feature, AI drives focused Q&A |
| `--quick` | One-line goal → assume-and-confirm spec, single-turn (autonomous-pipeline-safe) |
| `--from-spec <path>` | You already wrote a spec; ideate normalizes + lints it |
| `--project` | Multi-feature project: emits `plan.md` index + N child specs |

Skip ideate entirely if you have a spec or just want to describe the work — `/devlyn:resolve` accepts free-form goals too.

### Step 2 — Resolve with `/devlyn:resolve`

Hands-free pipeline for any coding task — bug fix, feature, refactor, debug, modify, PR review. Pass a spec, a free-form goal, or a diff to verify.

```
/devlyn:resolve "fix the login bug"                                # free-form
/devlyn:resolve --spec docs/specs/2026-05-04-auth/spec.md          # spec mode
/devlyn:resolve --verify-only <diff-or-PR-ref> --spec <path>       # verify-only
```

Internal phases run sequentially with file-based handoff via `.devlyn/pipeline.state.json`:

```
PLAN  →  IMPLEMENT  →  BUILD_GATE  →  CLEANUP  →  VERIFY (fresh subagent, findings-only)
```

- **PLAN** is the heaviest phase by design — formalizes invariants from the spec/goal and the file list to touch.
- **BUILD_GATE** runs your project's real compilers, typecheckers, linters, and `python3 .claude/skills/_shared/spec-verify-check.py` (verification commands literal-match). Auto-detects Next.js, Rust, Go, Solidity, Expo, Swift, and Dockerfiles. Browser flows route through Chrome MCP → Playwright → curl tier.
- **VERIFY** runs in a fresh subagent context with no code-mutation tools — findings only, structurally independent.
- Git checkpoints at every phase for safe rollback. Fix-loop budget shared across BUILD_GATE and VERIFY (`--max-rounds N`, default 4).

Common flags: `--engine claude|codex|auto` (default `claude`), `--bypass build-gate,cleanup`, `--pair-verify` (force pair-mode JUDGE in VERIFY), `--no-pair` (intentional solo VERIFY), `--risk-probes` / `--no-risk-probes`, `--perf` (per-phase timing).
`--pair-verify` and `--no-pair` are mutually exclusive; using both stops with `BLOCKED:invalid-flags`.

Free-form goals that ask for benchmark evidence, pair-evidence, risk-probe
measurement, `solo<pair` proof, or solo-headroom work must include an
actionable `solo-headroom hypothesis` naming the visible behavior `solo_claude`
is expected to miss plus a backticked observable command; the backticked line
itself must contain `miss` and be framed as the command/observable that exposes it. Without that,
`/devlyn:resolve` stops with `BLOCKED:solo-headroom-hypothesis-required` and
points you to `/devlyn:ideate` instead of inventing a weak hypothesis.
Free-form goals that add or run a new unmeasured benchmark, shadow fixture,
golden fixture, risk-probe, or pair-evidence candidate must also include
`solo ceiling avoidance`, mention `solo_claude`, and name the concrete
difference from rejected or solo-saturated controls such as `S2`-`S6`; without
that, `/devlyn:resolve` stops with `BLOCKED:solo-ceiling-avoidance-required`.

### Engine selection — Claude implementation, conditional pair VERIFY

`--engine claude` (default) is the canonical implementation surface for PLAN, IMPLEMENT, BUILD_GATE, and CLEANUP. VERIFY/JUDGE conditionally runs pair mode for verify-only runs, high-risk specs, risk probes, mechanical warnings, coverage gaps, or explicit `--pair-verify`.

`--engine codex` routes IMPLEMENT to Codex; `--engine auto` opts into the experimental dual-engine routing where applicable. Both are research-only at HEAD: iter-0020 closed Codex BUILD/IMPLEMENT below the quality floor on the 9-fixture suite (L2 vs L1 = −3.6, 3/8 gated fixtures cleared the +5 margin floor — release-readiness FAIL); iter-0033g + iter-0034 closed PLAN-pair as research-only with explicit unblock conditions (container/sandbox infra OR production telemetry capturing positive evidence of subagent introspection). Install the Codex CLI (https://platform.openai.com/docs/codex) and pass the flag explicitly to opt in:

```
/devlyn:resolve "fix the auth bug" --engine auto   # experimental, research-only
```

If Codex or Claude is absent when explicitly selected or conditionally required, the harness stops with `BLOCKED:codex-unavailable` or `BLOCKED:claude-unavailable` and prints setup guidance. Use `--no-pair` only when intentionally accepting solo VERIFY; use `--no-risk-probes` only when intentionally disabling automatic high-risk probes.

### Benchmark score runs

Use the benchmark CLI when a change claims `solo_claude < pair`. The score-focused runners print the run id, startup gate lines, blind-judge score tables, fixture pair margins, average pair margin, wall-time ratio, and failure reasons:

```bash
npx devlyn-cli benchmark headroom --min-fixtures 3 F16-cli-quote-tax-rules F23-cli-fulfillment-wave F25-cli-cart-promotion-rules
npx devlyn-cli benchmark recent
npx devlyn-cli benchmark recent --out-md /tmp/devlyn-recent-benchmark.md
npx devlyn-cli benchmark frontier --out-md /tmp/devlyn-pair-frontier.md
npx devlyn-cli benchmark audit --out-dir /tmp/devlyn-benchmark-audit
npx devlyn-cli benchmark audit-headroom --out-json /tmp/devlyn-headroom-audit.json
npx devlyn-cli benchmark pair --min-fixtures 3 --max-pair-solo-wall-ratio 3 F16-cli-quote-tax-rules F23-cli-fulfillment-wave F25-cli-cart-promotion-rules
```

`benchmark recent` prints a compact, wrap-safe snapshot of the current local
pair evidence: status counts, pair-lift aggregates, and one card per passing
pair-evidence fixture. It intentionally avoids wide Markdown tables, so the
same output stays readable in narrow terminals, PR comments, and release notes.
`benchmark frontier` also prints a stdout score summary for existing complete pair
evidence rows, including pair arm, trigger reasons, average/minimum pair margin,
and wall ratio, plus row-level verdicts even when `--out-json` or `--out-md`
writes an artifact. Markdown frontier artifacts include a `Triggers` column.
Full-pipeline pair gate artifacts record `require_hypothesis_trigger` in JSON
and include a Markdown `Hypothesis trigger` column, so strict regenerated
evidence shows whether each row carried `spec.solo_headroom_hypothesis`.
`benchmark audit` is the provider-free release/handoff guard: it writes
`audit.json` with the frontier summary, artifact map, and compact trigger-backed verdict-bearing `pair_evidence_rows`
(each row carries `pair_trigger_eligible: true`, non-empty `pair_trigger_reasons`, `pair_trigger_has_canonical_reason: true`, and `pair_trigger_has_hypothesis_reason`; the audit fails rows missing trigger reasons or missing actionable solo-headroom hypotheses in fixture `spec.md` whose observable command matches `expected.json`), runs the frontier with
`--fail-on-unmeasured`, requires at least four fixtures with passing pair evidence,
revalidates frontier `verdict: PASS`, zero unmeasured candidates, and revalidates `pair_mode: true`,
the default 5-point pair margin, and 3x pair/solo wall ratio, then
audits failed headroom results. The audit stdout also prints
`headroom_rejections=...`, `pair_evidence_quality=...`,
`pair_trigger_reasons=...`, `pair_evidence_hypotheses=...`, and
`pair_evidence_hypothesis_triggers=...` handoff rows, plus
`pair_trigger_historical_aliases=...` when archived evidence includes legacy
trigger aliases and `pair_evidence_hypothesis_trigger_gaps=...` when documented
hypotheses have not yet propagated into trigger reasons, with the rejected-fixture
coverage counts plus actual minimum pair margin, maximum pair/solo wall ratio,
and canonical trigger reason coverage plus row-match status.
The compact evidence row count must match the frontier evidence count,
`checks.frontier_stdout` records summary, aggregate, final-verdict, expected, printed score-row, trigger-visible row, and hypothesis-trigger-visible row counts,
`checks.headroom_rejections` records child verdict plus unrecorded/unsupported counts,
`checks.pair_evidence_quality` records the same quality thresholds from the compact rows,
`checks.pair_trigger_reasons` records canonical/historical-alias/exposed/total trigger-reason row counts, fixture-level historical alias details, summary count, and row-match status,
`checks.pair_evidence_hypotheses` records documented/total pair-evidence hypothesis row counts,
and `checks.pair_evidence_hypothesis_triggers` records whether documented hypotheses also appear as `spec.solo_headroom_hypothesis` trigger reasons plus fixture-level gap details
so incomplete or low-quality local score artifacts cannot inflate the claim.
Add `--require-hypothesis-trigger` to turn those hypothesis-trigger gaps from
archived-evidence WARN rows into release-blocking FAIL rows for newly
regenerated pair evidence.

```bash
npx devlyn-cli benchmark audit --require-hypothesis-trigger --out-dir /tmp/devlyn-benchmark-audit-strict
```

Historical trigger aliases are only reported for archived artifact review; new
current pair-evidence gates fail historical-only or unknown trigger reasons and
require at least one canonical `pair_trigger.reasons` entry.
`benchmark audit-headroom` fails if an active failed headroom fixture is missing
from both rejected registry and passing pair evidence.
Headroom runs use the current claim gate: `bare <= 60`, `solo_claude <= 80`,
and the default 5-point `bare`/`solo_claude` headroom margins before spending a pair arm.
Add `--dry-run` to either score runner to validate args, fixture ids, minimum
fixture count, and the replay command without running arms or judges. Dry-runs
and lint prove wiring only; real score claims must cite the run id and fixture
ids.

## Optional Power-User Skills

One creative companion skill lives in `optional-skills/` — install it via the interactive installer when you need it.

| Command | Use When |
|---|---|
| `/devlyn:design-system` | Extract exact design tokens (colors, type scale, spacing) from a chosen UI style |

> Earlier versions of devlyn-cli shipped 16+ skills (auto-resolve / preflight / evaluate / review / team-review / clean / update-docs / browser-validate / product-spec / feature-spec / recommend-features / discover-product / design-ui / implement-ui). Most were consolidated into `/devlyn:resolve` (which folds verification, review, and cleanup into its phases) plus `/devlyn:ideate` (which absorbs the planning surfaces) in the iter-0034 Phase 4 cutover (2026-05-04). `/devlyn:design-ui` is the required creative UI surface — on 2026-05-14 the optional `/devlyn:team-design-ui` was merged into it, so `/devlyn:design-ui` now always spawns a 5-specialist design team (Creative Director, Product Designer, Visual Designer, Interaction Designer, Accessibility Designer). Upgrades automatically remove the legacy skill directories from `~/.claude/skills/`.

---

## Auto-Activated Skills

These activate automatically — no commands needed. They shape how Claude thinks during relevant tasks.

| Skill | Activates During |
|---|---|
| `root-cause-analysis` | Debugging — enforces 5 Whys, evidence standards |
| `code-review-standards` | Reviews — severity framework, approval criteria |
| `ui-implementation-standards` | UI work — design fidelity, accessibility, responsiveness |
| `code-health-standards` | Maintenance — dead code prevention, complexity thresholds |

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
| `devlyn:reap` | Safely reap orphaned MCP / codex / Superset child processes |
| `devlyn:design-system` | Extract design tokens from a chosen UI style for exact reproduction |

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
| `playwright` | Playwright MCP — powers `/devlyn:resolve` BUILD_GATE browser tier (Chrome MCP → Playwright → curl fallback) |

> `--engine auto/codex` and conditional VERIFY pair mode use the local `codex` CLI binary, not MCP. Install from https://platform.openai.com/docs/codex, run the current Codex auth/login flow, verify `codex --version`, then rerun.

</details>

> **Want to add a pack?** Open a PR adding it to the `OPTIONAL_ADDONS` array in [`bin/devlyn.js`](bin/devlyn.js).

---

## Requirements

- **Node.js 18+**
- **[Claude Code](https://docs.anthropic.com/en/docs/claude-code)** installed and configured

## Contributing

- **Add a skill** — directory in `config/skills/` with `SKILL.md`
- **Add optional skill** — add to `optional-skills/` and `OPTIONAL_ADDONS` in [`bin/devlyn.js`](bin/devlyn.js)
- **Suggest a pack** — PR to the pack list

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=fysoul17/devlyn-cli&type=Date)](https://star-history.com/#fysoul17/devlyn-cli&Date)

## License

[MIT](LICENSE) — Nocodecat @ Donut Studio
