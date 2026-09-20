# 0197 — review repairs defects; fresh-context advantage remains unobserved

2026-09-21 KST. Root direct, no resolve invocation, including controls. Actual
comparison, not another static utility audit. Native Astra/high generated two
implementations of the planned history-lifecycle R6 inventory on copied real source.
Each received continued-thread review (S) and fresh-thread review (F), followed by
identically configured fresh repair workers. All ten scheduled calls finished once.
[Protocol](../experiments/0197/PROTOCOL.md), [request](../experiments/0197/request.md).

## Result and decision

Both routes produced two substantiated finding closures, on one initial product
each. Fresh context did not show additional closure benefit in this sample. Review
connected to validation and repair had observable value; the necessity of fresh
context or a complete resolve phase graph is not established. No full control or
no-review repair arm exists here. Keep our direct route and actual verification;
no new instruction/default, customer-routing change or lifecycle feature ships.

The frozen oracle passed all six products:41 actual-CLI inventory cases, the existing
33-test self-test command and the supplied/added unittest command (43/43 rows), plus
file scope. **This is oracle-complete, not product-complete.** The reference and oracle
missed two valid review counterexamples. Independent source review also exposed a
root-authored specification ambiguity about real receipt metadata. Do not use the
frozen ceiling or a post-hoc conjunction to declare an overall completion-rate winner.

| Product | Frozen rows + scope | Whitespace checkout | Case-alias receipt | Real allocated receipt schema* |
| --- | --- | --- | --- | --- |
| Initial1 |43/43 PASS|wrong checkout|receipt missing|BLOCKED|
| Initial2 |43/43 PASS|wrong checkout|receipt missing|listed|
|1-S repair|43/43 PASS|wrong checkout|receipt missing|BLOCKED|
|1-F repair|43/43 PASS|correct|correct|BLOCKED|
|2-F repair|43/43 PASS|wrong checkout|receipt missing|listed|
|2-S repair|43/43 PASS|correct|correct|listed|

*The schema column is an observed compatibility check under an ambiguous request,
not a retroactive primary criterion. In particular, do not relabel this as an
unqualified S1/2 versus F0/2 overall success result. All products remain research
artifacts. One task, two initial draws and one repair draw per review cannot establish
reliability equivalence or separate review effects from repair sampling noise.

## What was actually found and repaired

Two defects were independently emitted by1-F and2-S:

- `command()` strips stdout. The new history route reused it to obtain Git paths;
  repositories named `base` and `base ` therefore made the latter inventory the
  former. Both repairs add a path-specific Git reader that removes only the record
  newline. Same isolated fixture: initial wrong, corresponding repair correct.
- On the tested case-insensitive filesystem, `abc/receipt.json` and
  `ABC/receipt.json` are the same actual file. A dictionary keyed by scanned names
  nevertheless reported receipt-missing for run id `ABC`. Both repairs resolve
  the specified path through the filesystem while retaining metadata/link checks.
  The replay proves `samefile`; this is not simulated case folding.

`SUPPLEMENTAL-RESULTS.json` retains42 post-seal CLI replays: six cases across six
products and the calibration reference. The reference also misses both defects.
Each replay preserves fixture bytes/modes and records stdout/stderr. Predictions
precede replays in `SUPPLEMENTAL-PREDICTIONS.md`. These are exploratory finding
adjudication, not new frozen primary cases or additional model draws.

1-S emitted a different claim:2,000 unmatched array openings would raise an uncaught
RecursionError. Its fresh repair worker actually tested it and rejected it. Root
replayed2,000 and100,000 openings in both state and receipt metadata on all products
and the reference: Python3.14.6 returned BLOCKED JSON, with no traceback or mutation.
The emitted counterexample is unsupported on this runtime; this is not a universal
claim about every nesting failure or Python version. S emitted3 findings,2 substantiated
and closed; F emitted2, both substantiated and closed.2-F's empty review missed both
path defects. No harmful repair was observed on frozen or reproduced unambiguous cases.

## Independent review and the admission failure

Fable5.1 and Opus5 reviewed neutral-labelled source and claims before the comparison
table. Both found an operator-facing HIGH incompatibility that the four native reviews
missed: Initial1/1-S/1-F require an object-valued `task` in receipts, but actual
`allocate` stores the task description as a string. A real allocated receipt schema,
with fixture paths rebound, makes all three BLOCK. Initial2/2-F/2-S and the reference
accept it. Source: first family's `history_metadata` at711–715; existing
`allocate` writes `task=args.task` at187. `ADDITIONAL-REPLAY-RESULTS.json` preserves it.

