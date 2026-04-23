# Pipeline Routing — 3 Routes + Stage A + Stage B LITE

Auto-resolve adapts its pipeline shape to each task. Single source of truth for route selection; the orchestrator reads it, SKILL.md does not restate the rules.

## The 3 routes

| Route | Intended for | Phases that run |
|-------|-------------|-----------------|
| `fast` | Trivial / low-complexity, zero risk signals | PARSE → BUILD → BUILD GATE → [BROWSER if web] → EVAL → [FIX if findings] → FINAL REPORT |
| `standard` | Default for medium work | `fast` + CRITIC (findings-only) + DOCS |
| `strict` | High-complexity OR risk signals present OR escalated | `standard` + team-assembled BUILD + BUILD GATE strict mode |

Every route runs PARSE, BUILD, BUILD GATE, EVAL, and FINAL REPORT. Routes differ in whether CRITIC/DOCS run and whether BUILD assembles a team.

**Findings-only** (CRITIC) means the phase emits a `.findings.jsonl` + `.log.md` but does not write code. The orchestrator routes any NEEDS_WORK/BLOCKED findings through the unified fix loop (see SKILL.md `PHASE 2.5`), which re-runs EVAL. This enforces the post-EVAL invariant: all semantic changes go through EVAL.

## Default guardrails (route-invariant under `auto`)

These hold across all three routes with no `--bypass`:

1. **BUILD GATE PASS** — `fast` runs the gate too.
2. **Independent EVAL PASS** — file:line evidence required.
3. **Every criterion terminal** (`verified` or `failed`).
4. **Zero open HIGH/CRITICAL findings** at pipeline exit (subject to `--max-rounds` — see exhaustion table).
5. **Web file changes force BROWSER VALIDATE** (`.tsx/.jsx/.vue/.svelte/.css/.html`, `page.*/layout.*/route.*`).
6. **Post-BUILD risk detection auto-escalates** via Stage B LITE.

## The `--bypass` flag

Semantics: `--bypass <phase>[,<phase>...]`. Bypassable phases: `build-gate`, `browser`, `critic`, `docs`.

Every bypass is recorded in `state.route.bypasses` and surfaced in the final report's `Guardrails bypassed:` line.

**Deprecated aliases** (still accepted, log warning once): `--skip-build-gate`, `--skip-browser`, `--skip-review`, `--skip-clean`, `--skip-docs`, `--security-review skip`, `--bypass simplify|review|clean|security|challenge` all map to `--bypass critic` for the post-EVAL group or the appropriate phase otherwise. Removed next minor version.

## `--max-rounds` exhaustion

When the fix loop exhausts `max_rounds` with findings still open:

| `triggered_by` | exhaustion behavior |
|---|---|
| `build_gate` | **halt** — skip to FINAL REPORT with `BUILD GATE EXHAUSTED` banner |
| `browser_validate` | **halt** — skip to FINAL REPORT with `BROWSER EXHAUSTED` banner |
| `evaluate` | **proceed_with_warning** — FINAL REPORT shows `EVAL EXHAUSTED` banner + open findings |
| `critic` | **proceed_with_warning** — FINAL REPORT shows `CRITIC EXHAUSTED` banner + open findings |

Guardrail #4 is suspended under `_with_warning` exhaustion: report banner shows what's unresolved.

## Stage A — Pre-build (PHASE 0)

Decision order (first match wins):

1. **User override** (`--route fast|standard|strict`): set `route.selected`, `route.user_override: true`. Stage B LITE will not run.
2. **Hard blocker**: missing spec or unmet internal deps → halt BLOCKED.
3. **Risk keywords in source**: grep source body (spec body for spec-driven, task description for generated) for `auth, login, session, token, secret, password, crypto, api, env, permission, access, database, migration, payment`. Any hit → `strict`. Record matched keywords.
4. **Complexity-based** (spec-driven only):
   - `spec.frontmatter.complexity == "high"` → `strict`
   - `spec.frontmatter.complexity == "medium"` → `standard`
   - `spec.frontmatter.complexity == "low"` → `fast`
5. **Generated tasks**: default to `standard`, Stage B LITE may escalate after BUILD.

Stage A writes to `state.route.stage_a.{at, reasons}`.

## Stage B LITE — Post-BUILD-GATE (PHASE 1.4)

**One rule** (simplified from v3.2's multi-heuristic machinery). Does not run if `route.user_override == true`. Only escalates, never de-escalates.

**Rule**: escalate to `strict` if `git diff <state.base_ref.sha>` meets ANY of:

- **Risk keyword in diff content** — matches any of the 14 Stage A risk keywords.
- **API surface** — changed files include paths under `src/api/`, `routes/`, `handlers/`, `app/api/`.
- **Dependency change** — any of: `package.json`, `requirements.txt`, `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `Pipfile.lock`, `poetry.lock`, `Cargo.toml`, `Cargo.lock`, `go.mod`, `go.sum`.

Stage B LITE writes to `state.route.stage_b.{at, escalated_from, reasons}`. No escalation → `stage_b.at` remains `null`.

## Phase inclusion matrix

| Phase | `fast` | `standard` | `strict` |
|-------|--------|-----------|----------|
| 0 PARSE + PREFLIGHT + ROUTE | ✓ | ✓ | ✓ |
| 1 BUILD (solo) | ✓ | ✓ | — (team) |
| 1 BUILD (team) | `--team` | `--team` | ✓ |
| 1.4 BUILD GATE (auto) | ✓ | ✓ | — (strict+docker) |
| 1.4 BUILD GATE (strict+docker) | — | — | ✓ |
| 1.5 BROWSER VALIDATE | ✓ (web) | ✓ (web) | ✓ (web) |
| 2 EVALUATE | ✓ | ✓ | ✓ |
| 2.5 UNIFIED FIX LOOP | ✓ (if findings) | ✓ (if findings) | ✓ (if findings) |
| 3 CRITIC (findings-only) | — | ✓ | ✓ (security sub-pass uses native `security-review`) |
| 4 DOCS (doc-files only) | — | ✓ | ✓ |
| 5 FINAL REPORT + ARCHIVE | ✓ | ✓ | ✓ |

Legend: ✓ runs, — skipped by route. `--bypass <phase>` forces skip on any route. `fast` skips CRITIC and DOCS.

## Terminal-state algorithm (PHASE 5)

Final verdict computed across all findings files in precedence order:

1. **BUILD GATE FAIL** at exhaustion → `BLOCKED` with `BUILD GATE EXHAUSTED`.
2. **BROWSER VALIDATE BLOCKED** at exhaustion → `BLOCKED`.
3. **Any unresolved CRITICAL** in any `<phase>.findings.jsonl` → `BLOCKED`.
4. **Any unresolved HIGH** with `rule_id` prefix `correctness.*` / `security.*` / `design.*` → `NEEDS_WORK`.
5. **Any unresolved HIGH** (other categories) → `NEEDS_WORK`.
6. **Any unresolved MEDIUM security.***  → `NEEDS_WORK` (security stricter than general by design).
7. **Any unresolved MEDIUM** (other categories) → `PASS_WITH_ISSUES`.
8. **Only LOW / none** → `PASS`.

"Unresolved" means `status == "open"` in the latest round's file.

## Non-goals

- Per-criterion routing (every phase sees every criterion).
- Route re-evaluation mid-round.
- De-escalation.
- Replacing `--bypass` (bypass is an orthogonal opt-out).
