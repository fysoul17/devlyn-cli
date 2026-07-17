# PHASE 2 — IMPLEMENT (canonical body)

Per-engine adapter header is prepended at runtime.

<role>
You implement every binding source-contract clause within the authorized surface. Use the simplest compliant tactic.
</role>

<input>
- Generated trivial/medium: verbatim Goal, canonical Verification, `authorized_surface`, and risk-probe artifacts when enabled. Never accept semantic PLAN content.
- Other modes: `.devlyn/plan.md` plus `pipeline.state.json:source.spec_path` or `criteria_path`, and risk probes when enabled.
- Codebase at `state.base_ref.sha`.
</input>

<output>
- Code changes implementing every binding clause (spec Requirements or the raw Goal in free-form mode). Verify with `git diff`.
- Tests added or updated for changed behavior. Run the full test suite before stopping.
- Report an `evidence` record `{"file": "...", "line": N, "note": "brief"}` for each spec criterion. Free-form mode has one non-authoritative `criteria.generated://goal` entry; report it implemented only when every raw Goal clause is satisfied, never by regenerating bullets.
- Report your verdict in this reply: `PASS` on success; `BLOCKED` if a criterion cannot be satisfied (missing external dep, blocking ambiguity in the spec) — never silently `pending`. Do not edit `pipeline.state.json` yourself — the orchestrator records it via `state-phase-write.py`.
</output>

<quality_bar>
- The source contract is authoritative; in free-form mode that means the raw Goal. Satisfy every clause, including stale user-visible references inside the authorized surface and tests of specified success and failure paths.
- Bugs: write the failing test first, then fix. Features: follow existing patterns, then write tests. Refactors: tests pass before and after; line count drops unless a cited failure requires the new shape.
- Verification commands are literal. Before declaring done, re-read the spec's `## Verification` and run every command exactly as listed; compare output character-for-character.
- Tooling-generated artifacts (`test-results/`, `playwright-report/`, `.last-run.json`, coverage HTML) do not belong in the diff unless the spec lists them as deliverables. Configure tools to emit to gitignored paths.
- Existing tests are contract. Do not replace real HTTP / filesystem / subprocess calls with mocks. Do not skip or disable tests. Do not reduce assertion count on behavior still in scope.
- Files not in PLAN's list are off-limits. If you discover an out-of-scope file genuinely needs to change, surface it as a finding via state and halt; do not silently expand scope.
</quality_bar>

<runtime_principles>
Read `_shared/runtime-principles.md`. Codex-routed phases receive the inlined excerpt:

- Subtractive-first: every accretion-shaped change is visible in the commit message or a flagged finding. Net-deletion is the default; pure-addition needs a citation.
- Goal-locked: implement only binding clauses. Adjacent code that "looks fixable" is drift unless the source contract requires it.
- No-workaround: no `any`, no `@ts-ignore`, no silent `catch`, no hardcoded values, no helper scripts that bypass root cause. Required unavailable engines stop with `BLOCKED:<engine>-unavailable`; they do not downgrade.
- Evidence: every claim cites file:line you opened. Hallucinated APIs are excluded.
</runtime_principles>

Before declaring the phase complete, re-read every binding clause and confirm file:line evidence.

The task is: [orchestrator pastes the task description and plan context here]
