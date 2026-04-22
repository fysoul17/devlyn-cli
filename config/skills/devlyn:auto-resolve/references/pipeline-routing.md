# Pipeline Routing — 3 Routes + 2-Stage Decision + Bypass Flag

Auto-resolve adapts its pipeline shape to each task. This file is the **single source of truth** for route selection and escalation. The orchestrator reads it; SKILL.md does not restate the rules inline.

## The 3 routes

| Route | Intended for | Phases that run |
|-------|-------------|-----------------|
| `fast` | Trivial / low-complexity, zero risk signals | PARSE → BUILD → BUILD GATE → [BROWSER if web] → EVAL → [FIX if findings] → FINAL REPORT |
| `standard` | Default for medium work | `fast` + SIMPLIFY (findings-only) + CHALLENGE (findings-only) + DOCS |
| `strict` | High-complexity OR risk signals present OR escalated | `standard` + team-assembled BUILD + REVIEW (findings-only) + SECURITY (mandatory, findings-only) + CLEAN (findings-only) + BUILD GATE strict mode |

Every route runs PARSE, BUILD, BUILD GATE, EVAL, and FINAL REPORT. Routes differ in which **polish** and **audit** phases run.

**Findings-only** means the phase emits a `.findings.jsonl` + `.log.md` but does not write code. The orchestrator routes any NEEDS_WORK/BLOCKED findings into the unified fix loop (see SKILL.md `PHASE 2.5: UNIFIED FIX LOOP`), which re-runs EVALUATE after the fix. This is how the post-EVAL invariant is enforced: all semantic changes go through EVAL.

## Default guardrails (route-invariant under `auto`)

These hold across all three routes with no `--bypass`:

1. **BUILD GATE PASS** — `fast` runs the gate too.
2. **Independent EVAL PASS** — file:line evidence required.
3. **Every criterion terminal** (`verified` or `failed`).
4. **Zero open HIGH/CRITICAL findings** at pipeline exit (subject to `--max-rounds` budget — see caveat below).
5. **Web file changes force BROWSER VALIDATE** (`.tsx/.jsx/.vue/.svelte/.css/.html`, `page.*/layout.*/route.*`).
6. **Post-BUILD risk detection auto-escalates** — see Stage B.

## The `--bypass` flag

Replaces five prior `--skip-*` flags and `--security-review skip`. Semantics: `--bypass <phase>[,<phase>...]`.

Bypassable phases: `build-gate`, `browser`, `simplify`, `review`, `challenge`, `security`, `clean`, `docs`.

Every bypass is recorded in `state.route.bypasses` and surfaced in the final report's `Guardrails bypassed:` line so the user sees exactly what they traded.

Examples:
- `--bypass build-gate` — bypasses guardrail #1. Warning: "CI/Docker may still reject this code."
- `--bypass browser` — bypasses guardrail #5 even if web files changed.
- `--bypass security` — bypasses strict-route's forced security review.
- `--bypass clean,docs` — same as `--bypass clean --bypass docs`. Both forms accepted.

**Backwards compatibility**: `--skip-review`, `--skip-clean`, `--skip-docs`, `--skip-browser`, `--skip-build-gate` continue to work as deprecated aliases for `--bypass review`, etc. `--security-review skip` is deprecated alias for `--bypass security`. On use, the orchestrator logs "deprecated flag — use `--bypass <phase>`" once and proceeds. Removed in next minor version.

## `--max-rounds` exhaustion

When the unified fix loop exhausts `max_rounds` with findings still open, behavior depends on the latest `triggered_by`:

| `triggered_by` | exhaustion behavior |
|---|---|
| `build_gate` | **halt** — code does not compile; skip EVAL/DOCS/etc. and go straight to FINAL REPORT with `BUILD GATE EXHAUSTED` warning. |
| `browser_validate` | **halt** — app does not render; skip to FINAL REPORT with `BROWSER EXHAUSTED` warning. |
| `evaluate` | **proceed_with_warning** — go to next phase; FINAL REPORT shows `EVAL EXHAUSTED` banner listing every open HIGH/CRITICAL finding. |
| `challenge` | **proceed_with_warning** — same as evaluate. |
| `simplify` | **proceed_with_warning**. |
| `review` | **proceed_with_warning**. |
| `security_review` | **proceed_with_warning** — findings listed in final report. |
| `clean` | **proceed_with_warning**. |

The caveat on guardrail #4 (no HIGH/CRITICAL at exit) is explicitly suspended under `_with_warning` exhaustion: the report's top banner shows what's unresolved so the user can decide.

## Two-stage decision

### Stage A — Pre-build, at PHASE 0 (post spec-preflight, pre BUILD spawn)

Decision order (first match wins, short-circuit):

