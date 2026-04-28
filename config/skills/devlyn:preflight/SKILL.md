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
  - `auto` (default): code-auditor uses Codex (SWE-bench Pro +11.7pp for code analysis), docs-auditor uses Claude (writing quality), browser-auditor uses Claude (Chrome MCP). Requires the local `codex` CLI on PATH; on failure the engine pre-flight silently downgrades to `claude` per `config/skills/_shared/engine-preflight.md`.
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

Engine routes per the auto-resolve skill's `references/engine-routing.md` ("Pipeline Phase Routing (preflight)" → CODE AUDIT row): Codex on `--engine auto`/`codex`, Claude on `--engine claude`. When the route is **Codex**, shell out `bash .claude/skills/_shared/codex-monitored.sh -C <project root> -s read-only -c model_reasoning_effort=xhigh "<auditor prompt with commitment registry inlined>"` — the registry must be pasted into the prompt because Codex has no filesystem access under read-only. The wrapper closes stdin and heartbeats every 30s on stderr so the long code audit doesn't starve the outer API byte-watchdog (iter-0008 mechanism); rationale in `_shared/codex-config.md`. When the route is **Claude**, spawn a subagent with `mode: "bypassPermissions"`. Read the auditor prompt from `references/auditors/code-auditor.md` either way.

**Diff-context signal** (added iter-0019.A): if preflight was invoked with an explicit base ref (e.g. from auto-resolve `--autofix` verification pass with `base_ref.sha` available, or a user-passed `--base-ref` flag), include `base_ref_sha: <sha>` in the spawn prompt so the code-auditor's principles pass can fire `principle.subtractive-first-violation`. When no base ref is available (standalone holistic preflight), omit the field — the code-auditor will conservatively skip subtractive-first per its rule_id overlay table.

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

Auditors already emit each finding with its **category** (`MISSING` / `INCOMPLETE` / `DIVERGENT` / `BROKEN` / `SCOPE_VIOLATION` / `UNDOCUMENTED` / `STALE_DOC` / `PRINCIPLE_VIOLATION`) and severity (`CRITICAL` / `HIGH` / `MEDIUM` / `LOW`). SCOPE_VIOLATION findings additionally carry `rule_id: "scope.anti-commitment-violation"` so the triggering anti-commitment is traceable. Findings the code-auditor (and, with screenshot/route evidence, the browser-auditor) emits with `principle.*` rule_ids derive from `_shared/runtime-principles.md` — see `references/auditors/code-auditor.md` for the runtime-principle audit pass + the rule_id overlay table. Synthesis passes category + severity through — do NOT re-classify the category or re-severity-label. That would replace domain judgment with orchestrator mechanics.

1. **Read all audit files** in parallel:
   - `.devlyn/audit-code.md`
   - `.devlyn/audit-docs.md` (if exists)
   - `.devlyn/audit-browser.md` (if exists)

2. **Deduplicate** + **track conflicts**: if multiple auditors flagged the same issue, merge into one finding at the highest severity the reporting auditor assigned. Trust the auditor's severity — do not override. **Identity for dedup** (fallback when auditors don't all emit the same fields): primary key is `(rule_id, file, line)` when present; fallback is `(commitment_id, normalized_evidence_locator)` — `normalized_evidence_locator` is the file:line for present-code findings, the searched-path for MISSING findings, the doc section/line for STALE_DOC, the URL/route for browser. **Record disagreements** to feed PHASE 3.5 trigger #2: when the merged set has disagreements that are *material* — category mismatch, OR severity disagreement crossing the blocker boundary (`blocker={CRITICAL,HIGH}` vs `non_blocker={MEDIUM,LOW}` — at least one auditor in each bucket), OR ANY disagreement involving CRITICAL (e.g. CRITICAL vs HIGH is material even though both are blockers) — append the conflict to the Synthesis diagnostics block (step 5 below). LOW-vs-MEDIUM-only disagreements are NOT material; do not record them.

3. **Filter accepted divergences**: if `.devlyn/preflight-accepted.md` exists, remove findings whose (category, commitment) matches an accepted entry.

4. **Compare with previous run** (if `.devlyn/PREFLIGHT-REPORT.md` existed):
   - `RESOLVED`: finding from previous run no longer present
   - `PERSISTS`: finding still present
   - `NEW`: finding not in previous run

5. **Generate `.devlyn/PREFLIGHT-REPORT.md`** per the shape in `references/report-template.md`. Required sections in order: header (timestamp + scope + previous run + `Coverage:` line — always present, value is `full` when no auditor was skipped, `limited (...)` otherwise — and `Round 2:` status line populated by PHASE 3.5), Summary (counts per category), Delta, Commitment Coverage, **Synthesis diagnostics** (added iter-0019.A: full list of material auditor disagreements from step 2 + full list of findings excluded by `<evidence_standard>` — each excluded entry records `source_auditor`, `category`, `severity`, `commitment_id` and/or `rule_id` if present, `claimed_evidence` (raw text), `exclusion_reason` — Round 2 input is report-only so the diagnostics block must surface what the deduplicator suppressed in full, not as a count), Findings (grouped CRITICAL → HIGH → MEDIUM → LOW with category prefix + evidence + impact), **Round 2 critique** (populated only if PHASE 3.5 fires; appended directly after Findings so the user sees R2 verdict adjacent to the findings it reviewed), Documentation Findings, What's Verified, Not Started, Accepted Divergences. Every finding in the Findings section carries evidence per `<evidence_standard>` — shape varies by category. Findings without any evidence form are excluded from the Findings section but listed in Synthesis diagnostics.

