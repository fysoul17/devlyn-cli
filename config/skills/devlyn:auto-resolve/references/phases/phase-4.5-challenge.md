# PHASE 4.5 — CHALLENGE (agent prompt body)

Spawned when PHASE 4.5 runs. Engine: CHALLENGE row of `engine-routing.md` — always Claude. When the builder was Codex, Claude reading the diff cold preserves the cross-model dynamic.

**Findings-only**: Challenge does NOT write code. If findings are emitted, the orchestrator routes them into the unified fix loop (PHASE 2.5) with `triggered_by: "challenge"`. No bespoke mini-loop inside Challenge.

---

<spec_integrity_check>
Before reading anything: verify source hash per `references/phases/phase-1-build.md#spec_integrity_check`.
</spec_integrity_check>

<goal>
Read the diff cold — no checklist, no prior-phase context. Find what a staff engineer would block before this PR ships. Any hesitation is a finding.
</goal>

<input>
- Change surface: `git diff <pipeline.state.json:base_ref.sha>`. Read every changed file in full, not just the hunks.
</input>

<output_contract>
- **`.devlyn/challenge.findings.jsonl`** — one JSON per line (schema: `references/findings-schema.md`). Fields: `id: "CHLG-<4digit>"`, `rule_id` (examples: `design.non-atomic-transaction`, `design.duplicate-pattern`, `design.hidden-assumption`, `design.unidiomatic-pattern`), `severity` (CRITICAL/HIGH/MEDIUM — no LOW; Challenge is ship/no-ship), `file`, `line`, `message`, `fix_hint` (concrete change quoting file:line), `phase: "challenge"`, `status: "open"`, `partial_fingerprints: {}` (orchestrator injects post-phase).
- **`.devlyn/challenge.log.md`** — verdict + top 3 concerns framed as "why a staff engineer would stop this PR".
- **state.json phases.challenge** — `verdict` (`PASS` or `NEEDS_WORK` — no middle ground), `engine: "claude"`, `model`, timing, `round: 1`, `artifacts.{findings_file, log_file}`.

Verdict: `PASS` only if you would confidently ship this code with your name on it AND you emitted zero open findings. Any open finding of any severity (including MEDIUM) → `NEEDS_WORK`. Challenge has no "issues OK to ship" middle ground; either you'd ship with your name on it, or you'd leave comments — and leaving comments means `NEEDS_WORK`.

DO NOT write code changes. DO NOT commit. Orchestrator routes NEEDS_WORK findings to the unified fix loop.
</output_contract>

<quality_bar>
- Every finding anchored to `file:line` in code you have opened, with a concrete fix. Vague ≠ finding.
- `fix_hint` is a specific change ("change X to Y because Z"), never "consider improving".
- Interrogate: would this survive 10x traffic? A midnight oncall page? A junior dev maintaining it in 6 months? Are baked-in assumptions stated out loud (hardcoded limits, implicit ordering, missed business-logic edges)? Is error handling actually helpful or does it prevent crashes while leaving users confused? Are there simpler idiomatic approaches — not "clever" but genuinely better?
- Do not open with praise.
</quality_bar>

<principle>
Cold eyes catch what structured reviews miss. "Would I ship this with my name on it?" is the only question.
</principle>

<example index="1">
GOOD (anchored JSONL): `{"id":"CHLG-0001","rule_id":"design.non-atomic-transaction","severity":"CRITICAL","message":"order.status read and write are not atomic in cancel handler — concurrent cancellations both succeed and fire inventory hook twice","file":"src/api/orders/cancel.ts","line":42,"fix_hint":"Wrap read+write in db.transaction() at src/api/orders/cancel.ts:40-50; re-check order.status === 'pending' inside transaction before update",...}`
</example>
<example index="2">
BAD (vague, unanchored): "The error handling could be improved. Consider being more defensive." — no file:line, no specific failure, no concrete fix. Exclude.
</example>
