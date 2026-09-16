# 0185 — full review repairs hard failures, but one cleanup race survives

2026-09-17 KST. Mission1: test the easy-task direct-routing hypothesis on a harder
real developer-tool change. Root researched directly; resolve ran only as controls.
User required parking unfinished work at <=15% remaining account usage. Six scheduled
runs finished above that reserve; live counters and30s guard records are retained.

## Result

[Protocol](../experiments/0185/PROTOCOL.md) compares native Astra/high, unchanged0179
direct guidance, and actual same-model full resolve on one fresh request: make the
real `bin/devlyn.js::installSkillsForCLI` recoverable and exclusive across selected
skills, marker, deprecated paths, failure cleanup and cooperating installers. Two
fresh draws per route, fixed order A/B/C,C/B/A; no rerolls or root product repairs.

| Route | Root-complete | Draw1 / draw2 native seconds | Mean return seconds, failures included |
| --- | ---: | ---: | ---: |
| A native | 0/2 | 288.892 / 228.377 | 258.635 |
| B direct guidance, verify/cleanup/repair | 0/2 | 208.918 / 334.471 | 271.695 |
| C actual full, independent primary + repair | 1/2 | 1379.458 / 1609.477 | 1494.467 |

These are observed return times, **not successful-completion speeds for A/B**.
The sole root-complete product is C2 at1609.477s. Frozen external assessment added
3.281/3.181/3.151s per route respectively. Research preparation, root replays/source
adjudication, delivery and account-observation overhead are not pure model compute.

Frozen supplied/held-out checks passed all six; both full archives passed canonical
phase, invocation, role, mechanical, final-report and archive validation. Root source
review and post-seal replays establish the stricter completion column. Preserve
`ASSESSMENT.json` as the mechanical result and `RESULT.json.rows[].root_complete` as the
root outcome; do not overwrite the former or present6/6 as final quality.

## What review repaired, and what it missed

Both full runs' first fresh VERIFY independently emitted the same two HIGH classes:

- Lock release can fail after backups have already been disposed. All four A/B
  products and both pre-repair C products then throw while retaining the new install,
  unable to restore old bytes/modes as Requirement2 demands. The backup-disposal
  exception does not cover lock release. Both C repairs retain originals until
  successful release and restore the prior state on a one-shot release error.
- A terminal destination symlink can point two CLI paths to the same physical skills
  directory while lexical sibling locks remain different. All four A/B products and
  both pre-repair C products permit the contender. Both C repairs derive physical
  destination lock identity and reject it without disturbing the owner.

Both full runs followed NEEDS_WORK → fresh IMPLEMENT → BUILD_GATE → CLEANUP → fresh
VERIFY, then archived PASS. Four emitted finding instances closed in two products;
one previously incomplete product became complete. No new repair regression was
observed in the compared source/replay requirements.

Root found an additional existing C1 interaction after its final PASS:
`install-1-C/bin/devlyn.js:779` releases the recovery lock before `:790` removes a
newly created destination. With a one-shot failure on second-skill publication,
a reentrant installer at that rollback rmdir enters successfully (returns6), leaving
the first owner still mutating the shared destination outside its lock. C1's removal
then fails ENOTEMPTY. This is shared-path rollback, not private backup disposal.
The defect also exists in C1's pre-repair source; the repair did not create it.
C2 keeps destination-absence restoration inside the lock and rejects the contender.
All four A/B products pass this particular interaction but fail the earlier two.

Source identities, exceptions, filesystem snapshots and exact replays are in
`.devlyn/0185/REPLAY-RESULTS.json` and `ADDITIONAL-REPLAY-RESULTS.json`. The two
pre-repair C sources are reconstructed from retained Git commits solely for replay;
they are not additional model draws. Replays record captured HEAD as `source_sha`;
for uncommitted A2/B2 output, the sealed bytes/code_sha256 and retained baseline
diff are the source identity, not HEAD alone. Root never changed a measured implementation.

## Instrument corrections and limits