6. **Hold user presentation until PHASE 3.5 completes (or skips).** Do not show the report yet — if Round 2 fires it may revise findings; presenting a pre-R2 draft and then a different post-R2 view burns user trust. PHASE 4 step 0 below presents the final report.

## PHASE 3.5: ROUND 2 CRITIQUE (conditional, single optional pass)

The user-framed essence of preflight is "북극성 의도대로 클린하게 잘 구현되었는가" verified via Codex companion pair tickitaka. Round 1 (PHASE 2) emits findings; Round 2 critiques the synthesized report so a second-model pair-check sees what the first round produced. Single optional pass — never iterates further at runtime. Autoresearch-loop developer-invoked preflight (humans iterating the harness itself) may run additional rounds manually.

**5 deterministic triggers** (any one fires Round 2; check after PHASE 3 step 5 writes `PREFLIGHT-REPORT.md`):

1. `r2.findings_critical_or_high` — Summary table shows ≥1 CRITICAL or HIGH finding total (across categories, post-filter).
2. `r2.auditor_disagreement` — Synthesis diagnostics step 2 recorded a material disagreement (category mismatch, OR severity mismatch crossing CRITICAL/HIGH ↔ MEDIUM/LOW boundary, OR any auditor said CRITICAL). LOW-vs-MEDIUM-only is NOT material.
3. `r2.missing_evidence` — Synthesis diagnostics step 5 records ≥1 finding excluded by `<evidence_standard>`. Round 2 sees the excluded set and judges whether evidence reconstruction is possible.
4. `r2.autofix_would_promote_blocker` — `--autofix` flag set AND any finding has severity CRITICAL or HIGH. Auto-promoting a blocker without a second opinion is the failure mode this trigger prevents.
5. `r2.user_explicit` — caller passed `--challenge` or `--pair-round-2` flag (autoresearch-loop developer override).

If NONE fire → skip Round 2. Surface in the report header: `Round 2: skipped (no triggers fired)`.

If ANY fires → run Round 2:

- **Engine** (cross-model when possible — builder ≠ critic): route from the **actual Round 1 engine** (per `state.engine_actual` after the silent-downgrade rule in `_shared/engine-preflight.md`), NOT the requested engine.
  - Actual Round 1 = Codex (i.e. `--engine auto`/`--engine codex` + Codex was available): Round 2 critic is **Claude** (fresh `Agent` subagent, `mode: "bypassPermissions"`). Header: `Round 2: cross_model=true`.
  - Actual Round 1 = Claude (either `--engine claude` OR `--engine auto` that silently downgraded): Round 2 is a fresh Claude critic. Header: `Round 2: cross_model=false, reason=<engine=claude|codex-unavailable>`. Disabling Round 2 entirely would be worse than a same-model second pass under the user's pair-check requirement; just do not pretend it was cross-model.
- **Input**: the synthesized `.devlyn/PREFLIGHT-REPORT.md` ONLY. Round 2 does NOT re-audit the repo from scratch — that wastes spend and re-introduces noise the dedup just removed. Critique focuses on the report's findings, severities, evidence quality, and what the Synthesis diagnostics block flagged.
- **Output**: writes `.devlyn/preflight-round-2.md` with verdict `CONFIRMED` / `REVISED` / `BLOCKED` and per-finding adjustments (NEW findings appended, REVISED findings have severity/category updated with reason, RETRACTED findings marked with reason).
- **Wall-budget abort**: 240s hard cap. Timeout → mark `r2.timeout=true` in the report header, continue to PHASE 4 with Round 1 findings unchanged. Surface explicitly — never silent.
- **Single round only at runtime**. No Round 3 in runtime preflight. Autoresearch-loop developer-invoked preflight is exempt and may run further rounds manually.
- After Round 2 completes (or aborts), re-render the relevant sections of `PREFLIGHT-REPORT.md`: header gets `Round 2: <CONFIRMED|REVISED|BLOCKED|timeout>`; the "Round 2 critique" section is populated after Findings; per-finding adjustments are reflected inline in Findings with a `[R2: <CONFIRMED|REVISED|RETRACTED|NEW>]` prefix. **`BLOCKED` verdict** means Round 2 found a defect in Round 1 the report cannot ship with (e.g. a missed CRITICAL, an evidence-fabrication risk) — surfaces in header, halts `--autofix` (no auto-promotion), and forces interactive triage in PHASE 4. **`RETRACTED` findings** are dropped from Phase 4's active set.

**PHASE 4 active-set rule** (post-R2): triage / autofix consumes the post-R2 active finding set — `CONFIRMED` and `REVISED` findings are triaged at their final severity/category; `RETRACTED` findings are skipped; `NEW` findings (added by R2) are triaged like any other finding. `BLOCKED` verdict halts `--autofix` and forces interactive triage even if the user passed `--autofix`.

**Skip-flag interaction**: `--skip-browser` and `--skip-docs` reduce auditor coverage but DO NOT disable Round 2. They are surfaced in the header as `Coverage: limited (browser skipped)` so Round 2 sees them as evidence quality, not as suppression of a second opinion.

## PHASE 4: TRIAGE & PROMOTE

**Step 0 — Present the final report.** Now that PHASE 3.5 has completed (or been skipped), show `PREFLIGHT-REPORT.md` with the final post-R2 view. If Round 2 was skipped, the report is identical to the PHASE 3 output. If Round 2 ran, the user sees a single coherent post-R2 report — not a draft followed by a revised draft.

How the rest of this phase runs depends on the `--autofix` flag:

### Without --autofix (default — interactive)

Guide the user through triage. For each finding offer three actions:
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