The root-authored request's generic sentence about `task` types can be read as applying
to both state and receipt. It conflicts with the actual receipt schema; the two initial
implementations chose different readings. The reference and frozen fixtures omitted
this integration boundary. This is a specification/admission defect, not a reason to
silently rewrite the frozen request after observing outcomes. The compatibility result
must remain visible, and no production-ready or overall completion ranking follows.

Both blinded reviewers also endorsed the RecursionError claim; Fable asserted100,000
openings reproduced everywhere. Actual replay contradicts that specific claim. Their
agreement did not override execution. Fable's additional300-character-id regression
claim is retained separately: absent receipt containers return receipt-missing in all
products; with an existing container, filesystem ENAMETOOLONG makes the two repaired
products visibly BLOCK. The request requires visible filesystem errors, so this is
not counted as harmful repair. The initial non-triggering fixture and subsequent
triggered fixture are both retained; no invisible reroll or criterion change occurred. The prediction file was appended
after the first long-id result to register the second fixture; it is not blanket
pre-registration of every later source-review probe.

## Runtime, cost and fidelity

Native `codex exec resume <thread>` preserves the implementer's actual session;
no pasted reconstruction substitutes for continuation. Read-only nonce qualification
and a full-access shell→read-only transition both passed. The revised launcher gates
only new turn contexts. S includes prior tool/test history, native session state and
context pressure; it is not a pure experiment on author bias. Native CLI versions:
Codex0.155.1, Python3.14.6. [Official resume usage](https://developers.openai.com/codex/noninteractive/).

All four reviews used identical paired packet hashes, Astra/high/read-only, zero
tool calls and no observed compaction. All generation/repair contexts also reported
Astra/high. Both repairs per pair start fresh with identical prompts/caps, including
empty or rejected reviews. No result was selected, rerolled or root-repaired.

| Added review + repair, two draws | Native seconds | Incremental output tokens |
| --- | ---: | ---: |
| S continued |444.888|10,472|
| F fresh |505.302|11,612|

Shared initial generation:696.962s and19,472 output tokens. Ten-call total1647.152s.
These are native return times, excluding preparation, external assessment, peer
adjudication, root replays and delivery. Equal stage ceilings are not equal actual
expenditure; service/cache variance and n=2 preclude a general speed or billing claim.
S/F incremental input tokens were948,855/1,032,569, including684,288/826,880 cached.
Reasoning is included in output tokens and is not added again. Raw resumed counters
are cumulative: subtract the sealed initial counters before summing stage usage.
`RESUME-USAGE-CORRECTION.json` checks both deltas against native `last_token_usage`;
`RESULT.raw-counter-sum.json` preserves the preliminary sum and is not the cost result.

Root audited79 native shell commands and13 patch events: no observed reference,
sibling-product, publication or external-task access. Generation/repair isolation is
instructional with full-access tools, not a filesystem sandbox. All59 registered
inputs, six product seals and source modes match; original checkout WIP and historical
reports remain unchanged. Raw stdout, stderr, rollouts, process observations, prompts,
checks and source/Git remain recoverable under `.devlyn/0197` and `../0197-participants`.

Before draws, Fable/Opus findings improved the oracle, outcome classification, effective
sandbox checks and scoring rules. Final calibration: original0/41; reference and size-
primitive alternative41/41; common-dir mutant40/41; glob and ownership mutants30/41.
The alternative is not an independent implementation. Launcher regression tests6/6,
reference regression calibration, and repository full lint passed. Grok's initial
advisory attempted tools and ended without findings; it was not a PASS. Opus substituted.
Delivery/CI/owned-scratch cleanup authority is `.devlyn/0197/FINAL.md`.

## Historical answer and next frontier

Complex work has shown benefits: [0175](0175-routing-boundary.md)'s SQLite leasing
review found ownership-breaking precision loss and one full run repaired it, though
all routes retained another unmet requirement. [0185](0185-harder-installation-comparison.md)
completed native0/2, direct-guidance0/2, full1/2, with traced lock/recovery fixes. Those observations
support stronger review and repair on difficult work; they do not isolate every full
phase's necessity. [0196](0196-resolve-utility.md) retains the broader audit and costs.

Before another efficacy draw, reconcile state versus receipt field types against real
producer output and admit the oracle with actual allocated receipts. Use an untouched
natural task/confirmation; do not tune and rerun this exposed exam as confirmation.
Preserve this frozen request, including its ambiguity, and both observed interpretations.
No new reminder, replacement framework or full control is warranted by this result.
Mission1, independent field gate15 and untouched confirmation remain OPEN; preserve A16.
