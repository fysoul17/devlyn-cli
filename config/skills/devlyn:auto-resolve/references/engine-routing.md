# Engine Routing: Intelligent Model Selection

Routing rules for Claude / Codex / Dual per role and phase. Only read when `--engine` is `auto` or `codex`.

Codex call defaults: `model: "gpt-5.4"`, `reasoningEffort: "xhigh"`, `sandbox` per role (below), `workingDirectory: <project root>`.

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
| CRITIC (security sub-pass) | **Dual** | Codex | Claude |
| DOCS | Claude | Codex | Claude |

Rationale:
- BUILD/FIX: Codex — SWE-bench Pro advantage on hard coding.
- EVALUATE/CRITIC design sub-pass: Claude — long-context retrieval + skeptical reasoning; different model family from builder for GAN dynamic.
- BROWSER: Claude — Chrome MCP tools session-bound.
- CRITIC security: Dual on `auto` — Semgrep study shows each model finds unique vulnerabilities; for security, coverage trumps cost.

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

For Codex roles: `mcp__codex-cli__codex` with `model: "gpt-5.4"`, `reasoningEffort: "xhigh"`, sandbox per table. Include full role prompt inline; Codex has no access to TeamCreate/SendMessage/TaskCreate.

For Dual roles: run both in parallel, merge findings. Same finding from both → keep more detailed wording, mark "confirmed by both". Codex-only → prefix `[codex]`. Conflicts → keep both.

---

## Override behavior

- `--engine claude` → all roles/phases use Claude (no Codex calls).
- `--engine codex` → all phases use Codex for implementation/analysis, Claude only for orchestration/Chrome MCP.
- `--engine auto` (default) → each role/phase routes per this table.
