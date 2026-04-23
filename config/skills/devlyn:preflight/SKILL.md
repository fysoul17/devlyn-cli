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
Every finding must cite evidence. The shape depends on the finding category:

- **Present-code findings** (INCOMPLETE / DIVERGENT / BROKEN / SCOPE_VIOLATION / UNDOCUMENTED / STALE_DOC): `file:line` pointing at the offending code or doc.
- **MISSING findings** (code the spec required but no trace exists): an explicit "searched X and found no implementation" statement — this IS evidence of absence and qualifies under the standard. MISSING findings have no file:line by definition; forcing one would mean fabricating a target, which is worse than honest absence.
- **Doc findings** (STALE_DOC on ROADMAP/VISION/README): quote the stale text + cite the doc section or line.
- **Browser findings**: screenshot reference + URL/route.

A finding without one of these forms of evidence is speculation — exclude it. This matters because the report feeds into auto-resolve; vague findings produce vague fixes.
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

**Engine pre-flight**: follow `config/skills/_shared/engine-preflight.md`. The downgrade banner surfaces in the final preflight report header.

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

5. **Anti-commitments ARE audited** (Out of Scope entries in each spec). These are "must NOT build" claims — if the codebase has shipped something the spec explicitly excluded, that is a WORKAROUND / scope-creep finding, not a success. The code-auditor checks each anti-commitment: "is this excluded behavior present in the code?" If yes → emit a finding with **category `SCOPE_VIOLATION`** and **`rule_id: "scope.anti-commitment-violation"`**, severity HIGH (or CRITICAL if it also violates a constraint). Category is the report bucket; `rule_id` is the specific rule that fired — both fields always co-occur on anti-commitment findings.

6. **Separate planned items**: Items with `status: planned` in their spec frontmatter or "Planned" in ROADMAP.md are not expected to be implemented yet. Include them in a `[PLANNED]` section of the registry for visibility, but do **not** audit them as missing. Flagging planned items as MISSING creates noise and buries the real gaps in work that was supposed to be done.

7. **Write `.devlyn/commitment-registry.md`** per the shape in `references/report-template.md#commitment-registry-shape-devlyncommitment-registrymd`. Required blocks: scoped commitments grouped by phase/item, Anti-Commitments, Not Started (planned items — tracked, not audited for presence).

## PHASE 2: AUDIT

Spawn all applicable auditors in parallel. Each reads `.devlyn/commitment-registry.md` and investigates from their perspective.

### code-auditor (always)

Engine routes per the auto-resolve skill's `references/engine-routing.md` ("Pipeline Phase Routing (preflight)" → CODE AUDIT row): Codex on `--engine auto`/`codex`, Claude on `--engine claude`. When the route is **Codex**, shell out `codex exec -C <project root> -s read-only -c model_reasoning_effort=xhigh "<auditor prompt with commitment registry inlined>"` — the registry must be pasted into the prompt because Codex has no filesystem access under read-only. When the route is **Claude**, spawn a subagent with `mode: "bypassPermissions"`. Read the auditor prompt from `references/auditors/code-auditor.md` either way.

The code-auditor classifies each commitment as IMPLEMENTED, MISSING, INCOMPLETE, DIVERGENT, BROKEN, or SCOPE_VIOLATION — with evidence per `<evidence_standard>`. Also catches cross-feature integration gaps and constraint violations. Writes to `.devlyn/audit-code.md`.

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

Auditors already emit each finding with its **category** (`MISSING` / `INCOMPLETE` / `DIVERGENT` / `BROKEN` / `SCOPE_VIOLATION` / `UNDOCUMENTED` / `STALE_DOC`) and severity (`CRITICAL` / `HIGH` / `MEDIUM` / `LOW`). SCOPE_VIOLATION findings additionally carry `rule_id: "scope.anti-commitment-violation"` so the triggering anti-commitment is traceable. Synthesis passes both fields through — do NOT re-classify the category or re-severity-label. That would replace domain judgment with orchestrator mechanics.

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

5. **Generate `.devlyn/PREFLIGHT-REPORT.md`** per the shape in `references/report-template.md`. Required sections in order: header (timestamp + scope + previous run), Summary (counts per category), Delta, Commitment Coverage, Findings (grouped CRITICAL → HIGH → MEDIUM → LOW with category prefix + evidence + impact), Documentation Findings, What's Verified, Not Started, Accepted Divergences. Every finding carries evidence per `<evidence_standard>` — shape varies by category (file:line for present-code, "searched X / not found" for MISSING, doc quote for STALE_DOC, screenshot for browser). Findings without any evidence form are excluded.

6. **Present the report** to the user with a summary.

## PHASE 4: TRIAGE & PROMOTE

How this phase runs depends on the `--autofix` flag:

### Without --autofix (default — interactive)

Present findings and guide the user through triage. For each finding offer three actions:
1. **Promote** — create a roadmap item spec, add a row to ROADMAP.md
2. **Accept** — record the divergence as intentional; excluded from future runs
3. **Skip** — leave for later

Triage contract (same sequence whether user promotes one finding or twenty):

1. For each confirmed-promote finding, write an item spec in the appropriate roadmap phase directory (same phase as the original item, or a new "fixes" phase when findings cross multiple phases). Shape: `references/triage-templates.md#promoted-item-spec-written-per-confirmed-finding`. Priority derives from finding severity; complexity from scope.
2. Append new rows to `docs/ROADMAP.md` for every promoted spec — never regenerate the table.
3. For each accepted divergence, append to `.devlyn/preflight-accepted.md` (shape in triage-templates.md). These are filtered out in Phase 3 of every future preflight run.
4. **STALE_DOC findings are always fixed directly** — ROADMAP status, item spec frontmatter, VISION.md "What's Next". Factual corrections, not implementation decisions.
5. Print the triage-complete summary per the template.

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
