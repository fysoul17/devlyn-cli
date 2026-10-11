# Historical pair-trigger audit: F23 and I0185

2026-10-10. Read-only audit of completed 0234 evidence. No new model calls,
execution experiments, participant edits, historical regrading or product-rule
changes. This is a bounded design input for the owner after the solo frontier.

## What the evidence supports

A peer can find a consequential defect while an owner reports no unresolved
issue. F23 supplies an actual executed counterexample, repair and successful
recheck. An impasse-only trigger would miss that specific opportunity because
the owner had no recognized impasse. This supports considering an independent
attempt to falsify a consequential boundary change before declaring completion;
it does not establish the cost effectiveness of automatic review, a reliable
risk classifier, or an advantage from using a different engine.

The positive observation belongs to **same-engine H**, not cross-engine P.
0234 admitted neither recipe. Its stricter historical false-completion audit
counted **zero** false completions; this report preserves that classification.
“Confident owner with an unnoticed defect” describes the observed mechanism,
not a retrospective change to that metric.

## Exact F23 evidence and actual activation

Raw evidence root:

`/Users/aipalm/.local/share/nx01/0234-live/out/`

Line numbers below refer to each cell's `run/stdout` JSONL. Only visible
commands/results and assistant messages were used. All three cells received
the same F23 request; `d25-F23-codex-H-r1/harness/caller.json` has the ordering
requirement both in its request paragraph and checklist: priority descending,
then submission time ascending, then ID ascending.

| Cell and lines | Observation |
| --- | --- |
| `d24-F23-codex-B-r1`, 19, 24 | Public suite passes 41 tests; final says “Nothing unresolved.” Codex assessor `assessment/codex/stdout:3` identifies lost submillisecond precision. That assessor finding is a source-derived prediction, explicitly not an independently executed probe. |
| `d25-F23-codex-H-r1`, 10 | Owner recognizes the installed shared-state pair policy and seeks its runner. |
| d25, 23 | Actual `subprocess.run(['codex', 'exec', ...])` starts a separate read-only peer CLI. Its output has thread ID `01a119b2-c761-7e50-a887-6a9cb0b87527`, `turn.completed` and `PEER_EXIT: 0`. This is not a mention of a command or a simulated peer. |
| d25, 30, 33 | Owner reports 36 passing public tests and resumes that peer. The review prompt explicitly says “No unresolved claims from owner.” Peer predicts and then reports an executed ordering counterexample with exit 0 and empty stderr. |
| d25, 34 | Owner acknowledges the new defect and commits to preserving accepted timestamp precision with a regression test. |
| d25, 42 | Third successful resume: owner reports the comparator repair and 37 passing tests. Peer reruns the original and equivalent-fraction/offset cases; both pass. |
| d25, 43 | Final reports 37 passing tests and no unresolved issue. Both `assessment/codex/result.json` and `assessment/claude/result.json` record `complete: true`. This is the recorded completion judgment, not exhaustive proof of correctness. |
| `d26-F23-codex-P-r1`, 45, 48 | Cross-engine review occurred, public suite passes 40 tests, and final discloses a quantity limitation with no other unresolved issue. Codex assessor `assessment/codex/stdout:3` still identifies the same precision defect by source review. |

The decisive d25 peer counterexample has equal priorities and only one unit
of stock. Order `a-later` has `2027-01-01T00:00:00.0002Z`; `z-earlier` has
`2027-01-01T00:00:00.0001Z`. Expected: accept `z-earlier`. Observed before
repair: accept `a-later`, reject `z-earlier`. Validation accepted both inputs,
but `Date.parse` collapsed them into one millisecond, wrongly activating the
ID tie-break. The repair compares normalized fractional digits before ID when
parsed times tie. The final peer also verifies that equivalent `.000100`
timestamps with offsets still tie correctly. Thus the useful contribution was
a new, request-grounded counterexample, not agreement or another green suite.

**Diagnostic limitation:** d25 `diagnostics.json` records `peer.launched: 0`
and no turns, despite stdout lines 23, 33 and 42 containing the actual launch
and two successful resumes. The raw commands and returned session evidence
prove activation. This audit does not repair that historical diagnostic or
infer absent calls from it. The cell's recorded accounting is COMPLETE.