Before dispatch, calibration rejected the original and three rollback/lock/stamping
mutants while the root reference passed9/9. An initial test named a nonexistent
legacy deprecated directory; corrected before dispatch, with failed tests/results
retained. Runtime staging stamps only the assignment default, matching the real
installer and preserving its sentinel comparison; canonical bodies stay unchanged.

The calibrated checker was incomplete. Its fault sweep mistakenly allowed any
postcommit rmdir failure with a complete new install, conflating lock release with
backup disposal; the reference shares that gap. Neither the frozen suite nor the
first judges closed the C1 rollback-rmdir interaction. These post-seal extensions
are source adjudication, not preregistered confirmatory endpoints.

The first alias replay used an ancestor symlink. All sources rejected the contender
because the sibling lock also aliases through that ancestor. Preserve that negative
control; it was not evidence that the terminal-symlink finding was false. A separately
predicted terminal-symlink replay reproduced the claimed distinction. Of36 retained
replay invocations, the reference's absence-race probe is **not triggered** because
that reference publishes a whole directory, not a second selected skill; do not
count it as a demonstrated reference failure. All measured/pre-repair product
injections used for the outcome were triggered. Prediction documents and both
instrument versions remain under `.devlyn/0185/`.

The task uses the actual synchronous installer function and real files/processes,
with a VM loader redirecting source/destination to disposable fixtures. It does not
exercise the interactive installation UX. One root-authored request on one source,
two draws per route, source-adjudicated additional checks and coded cwd identifiers
limit generalization and blinding. Native service/cache variability is not isolated.

C explicitly used --spec --no-pair --no-risk-probes to hold the engine fixed across
all core roles. It measures the same-model full core, not default OTHER pair/probes.
All phases/independent primary/repair/archive remained mandatory. No installed
high-risk safeguard or routing rule changed. Actual canonical copies match all
registered source bodies after the declared path stamp. No evidence supports
removing safeguards from hard work or treating full execution as proof of success.

## Time and usage

C's recorded phase spans, summed across initial and repair rounds:

| Phase | C1 seconds | C2 seconds |
| --- | ---: | ---: |
| PLAN | 162.112 | 153.416 |
| IMPLEMENT | 464.228 | 625.768 |
| BUILD_GATE | 294.294 | 312.430 |
| CLEANUP | 99.173 | 177.182 |
| VERIFY | 235.015 | 197.707 |
| FINAL_REPORT | 15.026 | 38.641 |

The fresh reviews produced valid fixes, but this experiment cannot establish which
other phase costs are necessary. B's mean return time was5.05% higher than native;
both were incomplete, so this is not a quality-preserving speed claim.

Observed output tokens: A15,252; B15,680; C92,855 **plus missing judge usage**.
C has eight structured parent/worker threads per draw and two text-only judges per
draw. Preserve all native input/cache/output counters in `TELEMETRY.json`; reasoning
is included in output and must not be added again. Whole-run C tokens and actual
billing remain UNKNOWN. No dollar saving or general model ranking follows.

## Decision and retained frontier

Fresh independent review linked to actual repair improved this hard-task sample;
full orchestration still missed a requirement interaction in one draw. Keep existing
risk routing and verification/cleanup/repair. Do not promote the355-word direct
candidate or remove phases from hard tasks based on this sample.

The next bounded improvement target is verification of the complete lock/rollback
lifecycle, including removal of newly created public paths before unlock. Test a
focused review/repair candidate on a disjoint harder task against actual full core;
separate review's value from phase overhead before adopting a cheaper route. Preserve
these exposed failures and the frozen checker; do not tune and rerun this exam.

Registration64 inputs at2026-09-16T14:46Z, SHA256
`3a9c52d5a772e411daa9b56e99d715a344a83c2ea3a3f4fc500b8f9e4ee92fc0`.
All registered inputs and six product seals revalidated unchanged;353 recorded
native commands screened without publication/network/prior-research command matches.
Original user WIP, participant source/Git and recovery evidence remain intact.
Delivery/CI/owned cleanup authority: `.devlyn/0185-delivery/FINAL.md`,
receipt1dfef6c599ae0b1b68b57f13. Mission1 remains active.
