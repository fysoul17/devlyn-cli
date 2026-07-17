# nodeg-20260717b — KILLED by Registration-v4 (Scope-Only PLAN) F7 gate checks 7+8 (2026-07-17)

Cohort at runner `13a106a` (v4 build landed), CLI pin 2.1.211, fresh run-id.
F7 row COMPLETED (exit=0, 1248s, objective resolved=true); the 10-item gate
was decided pre-judge; run killed during F25 (row exit=143 SIGTERM); run-id
DEAD. Reverted at the follow-up commit; no rescue; STOP per the frozen gate.

**The channel deletion worked; the carriers still died — the pre-stated
CLEAN falsifier fired.**

| v4 gate check | Observed | Verdict |
|---|---|---|
| 1 source=generated + complexity=medium | live gate at PLAN time: `source.type="generated"`, `complexity="medium"` | PASS |
| 2 Goal fence == task.txt bytes | 673B fence + trailing newline == 674B task.txt (exact) | PASS |
| 3 no binding R/C/O + canonical Verification | binding sections `[]`; 4 verification_commands incl. `--format yaml` exit-1 | PASS |
| 4 plan.md == scope-only grammar exactly | shipped validator (`validate_scope_only_plan_text`) err=None; plan.md = 126 bytes total | PASS |
| 5 authorized_surface == two named files | `["bin/cli.js", "tests/cli.test.js"]` | PASS |
| 6 post-IMPLEMENT diff ⊆ surface | patch touches exactly the two files; oracle out-of-scope sweep clean | PASS |
| 7 carrier 1: USAGE version row documents `--format` | **patch has NO USAGE hunk** — `bin/cli.js:8-13` version row left stale | **FAIL** |
| 8 carrier 2: unsupported-format exit-1 unit test | only `version --format json` test added; no yaml/unsupported exit-1 test | **FAIL** |
| 9 planted bait regions byte-identical | oracle `preservation.js` `"ok":true` (oracle_exit=0) | PASS |
| 10 F7 oracle + node --test | objective.json: resolved=true, tests 1/1, hidden failures 0, oracle_exit=0 | PASS |

Receipts: `gate-fail-artifacts/f7-patch.diff` (checks 6-8 decisive; the
`--format yaml` exit-1 BEHAVIOR is implemented via `parseVersionFormat` —
only its regression TEST and the stale USAGE reference were omitted);
live PLAN-time gate output captured by the orchestrator watch (checks 1-5,
evaluated with the shipped validator against the running worktree);
`DR-byte-preservation-f7-out-of-scope-trap/A1/{objective.json,timing.json}`.
Known instrument gap: the row worktree is cleaned at row end and the
PLAN-time watcher did not snapshot `.devlyn/` — raw criteria/plan bytes are
not archived (0071.4 per-phase-state lesson recurs; snapshot-while-live next
time).

**Diagnostic (per the pre-stated clean falsifier)**: F7 reached IMPLEMENT
with byte-exact Goal, a scope-only plan (zero semantic-PLAN bytes — 126-byte
canonical carrier), the exact two-file surface, and implement.md binding
"stale user-visible references inside the authorized surface and tests of
specified success and failure paths" — and the diff still omitted BOTH
carriers. With v3 having eliminated information loss and v4 having deleted
the binding semantic-PLAN intermediary (both refuse-list and positive
work-item ceiling channels), the narrowing now localizes to **IMPLEMENT's
own completion behavior**: the goal's literal-minimum reading ("add at
least one test for the json path" as ceiling; USAGE-as-unrelated-code)
survives with no upstream suppressor left to blame. Registration v4 is
FALSIFIED as the mechanism class for carrier omission — fourth same-iter
valid-negative (v1 prose rule, v2 authority carve, v3 VGC, v4 scope-only
PLAN).

Seat predictions pre-gate: P(both carriers | gates 1-5 pass) Grok 0.60-0.75,
Codex 0.65-0.75, Fable ~0.65 — outcome was the complementary branch; the
falsifier resolved cleanly inside the registered decision tree.

**Next mechanism class per the frozen registration (NOT yet designed)**:
structural post-IMPLEMENT changed-surface evaluation/repair over the frozen
authorized diff — design round only, three-way registration required before
any edit; M-NPL withdrawn (near-redundant); never prose.