**Snapshot limitation:** the first peer read the starter before implementation,
then its probes ran after the owner had edited. Its initial “no command/tests”
finding was stale and subsequently withdrawn. The second, decisive turn
reviewed the implemented source. A future narrow review should bind its input
and executable checks to one stable source version; the first turn does not
prove that design dialogue itself caused the successful repair.

## Cost and comparison limits

Recorded full-cell totals, from `0234/results/cells.md:30–32`:

| F23 Codex arm | Recorded completion | Wall seconds | Input tokens | Output tokens |
| --- | --- | ---: | ---: | ---: |
| B | incomplete | 169 | 128,432 | 6,454 |
| H | complete | 246 | 798,746 | 13,510 |
| P | incomplete | 395 | 862,513 | 28,139 |

These are full-cell totals, not isolated review costs or repeated-effect
estimates. One successful H draw cannot establish expected resource savings,
cross-engine complementarity, or a solo ceiling. `0234-pair-reasoning.md:93–108`
records H/B as exploratory only: Codex development H 1/2 versus B 0/2, P 0/2;
no admission. Cross-engine P added roughly 2.3–3.5 times B's development input
without a completion gain. Claude easy P had 2.10 times B's input and 1.36
times its wall even without launching a peer, so trigger/decision overhead
must be measured too.

## I0185: review and repair can introduce a different failure

The relevant boundary is lock ownership and rollback across commit/release,
not simply “the tests are green.” The completed historical adjudication is
`autoresearch/experiments/0234/results/adjudication.md`:

- Lines 48–59: Claude B d03 has four witnessed defect types; P d05 has three,
  including a new `release-peer-lock` failure that B lacks. Partial defect
  reduction and regression must both remain visible.
- Lines 244–265: the first release really removes the current lock, reports
  failure, and another invocation obtains a new lock at that path. A blind
  retry then deletes the peer's lock. The witness uses a real peer process.
  It directly binds to the request's requirement to release only the current
  invocation's lock and preserve another owner's lock/data.
- Lines 307–316: d03's stranded-lock/alias defects and d05's failure to restore
  after a release fault were reproduced; broad pairing did not close them all.
- `0234/results/audit.md:78` records d05's public 5 plus regression 11 tests
  passing and its peer's “No remaining evidence-supported blockers.” The
  surviving defects remain coverage failures under the frozen audit rule.

This is evidence against automatic acceptance of a peer's proposed repair or
closure. Independent checks must protect the neighboring invariant as well
as reproduce the reported bug. More conversation alone supplies no guarantee.

## Prospective hypothesis, not a product instruction

0234 already tried automatic activation: correctness depending on the order
of multiple rules or shared state across operations (`0234-pair-reasoning.md:38`).
Its installed `d25.../cell/work/.agents/skills/_shared/pair.md:3–25` says **at
most three turns**, prescribing independent positions, reciprocal development
and closure. d25 actually used all three. Reinstating that whole recipe would
repeat a rejected treatment.

A distinct, smaller hypothesis is **one independent attempt at an executable
counterexample on a consequential boundary in a stable candidate**, even when
the owner feels done. Possible development boundaries supported by these two
tasks are: accepted inputs collapsed by a representation used for ordering or
identity; and ownership/rollback transitions across commit and release. These
are candidate selection features, not a validated exhaustive classifier.

The peer would receive the original contract and relevant stable source, try
to falsify one invariant, and cite the visible obligation plus expected/actual
behavior. A supported finding leads to repair and a check of that finding and
affected neighboring invariants. A clean first review does not require two
more dialogue turns. This is an empirical hypothesis; the historical success
occurred on turn two after prior context, so a fresh one-turn peer is **not yet
shown** to reproduce it.

If the owner later registers this candidate, compare against the best accepted
solo and an equally scoped solo verification attempt; distinguish a fresh
same-engine peer from a cross-engine peer. Charge selection, failed calls,
repair and rechecks to total end-to-end cost. F23/I0185 are exposed development
evidence, not untouched confirmation. Retain the registered quality and
per-success resource gates, including their per-engine limits. No product
change, launch or admission is requested by this report.
