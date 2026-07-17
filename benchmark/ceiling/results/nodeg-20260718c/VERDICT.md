# nodeg-20260718c — KILLED by Registration-v5 F7 gate check 7 (2026-07-18); carrier 2 FLIPPED with clean attribution — first lever-caused closure of iter-0072

Cohort at runner `833f66a` (v5 build + Amendments 2/3), CLI pin 2.1.211,
third fresh run-id of the v5 gate arc (20260718: worker validation-EPERM
BLOCKED; 20260718b: orchestrator skipped the phase — both non-diagnostic,
each fixed by a cross-confirmed amendment). This run is the first fully
DIAGNOSTIC v5 row; run killed pre-judge during F26 (F25 exit=1 recorded,
non-diagnostic; run-id DEAD).

| v5 gate check | Observed | Verdict |
|---|---|---|
| 1 source/complexity | generated + medium (live) | PASS |
| 3v5 Verification parses | 4 cmds incl. yaml exit-1 (live) | PASS |
| 5 surface == two named files | live gate | PASS |
| 6 diff ⊆ surface | final patch touches exactly the two files; oracle sweep clean | PASS |
| 9 bait byte-identical | oracle preservation green (objective) | PASS |
| 10 oracle + tests | resolved=true, tests 1/1, hidden 0, oracle_exit 0 | PASS |
| 11 goal.raw.txt exact + hash | goal_path set; sha `f3467374…` (= exact task bytes, same digest as prior runs) | PASS |
| 12 phases.surface_close + input hash | pre_sha `947dbf71…`, post_sha `ffa624df…`, engine codex, input patch archived | PASS |
| 13 ATTRIBUTION (pre-SC fails 7+8) | input patch: 0 USAGE hunks, 0 unsupported-format test | PASS (diagnostic) |
| 8 carrier 2: unsupported-format exit-1 test | **SURFACE_CLOSE delta = exactly this test** (`assert.throws(run(['version','--format','yaml']), {status: 1})`) | **PASS — FLIPPED BY THE LEVER** |
| 7 carrier 1: USAGE version row documents `--format` | final USAGE block unchanged (`version   Print the CLI version from package.json`) | **FAIL** |

**Result: the omitted class SPLIT.** Under a fresh audit+repair frame with
the obligations delivered VERBATIM (Amendment 2 confirmed working — the
assembled prompt carried UVR-STALE word-for-word) and dispatch
mechanically enforced (Amendment 3), the worker:

- fired PATH-TEST correctly → carrier 2 closed, mechanically attributed
  (pre-SC input patch lacked it; the SC delta is exactly the test;
  byte receipts in gate-fail-artifacts/). **First lever-caused carrier
  closure in five registrations.**
- read the USAGE block (worker log shows bin/cli.js:8 opened) and
  silently declined UVR-STALE — final message was bare PASS + the test
  diff, no stated reasoning. The stale user-visible reference survives
  its SIXTH channel (v1/v2 prose, v3 info-preservation, v4 semantic-PLAN
  deletion, v5 IMPLEMENT-binding, v5 SURFACE_CLOSE audit frame with the
  obligation named to its face).

Per the frozen gate (ALL checks must pass): NO-SHIP; all v5 surfaces
reverted; valid-negative; STOP. Neither pre-registered falsifier branch
fired cleanly — "both carriers flip" (ship) and "post patch fails 7+8"
(class-dead) both assumed the class was uniform. It is not:
**test-shaped closure is lever-reachable; documentation-sync closure is
not, in this frame, on this seat** (SURFACE_CLOSE ran on codex via the
executor pin; the blind-preferred bare B arm does close USAGE — seat/
frame interaction unmeasured).

Recorded amendments that remain LEARNINGS (code reverted with the build):
Amendment 2 (workers execute nothing; validation belongs to the next
mechanical gate; phase bodies pass VERBATIM — closes the
assembly-gloss channel) and Amendment 3 (declared conditional phases are
state-enforced at the VERIFY merge boundary — orchestrator-skip becomes
mechanically fatal). Both fixed observed, reproduced harness-failure
classes and bind any future phase addition.

Next round (three-way, design only, receipts above): the residual class
is exactly ONE obligation — stale user-visible reference sync. Candidate
axes recorded for the round (not designed): seat-fitness for the audit
frame (claude-routed SURFACE_CLOSE vs codex); obligation decidability
(UVR-STALE as currently worded requires a semantic "documents S's old
interface" judgment the codex seat declines silently); mechanical
UVR derivation (grep-adjacent staleness detection was rejected in r5 as
fixture-literal-shaped — revisit with the split receipt). Never prose.
