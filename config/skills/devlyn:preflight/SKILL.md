---
name: devlyn:preflight
description: >
  Final alignment check between vision/roadmap documents and the actual codebase before declaring
  a roadmap phase complete. Reads commitments from VISION.md, ROADMAP.md, and item specs, then
  audits the implementation with file:line evidence. Catches missing/incomplete features, spec
  divergence, bugs, and doc drift; validates browser behavior for web projects. Use when
  implementation is finished and you want a holistic roadmap-vs-code verification. Triggers on
  "preflight", "gap analysis", "did I miss anything", "check against the roadmap", "verify
  implementation", "are we done". Differs from /devlyn:evaluate (single changeset) and
  /devlyn:review (code quality) — preflight audits the entire project against planning docs.
---

# Vision-to-Implementation Preflight Check

The final gate before you declare "done." Read every promise the planning documents made, then verify each one against the actual codebase — evidence-based, no guessing.

<preflight_config>
$ARGUMENTS
</preflight_config>

<why_this_matters>
After implementing a full roadmap, gaps are almost inevitable. Features get partially implemented, edge cases from specs get skipped, implementations drift from the original design, and docs fall out of sync. These gaps compound — a missing integration here, a forgotten error state there — until the shipped product doesn't match the vision.

This skill catches those gaps systematically, before users do. The difference between "we built everything on the list" and "we actually delivered what we promised."
</why_this_matters>

<evidence_standard>
Every finding must cite evidence: file:line for code, specific doc section for documentation, screenshot for browser issues. A finding without evidence is speculation — exclude it.

The corollary: if you search thoroughly and can't find evidence that something exists, that IS evidence it's missing. "Searched for X across src/ and found no implementation" is a valid, evidence-based finding.

This matters because the report feeds into auto-resolve. Vague findings produce vague fixes.
</evidence_standard>

## Flags

Parse from `<preflight_config>`:
- `--phase N` — audit only phase N items (default: all phases)
- `--autofix` — auto-promote all findings to roadmap items and run auto-resolve on each
- `--skip-browser` — skip browser validation
- `--skip-docs` — skip documentation audit
- `--engine MODE` (auto) — controls which model handles audit phases. Modes:
  - `auto` (default): code-auditor uses Codex (SWE-bench Pro +11.7pp for code analysis), docs-auditor uses Claude (writing quality), browser-auditor uses Claude (Chrome MCP). Requires Codex MCP server.
  - `codex`: code-auditor uses Codex, docs-auditor and browser-auditor use Claude.
  - `claude`: all auditors use Claude subagents. No Codex calls.

Example: `/devlyn:preflight --phase 2 --skip-browser`
Example with engine: `/devlyn:preflight --engine auto`

**Engine pre-flight** (runs unless `--engine claude` was explicitly passed):
- The default engine is `auto`. If the user did not pass `--engine`, the engine is `auto` — NOT `claude`.
- Call `mcp__codex-cli__ping` to verify Codex MCP availability. On failure, **silently fall back to `--engine claude`** and note `engine downgraded: codex-ping failed` in the final preflight report header. Do not abort. Matches the hands-off contract used by auto-resolve and ideate.

## PHASE 0: DISCOVER & SCOPE

<use_parallel_tool_calls>
Phase 0 and Phase 1 do many independent reads (planning docs, item specs, prior state). When tool calls have no dependencies between them, issue them in parallel in a single response — that includes globbing for spec files and reading several specs at once. Only chain calls that depend on values from a previous call.
</use_parallel_tool_calls>

1. **Find planning documents** — search in parallel:
   - `docs/VISION.md`
   - `docs/ROADMAP.md`
   - `docs/roadmap/` directory (item specs)
   - If none found, stop clearly: "No vision/roadmap documents found. Run `/devlyn:ideate` first to create them."

2. **Determine scope**:
   - If `--phase N` specified → only read specs in `docs/roadmap/phase-N/`
   - Otherwise → read all phases
   - Read `docs/roadmap/backlog/` to identify deferred items (excluded from audit)

3. **Check for prior state**:
   - If `.devlyn/PREFLIGHT-REPORT.md` exists from a previous run → note it for delta comparison in PHASE 4
   - If `.devlyn/preflight-accepted.md` exists → load accepted divergences to filter in PHASE 4

