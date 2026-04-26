# Engine Routing: Intelligent Model Selection

Routing rules for Claude / Codex / Dual per role and phase. Only read when `--engine` is `auto` or `codex`.

> Codex invocations use the local `codex exec` CLI. Flag set + rationale live in `config/skills/_shared/codex-config.md`. No MCP, no model hardcoding — the CLI's current flagship is inherited automatically.

Codex call defaults: `codex exec -C <project root> -s <per role> -c model_reasoning_effort=xhigh "<prompt>"`. Omit `-m` so the flagship is auto-selected. Only pass `-m <variant>` when a role explicitly needs a specialized model line, and name the variant generically ("SWE-bench-heavy coding variant") rather than hardcoding a version number — version strings go stale fast.

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

For Codex roles: shell out `codex exec -C <project root> -s <sandbox per table> -c model_reasoning_effort=xhigh "<role prompt>"`. Include the full role prompt inline; Codex has no access to TeamCreate/SendMessage/TaskCreate.

For Dual roles: run both in parallel, merge findings. Same finding from both → keep more detailed wording, mark "confirmed by both". Codex-only → prefix `[codex]`. Conflicts → keep both.

---

## Override behavior

- `--engine claude` → all roles/phases use Claude (no Codex calls).
- `--engine codex` → all phases use Codex for implementation/analysis, Claude only for orchestration/Chrome MCP.
- `--engine auto` (default) → each role/phase routes per this table.
