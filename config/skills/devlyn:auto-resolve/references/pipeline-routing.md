# Pipeline Routing — 3 Routes + 2-Stage Decision

Auto-resolve adapts its pipeline shape to each task. The 11-phase pipeline is not one-size-fits-all: a typo fix and a cross-boundary auth rewrite need different process intensity. This file defines how the orchestrator picks the right shape.

## The 3 routes

| Route | Intended for | Phases that run |
|-------|-------------|-----------------|
| `fast` | Trivial / low-complexity, zero risk signals | PHASE 0 → 0.5 → 1 → 1.4 → 1.5 (if web) → 2 → 2.5 (if findings) → 8 |
| `standard` | Default for medium work | `fast` + 3 (simplify) + 4.5 (challenge) + 7 (docs) |
| `strict` | High-complexity OR risk signals present OR escalated from below | `standard` + 1 (team assembly in BUILD) + 4 (review team) + 5 (security mandatory) + 6 (clean) + BUILD GATE strict mode |

Phase numbers reference `SKILL.md`. Every route runs PHASES 0, 0.5, 1, 1.4, 2, 2.5 (conditional on findings), and 8. The routes differ in which *polish* and *audit* phases are appended.

### Default guardrails (route-invariant under `auto` mode)

These six are the pipeline's default quality floor — they hold across all three routes under `--route auto` with no user `--skip-*` flags:

1. **BUILD GATE PASS** — `fast` runs the gate too; `fast` does not compile warnings away.
2. **Independent EVALUATE PASS** — file:line evidence required for every verdict.
3. **Every criterion reaches a terminal state** (`verified` or `failed`) — no pipeline exits with dangling `pending` or `implemented` criteria.
4. **Zero open HIGH/CRITICAL findings** at pipeline exit (assuming max-rounds budget is sufficient — see caveat below).
5. **Web file changes force BROWSER VALIDATE** (`.tsx/.jsx/.vue/.svelte/.css/.html`, `page.*/layout.*/route.*`).
6. **Post-BUILD risk detection auto-escalates** — see Stage B below.

`fast` does not mean "cut corners". It means "skip phases that aren't needed for work of this shape". Quality stays high in any route — provided the user does not opt out via flag.

### Guardrails the user can override (with warning)

The following flags explicitly bypass default guardrails. User intent is supreme, but the bypass is loud:

- `--skip-build-gate` — bypasses guardrail #1. Pipeline warns: "Build gate skipped by user flag; CI/Docker may still reject this code."
- `--skip-browser` — bypasses guardrail #5 even if web files changed.
- `--security-review skip` — bypasses strict-route's forced security review.
- `--max-rounds N` with `N` exhausted before findings drain — caveat on guardrail #4: the pipeline halts the fix loop and proceeds to subsequent phases with unresolved findings listed in the final report. This is the only sanctioned path under which HIGH/CRITICAL findings can reach the user — reported with a prominent BUILD GATE EXHAUSTED or EVAL EXHAUSTED warning at the top of the final report.

When these overrides fire, the final report shows `Route: X (guardrails bypassed: <list>)` so the user sees exactly what they traded away.

## Two-stage decision

Routing happens in two stages because signals that matter arrive at two different times.

### Stage A — Pre-build, at PHASE 0.5

Signals available before BUILD runs: spec frontmatter, spec body content, user flags.

Decision order (first match wins, short-circuit):

1. **User override** (`--route fast|standard|strict`): set `route.selected` to that value; `route.user_override: true`; Stage A reasons include `"user explicit override"`. Stage B will not run (user knows best — respect the intent).
2. **Hard blocker**: missing spec file or unmet internal dependencies → halt before routing (BLOCKED, per PHASE 0.5 existing rules).
3. **Fail-silent risk class**: grep the source (spec body for spec-driven, task description for generated) for `auth, login, session, token, secret, password, crypto, api, env, permission, access, database, migration, payment`. Any hit → `strict`. Reasons record which keywords matched.
4. **Complexity-based** (spec-driven runs only):
   - `spec.frontmatter.complexity == "high"` → `strict`
   - `spec.frontmatter.complexity == "medium"` → `standard`
   - `spec.frontmatter.complexity == "low"` → `fast`
5. **Generated tasks (no frontmatter)**: Stage A defaults to `standard` with reason `"source.type=generated, complexity deferred to BUILD"`. BUILD writes `phases.build.complexity` and Stage B consults it.

Stage A writes to `pipeline.state.json.route.stage_a`:

```json
{
  "at": "2026-04-22T13:11:04Z",
  "reasons": ["spec.complexity = medium", "0 risk-signal hits in spec sections", "1 internal dep verified done"]
}
```

### Stage B — Post-BUILD, after PHASE 1.4 (BUILD GATE) completes

Signals available after BUILD runs: actual `git diff` surface, what BUILD classified complexity as (for generated runs), BUILD GATE verdict, whether tests were added.

