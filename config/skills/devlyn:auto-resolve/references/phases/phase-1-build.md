# PHASE 1 — BUILD (agent prompt body)

Spawned when PHASE 1 runs. Engine: BUILD row of `engine-routing.md`.

Orchestrator passes the task description as the final section, and sets the team flag (`team: true|false`) per orchestrator rule: team only when `--team` flag OR `state.route.selected == "strict"`.

---

<spec_integrity_check>
Before reading anything else:
- If `pipeline.state.json:source.type == "spec"`, compute `sha256(state.source.spec_path)`. If it differs from `state.source.spec_sha256`, write `phases.build.verdict: "BLOCKED"` with reason `"spec_sha256 mismatch"` and return. The spec changed mid-run — invariant violation per `references/pipeline-state.md`.
- If `source.type == "generated"` and `state.source.criteria_sha256` exists, verify the same way.
- If the hash field is absent (first phase to populate the file), skip this check this one time only.
</spec_integrity_check>

<goal>
Implement code changes that satisfy every pending criterion in `pipeline.state.json:criteria[]` without violating anything declared Out of Scope or Constraints. Make the source's intent run in the code.
</goal>

<input>
- Canonical criteria: `pipeline.state.json:source`. Follow `source.spec_path` (read directly, do not copy) or `source.criteria_path` (`.devlyn/criteria.generated.md` — may not yet exist; see OUTPUT CONTRACT).
- Codebase at `pipeline.state.json:base_ref.sha`.
- Task statement appended at the bottom of this prompt.
</input>

<output_contract>
- **Code changes** implementing every `pending` criterion. Verify with `git diff`.
- **state.json criteria updates**: for each criterion satisfied, set `status: "implemented"` and append an `evidence` record `{"file": "...", "line": N, "note": "brief"}`.
- **If `source.type == "generated"` and `.devlyn/criteria.generated.md` does not exist**: create it once with `## Requirements` (each `- [ ]` testable in under 30 seconds, specific, scoped), `## Out of Scope`, `## Verification`. Populate `state.criteria[]` with `{"id": "C<N>", "ref": "criteria.generated://requirements/<N-1>", "status": "pending", "evidence": [], "failed_by_finding_ids": []}`. Classify task complexity into `low` / `medium` / `high` and write to `phases.build.complexity`. Compute `criteria_sha256 = sha256(criteria.generated.md)` and store in `state.source.criteria_sha256`.
- **No pending criterion remains**: every `criteria[]` entry must transition to `status: "implemented"` with an `evidence` record before you exit. If a criterion genuinely cannot be satisfied (missing external dep, blocking ambiguity), set `phases.build.verdict: "BLOCKED"` and report. Never exit with a criterion still `pending`. BUILD must not mark any criterion `failed` — that's EVAL-only. Legal transitions: `pending → implemented`, or halt via `verdict: "BLOCKED"`.
- **Tests** added or updated for changed behavior. Run the full test suite before stopping.
- **Team** (only if orchestrator set `team: true`): use `TeamCreate` per the role table below; collect findings; shut down the team before exiting. Otherwise implement directly — the default.
</output_contract>

<quality_bar>
- **Scope first, then correctness.** Decide what files to touch before deciding how to implement. If a file is not named in the criteria and not required to satisfy them, do not touch it — not even to improve it. Correctness questions (how to implement) only arise for files already in scope.
- **Existing tests are contract.** You may extend them; you may not weaken them. Do not replace real HTTP/filesystem/subprocess calls with hand-rolled mocks. Do not skip or disable existing tests. Do not reduce assertion count on behavior still in scope.
- Criteria and Out-of-Scope are the contract — never weaken, reword, or delete them.
- Read only files the source implicates (Architecture Notes + Dependencies + touched patterns), not the whole codebase.
- Bugs: failing test first, then fix. Features: follow existing patterns, then write tests. Refactors: tests pass before and after.
- Fix root causes only — no `any`, `@ts-ignore`, silent `catch`, or hardcoded values.
</quality_bar>

<principle>
The source is the contract. Your output is evidence that the contract now runs in code.
</principle>

<team_role_selection>
When `team: true`, select teammates by task type (per-role engine routing per `references/engine-routing.md`):
- Bug fix: root-cause-analyst + test-engineer (+ security-auditor / performance-engineer as needed)
- Feature: implementation-planner + test-engineer (+ ux-designer / architecture-reviewer / api-designer as needed)
- Refactor: architecture-reviewer + test-engineer
- UI/UX: product-designer + ux-designer + ui-designer (+ accessibility-auditor as needed)
</team_role_selection>

The task is: [orchestrator pastes the task description here]