1. **User override** (`--route fast|standard|strict`): set `route.selected`, `route.user_override: true`. Stage B will not run.
2. **Hard blocker**: missing spec file or unmet internal dependencies → halt before routing (BLOCKED).
3. **Fail-silent risk class**: grep source body (spec body for spec-driven, task description for generated) for `auth, login, session, token, secret, password, crypto, api, env, permission, access, database, migration, payment`. Any hit → `strict`. Reasons record which keywords matched.
4. **Complexity-based** (spec-driven only):
   - `spec.frontmatter.complexity == "high"` → `strict`
   - `spec.frontmatter.complexity == "medium"` → `standard`
   - `spec.frontmatter.complexity == "low"` → `fast`
5. **Generated tasks (no frontmatter)**: default to `standard` with reason `source.type=generated, Stage A defers complexity-based routing to Stage B post-BUILD`. BUILD writes `phases.build.complexity`; Stage B consults it.

Stage A writes to `state.route.stage_a.{at, reasons}`.

### Stage B — Post-BUILD, after PHASE 1.4 (BUILD GATE) completes

**Only escalates** (fast → standard → strict or standard → strict), never de-escalates. Rationale: adaptive routing should over-protect when signals are ambiguous; never remove guardrails once added.

**Does not run if `route.user_override == true`** — user's explicit choice wins.

Decision order (all signals evaluated; worst escalation wins):

1. **Risk keyword in diff content**: `git diff <base_ref.sha>` matches any of the 14 risk-class keywords → escalate to `strict`.
2. **Cross-boundary surface**: changed files span ≥3 top-level directories → escalate one tier.
3. **Diff size**: `>10` files OR `>400` lines changed → escalate one tier.
4. **API surface touched**: files under `src/api/`, `routes/`, `handlers/`, `app/api/` → escalate `fast → standard`.
5. **Tests absent for new code paths**: new source files in `src/` without corresponding test files → escalate `fast → standard`.
6. **BUILD GATE required strict mode** (`build_gate_strict_forced == true` because Stage A saw auth domain or high-complexity): flag in stage_b reasons but no additional escalation (already strict).

Stage B writes to `state.route.stage_b.{at, escalated_from, reasons}`. If no escalation fires, `stage_b.at` remains `null`.

## Phase inclusion matrix

| Phase | `fast` | `standard` | `strict` |
|-------|--------|-----------|----------|
| 0 PARSE + PREFLIGHT + ROUTE | ✓ | ✓ | ✓ |
| 1 BUILD (solo) | ✓ | ✓ | — (team) |
| 1 BUILD (team) | — | — | ✓ |
| 1.4 BUILD GATE (auto) | ✓ | ✓ | — (strict+docker) |
| 1.4 BUILD GATE (strict+docker) | — | — | ✓ |
| 1.5 BROWSER VALIDATE | ✓ (web) | ✓ (web) | ✓ (web) |
| 2 EVALUATE | ✓ | ✓ | ✓ |
| 2.5 UNIFIED FIX LOOP | ✓ (if findings) | ✓ (if findings) | ✓ (if findings) |
| 3 SIMPLIFY (findings-only) | — | ✓ | ✓ |
| 4 REVIEW team (findings-only) | — | — | ✓ |
| 4.5 CHALLENGE (findings-only) | — | ✓ | ✓ |
| 5 SECURITY REVIEW (findings-only) | — (unless Stage A/B escalated) | auto-detect | forced |
| 6 CLEAN (findings-only) | — | — | ✓ |
| 7 DOCS (doc-file mutations only) | — | ✓ | ✓ |
| 8 FINAL REPORT + ARCHIVE | ✓ | ✓ | ✓ |

Legend: ✓ runs, — skipped by route. `--bypass <phase>` forces skip on any route.

`fast` skips SIMPLIFY, REVIEW, CHALLENGE, SECURITY (unless escalated), CLEAN, DOCS.

## Terminal-state algorithm (PHASE 8)

The final verdict is computed from all findings files across the run, applying this precedence in order (first match wins):

1. **BUILD GATE FAIL** at exhaustion → `BLOCKED` with banner `BUILD GATE EXHAUSTED`.
2. **BROWSER VALIDATE BLOCKED** at exhaustion → `BLOCKED`.
3. **Any unresolved CRITICAL finding** in any `<phase>.findings.jsonl` → `BLOCKED`.
4. **Any unresolved HIGH finding** with `rule_id` prefix `correctness.*` or `security.*` → `NEEDS_WORK`.
5. **Any unresolved HIGH finding** (other categories) → `NEEDS_WORK`.
6. **Any unresolved MEDIUM finding** → `PASS_WITH_ISSUES`.
7. **Only LOW findings (or none)** → `PASS`.

"Unresolved" means `status == "open"` in the latest fix-loop round's findings file. `status == "resolved"` or `status == "suppressed"` are excluded.

The final report's top banner reflects this verdict. `Guardrails bypassed:` line lists `state.route.bypasses`. `Max-rounds exhaustion:` banner fires when `rounds.global >= max_rounds` and findings remain open.

## Non-goals

- Per-criterion routing (every phase sees every criterion).
- Route re-evaluation mid-round.
- De-escalation.
- Replacing `--bypass` flags (bypass remains; route is an overlay).