4. **Announce**:
```
Preflight check starting
Scope: [Phase N / All phases]
Documents: VISION.md, ROADMAP.md, [N] item specs
Deferred items (excluded): [N]
Previous run: [found — will show delta / none]
Phases: 1 Extract → 2 Audit (code + docs + browser) → 3 Report → 4 Triage
```

## PHASE 1: EXTRACT COMMITMENTS

Read all in-scope planning documents and build a **commitment registry** — every concrete promise the documents make. This registry is the grading rubric for all auditors.

1. **Read in parallel**: VISION.md, ROADMAP.md, all in-scope item specs, phase `_overview.md` files

2. **Extract from each item spec**:
   - Requirements section → each bullet becomes a `FEATURE` or `BEHAVIOR` commitment
   - Constraints section → each becomes a `CONSTRAINT` commitment
   - Dependencies section → each becomes an `INTEGRATION` commitment
   - Explicit test requirements → `TEST` commitments

3. **Extract from VISION.md**: high-level success criteria — checked at a broader level ("the system supports X" rather than "file Y has function Z")

4. **Filter out** (excluded from audit entirely):
   - Items in `backlog/` or `deferred.md`
   - Items with `status: cut` in ROADMAP.md

5. **Anti-commitments ARE audited** (Out of Scope entries in each spec). These are "must NOT build" claims — if the codebase has shipped something the spec explicitly excluded, that is a WORKAROUND / scope-creep finding, not a success. The code-auditor checks each anti-commitment: "is this excluded behavior present in the code?" If yes → emit a finding with `rule_id: "scope.anti-commitment-violation"` (severity HIGH).

6. **Separate planned items**: Items with `status: planned` in their spec frontmatter or "Planned" in ROADMAP.md are not expected to be implemented yet. Include them in a `[PLANNED]` section of the registry for visibility, but do **not** audit them as missing. Flagging planned items as MISSING creates noise and buries the real gaps in work that was supposed to be done.

7. **Write to `.devlyn/commitment-registry.md`**:

```markdown
# Commitment Registry
Generated: [timestamp]
Scope: [phase N / all]
Total commitments: [N]

## Phase 1: [name]
### 1.1 [item title] (spec status: [done/in-progress/planned])
- [FEATURE] User can sign up with email and password
- [BEHAVIOR] Failed login returns 401 with specific error message
- [CONSTRAINT] Passwords hashed with bcrypt, min 8 characters
- [INTEGRATION] Auth middleware applied to all /api/* routes
- [TEST] Auth flow covered by E2E tests

## Anti-Commitments (Out of Scope — audited as "must NOT exist in code")
- [item 1.1] Must NOT include social login
- [item 1.2] Must NOT include real-time inventory sync

## Not Started (Planned — not audited for presence, but still anti-commitments inside them apply)
### 2.1 [item title] (spec status: planned)
- [FEATURE] WebSocket connection on page load
- [FEATURE] Real-time task list updates
[Planned items are tracked for visibility; code-auditor does not flag as MISSING.]
```

## PHASE 2: AUDIT

Spawn all applicable auditors in parallel. Each reads `.devlyn/commitment-registry.md` and investigates from their perspective.

### code-auditor (always)

Engine routes per the auto-resolve skill's `references/engine-routing.md` ("Pipeline Phase Routing (preflight)" → CODE AUDIT row): Codex on `--engine auto`/`codex`, Claude on `--engine claude`. When the route is **Codex**, call `mcp__codex-cli__codex` with the auditor prompt inline (Codex cannot read `.devlyn/commitment-registry.md` directly under `read-only` sandbox, so paste the registry into the prompt). When the route is **Claude**, spawn a subagent with `mode: "bypassPermissions"`. Read the auditor prompt from `references/auditors/code-auditor.md` either way.

The code-auditor classifies each commitment as IMPLEMENTED, MISSING, INCOMPLETE, DIVERGENT, or BROKEN — with file:line evidence. Also catches cross-feature integration gaps and constraint violations. Writes to `.devlyn/audit-code.md`.

### docs-auditor (unless --skip-docs)

