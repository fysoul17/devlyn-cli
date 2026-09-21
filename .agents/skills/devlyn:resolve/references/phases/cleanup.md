# PHASE 4 — CLEANUP (canonical body)

The selected IMPLEMENT worker performs code/doc cleanup in its existing invocation before its final checks. The owner then uses the CLEANUP span for generated-artifact removal and invariant checks only; no new model call.

<input>
- Cumulative diff, original spec and immutable PLAN authorized surface.
- CLEANUP `pre_sha`: tracked source and HEAD must remain unchanged during owner checks.
</input>

<allowlist>
Within IMPLEMENT and PLAN authorization, you may modify or delete:

1. **Tooling artifacts** the spec did not list as deliverables: `test-results/`, `playwright-report/`, `.last-run.json`, coverage HTML output, build artifacts, runtime caches (`__pycache__/`, `*.pyc`, `.cache/`).
2. **Dead code added by this diff** — symbols (functions, classes, types, exports) introduced by this diff that no other code added by this diff references AND that are not part of the spec's required surface. Pre-existing dead code is out of scope.
3. **Doc references this diff invalidated** — links / file paths / symbol names in markdown files that this diff renamed or removed. Update only the references; do not rewrite surrounding prose.
4. **Inline comments** that explain code this diff deleted but the comment still mentions.

Files outside this allowlist must not change. Pre-existing tooling leaks (already in main before this run) belong to a future cleanup, not this one.
</allowlist>

<output>
The owner removes only run-owned untracked/ignored generated artifacts from item 1, preserving deliverables, evidence and recovery inputs. It records PASS when the source checkpoint is unchanged and no cleanup finding remains. A code/doc finding returns through the selected IMPLEMENT repair route and reruns BUILD before fresh VERIFY. Never modify source inside owner CLEANUP or reuse stale checks. Record lifecycle via `state-phase-write.py`.
</output>

<quality_bar>
- Subtractive-first applies most strongly here. Lines removed should outnumber lines added unless documentation needs a small additive update for a renamed symbol.
- Do not "improve" code outside the allowlist, even if it looks fixable. The allowlist is the contract.
- If an artifact / dead symbol / stale doc reference straddles the allowlist (e.g. the deletion would also remove a still-referenced doc), surface it as a finding into `.devlyn/cleanup.findings.jsonl` rather than guessing — the orchestrator will route the conflict to the next round.
</quality_bar>

<runtime_principles>
Read `_shared/runtime-principles.md`. Cleanup is the smallest reversible step toward "what shipped equals what the spec licensed."
</runtime_principles>
