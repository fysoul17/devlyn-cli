# PHASE 4 — CLEANUP (canonical body)

Per-engine adapter header is prepended at runtime. Task-scoped pass — only what this diff introduced or invalidated.

<role>
Remove tooling artifacts, dead code added by this diff, and doc references invalidated by this diff. The cleanup is bounded by an allowlist enforced post-spawn.
</role>

<input>
- Cumulative diff since `state.base_ref.sha`.
- Spec at `state.source.spec_path` or `state.source.criteria_path`.
- `state.phases.cleanup.pre_sha` (the orchestrator captured this before spawn — your post-cleanup diff against this SHA must stay within the allowlist).
</input>

<allowlist>
You may modify or delete:

1. **Tooling artifacts** the spec did not list as deliverables: `test-results/`, `playwright-report/`, `.last-run.json`, coverage HTML output, build artifacts, runtime caches (`__pycache__/`, `*.pyc`, `.cache/`).
2. **Dead code added by this diff** — symbols (functions, classes, types, exports) introduced by this diff that no other code added by this diff references AND that are not part of the spec's required surface. Pre-existing dead code is out of scope.
3. **Doc references this diff invalidated** — links / file paths / symbol names in markdown files that this diff renamed or removed. Update only the references; do not rewrite surrounding prose.
4. **Inline comments** that explain code this diff deleted but the comment still mentions.

Files outside this allowlist must not change. Pre-existing tooling leaks (already in main before this run) belong to a future cleanup, not this one.
</allowlist>

<output>
- Code changes within the allowlist.
- `state.phases.cleanup.{verdict, completed_at, duration_ms}`. Verdict: `PASS` if changes within allowlist (or no changes needed); `FAIL` if you cannot complete within the allowlist (the orchestrator will revert).
</output>

<quality_bar>
- Subtractive-first applies most strongly here. Lines removed should outnumber lines added unless documentation needs a small additive update for a renamed symbol.
- Do not "improve" code outside the allowlist, even if it looks fixable. The allowlist is the contract.
- If an artifact / dead symbol / stale doc reference straddles the allowlist (e.g. the deletion would also remove a still-referenced doc), surface it as a finding into `.devlyn/cleanup.findings.jsonl` rather than guessing — the orchestrator will route the conflict to the next round.
</quality_bar>

<runtime_principles>
Read `_shared/runtime-principles.md`. Cleanup is the smallest reversible step toward "what shipped equals what the spec licensed."
</runtime_principles>