Always Claude (writing-quality strength) regardless of `--engine`. Spawn a subagent with `mode: "bypassPermissions"`. Read the full prompt from `references/auditors/docs-auditor.md` and pass it to the subagent.

Checks: ROADMAP.md status accuracy, README alignment, API doc coverage, VISION.md currency, item spec status. Writes to `.devlyn/audit-docs.md`.

### browser-auditor (conditional)

Always Claude (Chrome MCP tools are session-bound) regardless of `--engine`.

**Skip conditions** (check in order):
1. `--skip-browser` flag → skip
2. No web-relevant files in project (no `*.tsx`, `*.jsx`, `*.vue`, `*.svelte`, `*.html`, `page.*`, `layout.*`) → skip with note "Browser validation skipped — no web files detected"
3. Otherwise → spawn

Spawn a subagent with `mode: "bypassPermissions"`. Read the full prompt from `references/auditors/browser-auditor.md` and pass it to the subagent.

Tests user-facing features in the browser against commitment registry. Writes to `.devlyn/audit-browser.md`.

**After all auditors complete**: Read each audit file and proceed to PHASE 3.

## PHASE 3: SYNTHESIZE & REPORT

Auditors already emit each finding with its category (`MISSING`/`INCOMPLETE`/`DIVERGENT`/`BROKEN`/`UNDOCUMENTED`/`STALE_DOC`/`scope.anti-commitment-violation`) and severity (`CRITICAL`/`HIGH`/`MEDIUM`/`LOW`). Synthesis passes them through — do NOT re-classify or re-severity-label. That would replace domain judgment with orchestrator mechanics.

1. **Read all audit files** in parallel:
   - `.devlyn/audit-code.md`
   - `.devlyn/audit-docs.md` (if exists)
   - `.devlyn/audit-browser.md` (if exists)

2. **Deduplicate**: if multiple auditors flagged the same issue (same category + file:line), merge into one finding at the highest severity the reporting auditor assigned. Trust the auditor's severity — do not override.

3. **Filter accepted divergences**: if `.devlyn/preflight-accepted.md` exists, remove findings whose (category, commitment) matches an accepted entry.

4. **Compare with previous run** (if `.devlyn/PREFLIGHT-REPORT.md` existed):
   - `RESOLVED`: finding from previous run no longer present
   - `PERSISTS`: finding still present
   - `NEW`: finding not in previous run

5. **Generate `.devlyn/PREFLIGHT-REPORT.md`**:

```markdown
# Preflight Report
Generated: [timestamp]
Scope: [phase N / all]
Previous run: [timestamp / none]

## Summary
| Category | Count |
|----------|-------|
| MISSING | [N] |
| INCOMPLETE | [N] |
| DIVERGENT | [N] |
| BROKEN | [N] |
| SCOPE_VIOLATION | [N] |
| UNDOCUMENTED | [N] |
| STALE_DOC | [N] |
| **Total findings** | **[N]** |

## Delta (vs previous run)
- Resolved: [N]
- Persists: [N]
- New: [N]

## Commitment Coverage
- Active commitments (done/in-progress specs): [N]
- Verified (IMPLEMENTED): [N] ([%])
- Issues found: [N] ([%])
- Planned items (excluded from audit): [N] across [M] specs

## Findings

### CRITICAL
- **[MISSING]** `1.2` — Order cancellation flow
  - **Commitment**: "User can cancel pending orders within 24 hours"
  - **Evidence**: No cancellation endpoint in `src/api/orders/`. No cancel button in `src/components/OrderDetail.tsx`.
  - **Impact**: Core user workflow completely absent.

### HIGH
- **[INCOMPLETE]** `1.1` — Error handling on signup
  - **Commitment**: "Failed signup shows specific validation errors"
  - **Evidence**: `src/api/auth/signup.ts:34` returns generic 500. No field-level validation.
  - **Impact**: Users see "Something went wrong" instead of actionable feedback.

### MEDIUM
...

### LOW
...

## Documentation Findings
- [STALE_DOC] ROADMAP.md: Item 1.3 status "In Progress" → should be "Done"
- [UNDOCUMENTED] WebSocket real-time updates not mentioned in README

## What's Verified
[Explicitly list areas that passed — balanced feedback prevents over-correction]
- Auth flow: all 5 commitments verified (signup, login, logout, password reset, session management)
- Database schema: matches all spec constraints

## Not Started (Expected — Planned Items)
[List planned items here for visibility, not as findings]
- 2.1 Real-time Updates — status: planned, 5 commitments
- 2.2 Team Management — status: planned, 6 commitments
These items are acknowledged future work per the roadmap. They will be audited when their status changes to in-progress or done.

## Accepted Divergences (from previous runs)
- [list any, or "None"]
```

