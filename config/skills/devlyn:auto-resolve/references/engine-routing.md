# Engine Routing: Intelligent Model Selection

Instructions for routing work to the optimal model (Claude or Codex) per role and phase. Only read this file when `--engine` is set to `auto` or `codex`.

The routing table below is derived from published benchmarks (April 2026) comparing Claude Opus 4.6 and GPT-5.4 across task-relevant dimensions. The principle: each role's work goes to the model that objectively performs better at that task type.

---

## Benchmark Basis

| Dimension | Claude Opus 4.6 | GPT-5.4 | Gap | Source |
|-----------|-----------------|---------|-----|--------|
| Long-context retrieval (256k) | 92% | ~64% | Claude +28pp | MRCR v2 |
| Graduate-level reasoning | 87.4% | 83.9% | Claude +3.5pp | GPQA Diamond |
| Hard coding problems | ~46% | 57.7% | Codex +11.7pp | SWE-bench Pro |
| Function-level code gen | 90.4% | 93.1% | Codex +2.7pp | HumanEval |
| Terminal/CLI tasks | 65.4% | 75.1% | Codex +9.7pp | Terminal-Bench 2.0 |
| Real-world issue resolution | ~80% | ~80% | Tied | SWE-bench Verified |
| Security vulnerability detection | — | — | Tied | Semgrep 2025 study |
| Agentic computer use | 72.7% | 75.0% | Codex +2.3pp | OSWorld |
| Ambiguous intent handling | Preferred by 70% devs | — | Claude | Developer surveys |

---

## Codex Call Defaults

Every Codex call in this file uses these defaults unless stated otherwise:

```
model: "gpt-5.4"
reasoningEffort: "xhigh"
sandbox: varies per role (see table)
workingDirectory: project root
```

The `model` field accepts any string — pass `"gpt-5.4"` even if the MCP schema lists older defaults. The Codex CLI resolves it.

---

## Role Routing Table

### team-resolve roles

| Role | Engine | Sandbox | Rationale |
|------|--------|---------|-----------|
| root-cause-analyst | **Claude** | — | A/B test: Claude traced git history (15 tool calls) finding exact commit + unchecked migration plan. Codex analyzed structure well but lacked git history depth. Tool access > SWE-bench Pro advantage for this role. |
| test-engineer | **Codex** | workspace-write | Test code generation = HumanEval (+2.7pp), needs file write |
| security-auditor | **Dual** | read-only | Semgrep: both find unique vulns; GAN > single model |
| implementation-planner | **Codex** | read-only | Implementation planning = SWE-bench Pro (+11.7pp) |
| product-designer | **Claude** | — | Ambiguous requirements, user intent = Claude strength |
| ui-designer | **Claude** | — | Visual spec, design reasoning = non-coding task |
| ux-designer | **Claude** | — | User flow analysis = ambiguous intent handling |
| accessibility-auditor | **Codex** | read-only | WCAG pattern checking in code = SWE-bench Pro > GPQA gap |
| product-analyst | **Claude** | — | Requirements clarity, scope judgment = ambiguity handling |
| architecture-reviewer | **Claude** | — | Codebase-wide pattern review = MRCR long-context (+28pp) |
| performance-engineer | **Codex** | read-only | Terminal tasks + algorithm analysis = Terminal-Bench (+9.7pp) |
| api-designer | **Codex** | read-only | API code pattern matching = SWE-bench Pro (+11.7pp) |

### team-review roles

| Role | Engine | Sandbox | Rationale |
|------|--------|---------|-----------|
| security-reviewer | **Dual** | read-only | Same as team-resolve security-auditor |
| quality-reviewer | **Codex** | read-only | Code quality/bug detection = SWE-bench Pro (+11.7pp) |
| test-analyst | **Codex** | workspace-write | Test gap analysis + test code suggestions |
| ux-reviewer | **Claude** | — | UX flow assessment = ambiguity handling |
| ui-reviewer | **Claude** | — | Design token consistency = non-coding task |
| accessibility-reviewer | **Codex** | read-only | WCAG code patterns = SWE-bench Pro |
| product-validator | **Claude** | — | Business logic intent = ambiguity handling |
| api-reviewer | **Codex** | read-only | API pattern consistency = SWE-bench Pro |
| performance-reviewer | **Codex** | read-only | Algorithm complexity = Terminal-Bench (+9.7pp) |

### Summary distribution

| Engine | team-resolve (12) | team-review (9) | Total |
|--------|-------------------|-----------------|-------|
| Claude | 6 | 3 | 9 |
| Codex | 4 | 4 | 8 |
| Dual | 2 | 2 | 4 |

---

## Pipeline Phase Routing (auto-resolve)

| Phase | --engine auto | --engine codex | --engine claude |
|-------|--------------|----------------|-----------------|
| BUILD (implementation) | **Codex** | Codex | Claude |
| BUILD GATE | bash (model-agnostic) | bash | bash |
| BROWSER VALIDATE | Claude (Chrome MCP only) | Claude | Claude |
| EVALUATE | **Claude** | Claude | Claude |
| FIX LOOP | **Codex** | Codex | Claude |
| SIMPLIFY | Claude | Codex | Claude |
| REVIEW (team) | **Mixed per table** | Codex all | Claude all |
| CHALLENGE | **Claude** | Claude | Claude |
| SECURITY REVIEW | **Dual** | Codex | Claude |
| CLEAN | Claude | Codex | Claude |
| DOCS | Claude | Codex | Claude |

