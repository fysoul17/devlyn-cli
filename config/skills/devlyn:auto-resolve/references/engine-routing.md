# Engine Routing: Intelligent Model Selection

Routing rules for Claude / Codex / Dual per role and phase. Only read when `--engine` is `auto` or `codex`.

> Codex invocations shell out via the wrapper at `_shared/codex-monitored.sh`. Flag set + rationale live in `config/skills/_shared/codex-config.md`. No MCP, no model hardcoding — the CLI's current flagship is inherited automatically.

Codex call defaults: `bash .claude/skills/_shared/codex-monitored.sh -C <project root> -s <per role> -c model_reasoning_effort=xhigh "<prompt>"`. The wrapper passes args through verbatim to the underlying CLI and emits a heartbeat every 30s so the outer `claude -p` byte-watchdog stays fed during long reasoning. Omit `-m` so the flagship is auto-selected. Only pass `-m <variant>` when a role explicitly needs a specialized model line, and name the variant generically ("SWE-bench-heavy coding variant") rather than hardcoding a version number — version strings go stale fast.

---

## Pipeline Phase Routing (auto-resolve)

| Phase | `--engine auto` | `--engine codex` | `--engine claude` |
|-------|--------------|----------------|-----------------|
| BUILD | **Codex** | Codex | Claude |
| BUILD GATE | bash | bash | bash |
| BROWSER VALIDATE | Claude (Chrome MCP) | Claude | Claude |
| EVALUATE | **Claude** | Claude | Claude |
| FIX LOOP | **Codex** | Codex | Claude |
| CRITIC (design sub-pass) | Claude | Claude | Claude |
| CRITIC (security sub-pass) | **Native `security-review`** | Native | Native |
| DOCS | Claude | Codex | Claude |

Rationale:
- BUILD/FIX: Codex — SWE-bench Pro advantage on hard coding.
- EVALUATE/CRITIC design sub-pass: Claude — long-context retrieval + skeptical reasoning; different model family from builder for GAN dynamic.
- BROWSER: Claude — Chrome MCP tools session-bound.
- CRITIC security: native Claude Code `security-review` skill on every engine — findings-only (post-EVAL invariant compatible), covers the same OWASP surface as the old custom pass, and drops the Dual-model token cost. Invocation + normalization rules live in `phases/phase-3-critic.md` (Sub-pass 2).

### Per-fixture-class BUILD overrides (iter-0020)

The `--engine auto` BUILD default is Codex. Per-fixture-class overrides apply when `state.source.fixture_class` (populated from `BENCH_FIXTURE_CATEGORY` env at PHASE 0) matches an entry. The override fires ONLY when user `--engine == "auto"` — explicit `--engine claude` / `--engine codex` always wins.

| `fixture_class` | BUILD override | Rationale |
|---|---|---|
| `e2e` | **Claude** | iter-0020: F9 evidence — Codex BUILD on novice-flow regresses L2-L1 = -21 with material wall premium AND introduces silent-catch DQ ([memory:`project_iter0019_8_shipped_2026_04_28.md`](../../../../autoresearch/iterations/0020-pair-policy-narrow.md), F9-rerun RUN_ID `20260428T112748Z-0f9e077-iter-0019-9-F9-reverify`). Pair-mode Codex BUILD is not layer-cost-justified for this class; routing to Claude BUILD is the narrow defense. Other fixture classes keep Codex BUILD on `auto`. |

The override is selected in code by `scripts/select_phase_engine.py` (invoked from PHASE 1 BUILD before spawn). It writes `state.route.engine_overrides.build` when fired so `coverage_report.py` can prove the route was exercised.

Rollback condition: revert this entry if the iter-0020 9-fixture suite (or any subsequent paid run) shows the e2e fixture-class regressing by ≥ 3 axes vs the iter-0019.9 baseline (F9 L1=92 / verify=1.0 / dq=false).

---

## Pipeline Phase Routing (ideate)

| Phase | `--engine auto` | `--engine codex` | `--engine claude` |
|-------|--------------|----------------|-----------------|
| FRAME | Claude | Codex | Claude |
| EXPLORE | Claude | Codex | Claude |
| CONVERGE | Claude | Codex | Claude |
| CHALLENGE | **Codex** (rubric critic) | Claude (role reversal) | Claude |
| DOCUMENT | Claude | Codex | Claude |

CHALLENGE: when `--engine auto`, Codex runs the rubric as critic (builder and critic always different models).

---

## Pipeline Phase Routing (preflight)

| Phase | `--engine auto` | `--engine codex` | `--engine claude` |
|-------|--------------|----------------|-----------------|
| EXTRACT | Claude | Codex | Claude |
| AUDIT (code) | **Codex** | Codex | Claude |
| AUDIT (docs) | **Claude** | Claude | Claude |
| AUDIT (browser) | Claude | Claude | Claude |
| SYNTHESIZE | Claude | Claude | Claude |

Docs auditor is always Claude (writing-quality strength for prose-drift detection). Browser is always Claude (Chrome MCP session-bound).

---

## Team-role routing (when `--team` is on OR route == strict in auto-resolve, OR team-review in standalone)

| Role | Engine | Sandbox | Rationale |
|------|--------|---------|-----------|
| root-cause-analyst | Claude | — | Git-history traversal + tool access beats SWE-bench Pro for this role |
| test-engineer | Codex | workspace-write | HumanEval edge, needs file write |
| security-auditor | Dual | read-only | Semgrep: each finds unique vulns |
| implementation-planner | Codex | read-only | SWE-bench Pro +11.7pp |
| architecture-reviewer | Claude | — | Codebase-wide pattern review = MRCR strength |
| performance-engineer | Codex | read-only | Terminal-Bench edge |
| api-designer / api-reviewer | Dual | read-only | Both find unique API issues |
| quality-reviewer | Dual | read-only | Measured ~36–73% coverage gain from dual |
| ux/ui/accessibility-* | Claude | — | Ambiguity handling + WCAG domain depth |

For Codex roles: shell out `bash .claude/skills/_shared/codex-monitored.sh -C <project root> -s <sandbox per table> -c model_reasoning_effort=xhigh "<role prompt>"`. Include the full role prompt inline; Codex has no access to TeamCreate/SendMessage/TaskCreate.

For Dual roles: run both in parallel, merge findings. Same finding from both → keep more detailed wording, mark "confirmed by both". Codex-only → prefix `[codex]`. Conflicts → keep both.

---

## Override behavior

- `--engine claude` → all roles/phases use Claude (no Codex calls).
- `--engine codex` → all phases use Codex for implementation/analysis, Claude only for orchestration/Chrome MCP.
- `--engine auto` (default) → each role/phase routes per this table.