6. **Present the report** to the user with a summary.

## PHASE 4: TRIAGE & PROMOTE

How this phase runs depends on the `--autofix` flag:

### Without --autofix (default — interactive)

Present findings and guide the user through triage:

```
Preflight found [N] findings across [categories].

For each finding, you can:
1. **Promote** → creates a roadmap item spec, adds to ROADMAP.md
2. **Accept** → marks as intentional divergence (won't flag on future runs)
3. **Skip** → leave for later

Which findings would you like to promote to the roadmap?
```

**When the user confirms findings to promote:**

1. **Generate item specs** for each confirmed finding, following the ideate template format:
   ```markdown
   ---
   id: "[phase].[next-number]"
   title: "[Fix/Add: description]"
   phase: [N]
   status: planned
   priority: [derived from finding severity]
   complexity: [estimated from finding scope]
   depends-on: []
   ---

   # [id] [Title]

   ## Context
   Preflight check identified this gap against the original roadmap specification.
   [Brief context from the original commitment and what's wrong]

   ## Objective
   [What needs to be true after this is fixed]

   ## Requirements
   - [ ] [Specific fix requirement derived from the finding]
   - [ ] [Verification step]

   ## Constraints
   - Must align with original spec at docs/roadmap/phase-N/[original-item].md

   ## Out of Scope
   - Changes beyond what the original spec requires
   ```

2. **Place specs** in the appropriate roadmap phase directory (same phase as the original item, or a new "fixes" phase if multiple phases are affected)

3. **Update ROADMAP.md** with new rows for promoted findings

4. **Record accepted divergences** in `.devlyn/preflight-accepted.md`:
   ```markdown
   # Accepted Divergences
   # Findings marked as intentional — excluded from future preflight runs

   - [item-id] [commitment]: [reason accepted]
   ```

5. **STALE_DOC findings**: Fix these directly — update ROADMAP.md statuses, item spec frontmatter, and VISION.md "What's Next" sections. These are factual corrections, not implementation decisions.

6. **Suggest next steps**:
```
Triage complete.
- [N] findings promoted to roadmap ([list item IDs])
- [N] divergences accepted
- [N] doc issues fixed directly

Next steps:
- To implement fixes: /devlyn:auto-resolve "Implement per spec at docs/roadmap/phase-N/[id]-[name].md"
  - For CRITICAL severity or complex DIVERGENT findings, the default `--engine auto` already routes BUILD/FIX to Codex and EVALUATE/CHALLENGE to Claude (cross-model GAN dynamic). No extra flag needed.
- To re-run preflight after fixes: /devlyn:preflight [same flags]
- To add new features discovered during audit: /devlyn:ideate expand
```

### With --autofix

1. Auto-promote all CRITICAL and HIGH findings to roadmap items (steps 1-3 above)
2. Fix all STALE_DOC findings directly
3. MEDIUM and LOW findings are reported but not auto-promoted (include in report with note "manually promote if needed")
4. For each promoted item, spawn `/devlyn:auto-resolve` sequentially:
   ```
   /devlyn:auto-resolve "Implement per spec at docs/roadmap/phase-N/[id]-[name].md"
   ```
5. After all auto-resolve runs complete, re-run preflight (without --autofix) as a verification pass
6. Present final delta report showing what was resolved

<autofix_safety>
Auto-promoting only CRITICAL and HIGH findings prevents noise — MEDIUM/LOW findings often benefit from human judgment on whether they're worth fixing or should be accepted as intentional divergence. The user can always manually promote remaining findings after reviewing the report.
</autofix_safety>

## Language

Generate all documents and reports in the language the user communicates in. Keep technical terms (file paths, code references, category names like MISSING/DIVERGENT) in English for consistency with the rest of the devlyn toolchain.