**Stage B can only escalate** (`fast → standard → strict` or `standard → strict`), never de-escalate. Rationale: adaptive routing should over-protect when signals are ambiguous; never remove guardrails once added.

**Stage B does not run if `route.user_override: true`.** The user's explicit choice is respected.

Decision order (all signals evaluated; worst escalation wins):

1. **Risk keyword in diff content** (not just spec body): `git diff <base_ref.sha>` for any of the 14 risk-class keywords → escalate to `strict`
2. **Cross-boundary surface**: changed files span multiple top-level directories in a way the spec didn't declare (e.g., both `app/` and `src/api/` and `migrations/`) → escalate current route one tier
3. **Diff size**: `>10` files changed OR `>400` lines changed → escalate current route one tier (BUILD may have done more than the spec implied)
4. **API surface touched**: any file under `src/api/`, `routes/`, `handlers/`, `app/api/` → escalate `fast → standard` (no effect at `standard` or `strict`)
5. **Tests absent for new code paths**: new source files in `src/` without corresponding test files → escalate `fast → standard`
6. **BUILD GATE required strict mode**: if `build_gate_strict_forced == true` (spec high-complexity or auth domain) and the gate ran in auto mode → flag in stage_b reasons but do not escalate further (already strict from Stage A)

Stage B writes to `pipeline.state.json.route.stage_b`:

```json
{
  "at": "2026-04-22T13:32:18Z",
  "escalated_from": "fast",
  "reasons": ["diff_files=14 > threshold=10", "api surface touched: src/api/user/avatar.ts", "no test file for src/api/user/avatar.ts"]
}
```

If no escalation fires, `stage_b.at` remains `null` and `stage_b.reasons` stays empty.

## Phase inclusion matrix

Each optional phase checks `state.route.selected` at its own "should I run?" step. User `--skip-*` flags override the route decision (user intent is supreme).

| Phase | `fast` | `standard` | `strict` |
|-------|--------|-----------|----------|
| 0 PARSE INPUT | ✓ | ✓ | ✓ |
| 0.5 SPEC PREFLIGHT | ✓ | ✓ | ✓ |
| 1 BUILD (solo) | ✓ | ✓ | — (uses team) |
| 1 BUILD (team) | — | — | ✓ |
| 1.4 BUILD GATE (auto) | ✓ | ✓ | — (uses strict+docker) |
| 1.4 BUILD GATE (strict+docker) | — | — | ✓ |
| 1.4-fix (fix loop) | ✓ (conditional) | ✓ (conditional) | ✓ (conditional) |
| 1.5 BROWSER VALIDATE | ✓ (web files) | ✓ (web files) | ✓ (web files) |
| 2 EVALUATE | ✓ | ✓ | ✓ |
| 2.5 FIX LOOP | ✓ (conditional) | ✓ (conditional) | ✓ (conditional) |
| 3 SIMPLIFY | — | ✓ | ✓ |
| 4 REVIEW (team) | — | — | ✓ |
| 4.5 CHALLENGE | — | ✓ | ✓ |
| 5 SECURITY REVIEW | — (Stage A/B would have escalated if risk detected) | auto-detect | forced run |
| 6 CLEAN | — | — | ✓ |
| 7 DOCS | — | ✓ | ✓ |
| 8 FINAL REPORT | ✓ | ✓ | ✓ |

Legend: ✓ runs, — skipped (by route), "conditional" runs only if prior phase emitted findings.

`fast` skips 6 optional phases: SIMPLIFY, REVIEW, CHALLENGE, SECURITY (unless risk keyword triggered Stage A escalation to strict), CLEAN, DOCS.

## Interaction with `--skip-*` and `--security-review` flags

User flags always override the route decision. Specifically:

- `--skip-browser` forces skip even if web files changed (user's responsibility)
- `--skip-review`, `--skip-clean`, `--skip-docs` force skip even on `strict`
- `--skip-build-gate` forces skip on all routes (against route intent — warn loudly)
- `--security-review skip` forces skip even on `strict`; `--security-review always` forces run on `fast`
- `--build-gate strict` forces strict mode on all routes (additive, not destructive)

The route provides the default; flags provide explicit user intent. When they conflict, the user wins.

## Transparency in the final report

The PHASE 8 final report surfaces routing decisions so the user can audit and override next time:

```
Route: standard (user_override: false)
Stage A reasons: spec.complexity=medium, 0 risk-signal hits
Stage B: (no escalation)
Phases skipped by route: review(team), security(auto-detect), clean
```

If Stage B escalated:

```
Route: strict (escalated from fast)
Stage A reasons: spec.complexity=low, 0 risk keywords
Stage B reasons: api surface touched, diff>10 files, auth keyword in diff content
Escalation: fast → strict at post-BUILD checkpoint
```

## Non-goals

- Per-criterion routing (every phase that runs sees every criterion)
- Route re-evaluation mid-round (Stage B fires once, after BUILD GATE)
- De-escalation (never — once escalated, stay escalated for the run)
- Replacing `--skip-*` flags (flags remain; route is an overlay on top)
