# 0121 — Record PLAN failure when no plan was produced

## Intent and observed failure

An unavailable fresh PLAN worker must leave an explicit, completed BLOCKED phase so the operator can diagnose the failure. In the actual 0120 R1 run `rs-20260906T173436Z-5a086a70590e`, the worker exited 1 before producing `plan.md`. The prescribed `complete --verdict BLOCKED --engine-session-log .devlyn/plan.worker-session.0.jsonl` was rejected by schema3 output hashing, leaving the phase unfinished. Raw evidence remains immutable under main `.devlyn/0120-harness-direction-20260906/entry-calibration-r1/` and its owned archive.

## Required behavior

- For schema3 PLAN completion with caller verdict BLOCKED and lexically absent `plan.md`, persist the phase completion time, duration, BLOCKED verdict and null output digest. Continue the existing receipt/session attestation path; failed or malformed attestation remains visible, with null effective model and a nonzero command result where currently required.
- A null PLAN digest is valid only for this terminal missing-output BLOCKED state while the path remains lexically absent. No fabricated plan, digest or effective model. A directory, dangling symlink, unreadable file, removed bound output or changed bound bytes must not qualify as absence.
- Such a completed phase permits final-report lifecycle operations, but cannot authorize PLAN re-dispatch, IMPLEMENT, PROBE or other work. Failed transitions remain atomic and cannot open the next phase.
- Existing output is bound and revalidated even on BLOCKED. PASS and other verdicts still require the plan artifact. Preserve successful paths, bounded ordinary PLAN correction, non-schema3 compatibility and all existing receipt validation.
- Preserve the finish gate and terminal precedence. A missing authorized surface may still yield `BLOCKED:finish-gate-unclean`; this fix makes the originating phase truthful, without making the run shippable.

## Scope and validation

Change only canonical `_shared/state-phase-write.py`, its tracked installed mirror, and the matching state-schema contract/mirror if its existing unqualified hash rule needs correction. Extend existing self-tests with actual CLI/state-file regressions for the observed schema3 failed worker, final-report closure, refused nonterminal spawn/transition, success without output, bound output deletion/tampering, nonregular paths and malformed receipt. Do not construct a new test framework. Run the module self-test, receipt self-test and required skill lint; preserve raw commands/results. Obtain independent Fable 5.1/Grok 4.6 advice and root adjudication on the final change.

This is a bounded repair through the pinned Codex implementation route, authorized by the user's continuation instruction. It does not enter a new resolve run inside the diagnosed broken entry environment. No public knob, runtime permission change, model routing change, A16 mutation or performance claim belongs to this patch. A subsequent fresh entry calibration will test the repaired runtime separately.

Principles: **No workaround** preserves absent evidence honestly; **No overengineering** extends existing validators and tests; **No guesswork** uses the actual failure and preregistered assertions; **Production ready** requires a truthful failure lifecycle.