Rationale for `--engine auto` choices:
- BUILD/FIX: Codex — SWE-bench Pro 57.7% vs 46%. The biggest model gap is in hard coding tasks.
- EVALUATE/CHALLENGE: Claude — evaluating a full diff requires long-context retrieval (MRCR +28pp) and skeptical reasoning (GPQA +3.5pp). Different model family from builder creates GAN dynamic.
- BROWSER: Claude — Chrome MCP tools are Claude Code session-bound.
- SECURITY: Dual — Semgrep study shows both models find unique vulnerabilities.

---

## Pipeline Phase Routing (ideate)

| Phase | --engine auto | --engine codex | --engine claude |
|-------|--------------|----------------|-----------------|
| FRAME | **Claude** | Codex | Claude |
| EXPLORE | **Claude** | Codex | Claude |
| CONVERGE | **Claude** | Codex | Claude |
| CHALLENGE | **Codex** (rubric critic) | Claude (role reversal) | Claude |
| DOCUMENT | **Claude** | Codex | Claude |

Rationale:
- FRAME/EXPLORE/CONVERGE: Claude — ambiguous intent handling, multi-perspective reasoning.
- CHALLENGE: When `--engine auto`, Codex runs the rubric pass as critic (same role as `--with-codex` but automatic). When `--engine codex`, Claude runs the challenge (role reversal — builder and critic are always different models).
- DOCUMENT: Claude — writing quality for spec generation.

---

## Pipeline Phase Routing (preflight)

| Phase | --engine auto | --engine codex | --engine claude |
|-------|--------------|----------------|-----------------|
| EXTRACT COMMITMENTS | Claude | Codex | Claude |
| CODE AUDIT | **Codex** | Codex | Claude |
| DOCS AUDIT | **Claude** | Codex | Claude |
| BROWSER AUDIT | Claude (Chrome MCP) | Claude | Claude |
| SYNTHESIZE | Claude | Claude | Claude |

---

## How to Spawn a Codex Role

For roles marked **Codex** in the routing table, call `mcp__codex-cli__codex` instead of spawning a Claude Agent subagent. Package the role's full prompt (from the skill's teammate prompt section) into the Codex call.

Template:

```
mcp__codex-cli__codex({
  prompt: "[full role prompt with issue context, file paths, and deliverable format]",
  model: "gpt-5.4",
  reasoningEffort: "xhigh",
  sandbox: "[read-only or workspace-write per table]",
  workingDirectory: "[project root]"
})
```

**Important**: Codex has no access to team infrastructure (TeamCreate, SendMessage, TaskCreate). For Codex roles:
- Include ALL context inline in the prompt (issue description, file paths from investigation, deliverable format)
- The orchestrator collects Codex's response and routes it where it would have gone via SendMessage
- Codex roles cannot communicate with other teammates directly — the orchestrator relays findings

For roles marked **Claude**, spawn a normal Agent subagent as before.

---

## How to Spawn a Dual Role

For roles marked **Dual**, run BOTH models in parallel and merge findings:

1. Spawn a Claude Agent subagent with the role's prompt
2. Call `mcp__codex-cli__codex` with the same role's prompt (sandbox: "read-only")
3. Wait for both to complete
4. Merge findings:
   - Same finding from both → keep more detailed description, mark "confirmed by both models"
   - Claude-only → keep as-is
   - Codex-only → prefix with `[codex]`
   - Conflicting findings → keep both, note the disagreement
   - Take the MORE SEVERE verdict between the two

---

## How to Spawn a Codex BUILD/FIX Agent

For BUILD and FIX LOOP phases when engine routes to Codex:

```
mcp__codex-cli__codex({
  prompt: "[full build/fix prompt with task description, done criteria, and implementation instructions]",
  model: "gpt-5.4",
  reasoningEffort: "xhigh",
  sandbox: "workspace-write",
  fullAuto: true,
  workingDirectory: "[project root]"
})
```

**After Codex completes**: verify changes were made (`git diff --stat`), then proceed to the next phase as normal. The file-based handoff (`.devlyn/done-criteria.md`, `.devlyn/EVAL-FINDINGS.md`, etc.) works identically — Codex writes the same files Claude would.

**Session management**: For FIX LOOP iterations, use a fresh call each time (no `sessionId` reuse) because sandbox/fullAuto parameters only apply on the first call of a session.

---

## Override Behavior

- `--engine claude` → all roles and phases use Claude (current default behavior, no Codex calls)
- `--engine codex` → all phases use Codex for implementation/analysis, Claude only for orchestration and Chrome MCP
- `--engine auto` → each role and phase routes to the optimal model per this table
- `--engine auto` is the recommended default when Codex MCP server is available

`--engine` and `--with-codex` are **mutually exclusive**. `--engine auto` subsumes `--with-codex both` — it uses Codex where it's optimal (broader than just evaluate/review). If both flags are passed, `--engine` takes precedence and `--with-codex` is ignored with a warning.
