# `.devlyn/PREFLIGHT-REPORT.md` — Required Shape

Render the report with the exact section order below. Severity order is CRITICAL → HIGH → MEDIUM → LOW. Categories surfaced from auditors (MISSING / INCOMPLETE / DIVERGENT / BROKEN / SCOPE_VIOLATION / UNDOCUMENTED / STALE_DOC / PRINCIPLE_VIOLATION) are printed as-is, never re-classified by the synthesizer.

Each finding MUST include: `[CATEGORY]` prefix, the commitment id, the commitment text, file:line evidence (or a "searched and not found" statement for MISSING), and a one-line impact. After PHASE 3.5 runs, findings adjusted by Round 2 carry an inline `[R2: <CONFIRMED|REVISED|RETRACTED|NEW>]` prefix. Findings without evidence are excluded from the Findings section and surfaced in `Synthesis diagnostics` instead, per the `<evidence_standard>` in SKILL.md.

```markdown
# Preflight Report
Generated: [timestamp]
Scope: [phase N / all]
Previous run: [timestamp / none]
Coverage: [full / limited (browser skipped) / limited (docs skipped) / limited (browser+docs skipped)]
Round 2: [skipped (no triggers fired) / CONFIRMED / REVISED / BLOCKED / timeout]   ← always present; populated by PHASE 3.5
[If Round 2 ran: cross_model: <true|false>, reason: <engine=claude|codex-unavailable|null>]

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
| PRINCIPLE_VIOLATION | [N] |
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

## Synthesis diagnostics
<!-- iter-0019.A: surfaces what the deduplicator suppressed so PHASE 3.5 (Round 2) can judge it from the report alone. Always present; "None" when both lists are empty. Do NOT move suppressed findings into the Findings section — that violates evidence-clean ordering. -->

### Material auditor disagreements (post-dedup, pre-R2)
- `(rule_id|commitment_id, file:line|locator)` — auditor A said `[CATEGORY-A] severity-A`, auditor B said `[CATEGORY-B] severity-B`. Materiality: <category-mismatch | severity-boundary-cross | involves-CRITICAL>.

### Findings excluded by `<evidence_standard>`
- `source_auditor: <code|docs|browser>`, `category: <CATEGORY>`, `severity: <CRITICAL|HIGH|MEDIUM|LOW>`, `commitment_id: <id|null>`, `rule_id: <id|null>`, `claimed_evidence: "<raw text the auditor wrote>"`, `exclusion_reason: <missing-file:line | missing-search-statement | missing-doc-quote | missing-screenshot>`.

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
- **[SCOPE_VIOLATION]** `1.3` — Goal-locked drift (rule_id: `principle.goal-locked-drift`)
  - **Commitment**: "Spec scope: rate-limit middleware only"
  - **Evidence**: `src/api/auth/login.ts:78` — diff also rewrote unrelated session logic that no commitment requested. Reference principle "goal-locked drift" (`_shared/runtime-principles.md`).
  - **Impact**: Out-of-scope work shipped silently; review burden + regression risk.
- **[PRINCIPLE_VIOLATION]** (no commitment) — Unjustified duplicate machinery (rule_id: `principle.unjustified-duplicate-machinery`)
  - **Evidence**: `src/utils/format-date.ts:12` and `src/components/Timeline.tsx:84` define near-duplicate `formatRelativeTime()` helpers with no spec justification.
  - **Impact**: Drift between the two will eventually produce inconsistent UX; test surface doubled.

### MEDIUM
...

### LOW
...

## Round 2 critique
<!-- iter-0019.A: present only if Round 2 fired. Header `Round 2: skipped` ⇒ omit this section. -->

**Verdict**: <CONFIRMED | REVISED | BLOCKED | timeout>
**Triggers fired**: [list of r2.* trigger ids that activated Round 2]
**Wall**: [N]s

### Adjustments
- `[R2: REVISED]` Finding `<id>`: severity HIGH → CRITICAL — reason: "<one-line>".
- `[R2: RETRACTED]` Finding `<id>`: reason: "<one-line>".
- `[R2: NEW]` `<file:line>` `[CATEGORY] severity` — short statement.

### Notes
- One paragraph of R2 cross-cutting observations: missed evidence patterns, severity calibration drift, etc.

## Documentation Findings
- [STALE_DOC] ROADMAP.md: Item 1.3 status "In Progress" → should be "Done"
- [UNDOCUMENTED] WebSocket real-time updates not mentioned in README

## What's Verified
[Explicitly list areas that passed — balanced feedback prevents over-correction]
- Auth flow: all 5 commitments verified (signup, login, logout, password reset, session management)
- Database schema: matches all spec constraints

## Not Started (Expected — Planned Items)
- 2.1 Real-time Updates — status: planned, 5 commitments
- 2.2 Team Management — status: planned, 6 commitments
These items are acknowledged future work per the roadmap. They will be audited when their status changes to in-progress or done.

## Accepted Divergences (from previous runs)
- [list any, or "None"]
```

## Commitment Registry shape (`.devlyn/commitment-registry.md`)

Phase 1 writes the registry in this shape so every auditor sees the same grading rubric.

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
