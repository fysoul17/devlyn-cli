# 0227 diagnosis — why a correct reference was blocked

After [0227](../RESULT.md) ended NOT PASS on one reference false alarm, the user chose (2026-09-30) to diagnose before any new registration. This is diagnostic evidence, not a screen: nothing here regrades 0227.

## Method

- Read the false-alarm seat's prompt, transcript and output (`/Users/Shared/devlyn-vr-0227/rounds/1801a5478ae8/work/.devlyn/`).
- Compared the judging rubric of the candidate (`22616b57` + F `f40da73b`) with the pre-candidate baseline (`366d837a`).
- Counted every binding claim on a reference round in 0226, G3 and 0227 by engine and kind.
- Replayed the four J4 reference rounds from their sealed pristine inputs ([`replay.py`](replay.py): the round's work tree and Codex home extracted to `/Users/Shared/devlyn-vr-0227-diag/`, the manifest's round environment with the paths relocated, the candidate's `verify-judges.py`, both seats live; raw results [`replays.jsonl`](replays.jsonl)). The J4 reference span is the same in all four rounds; they differ in orientation and repetition. Astra verified the inputs (pristine tars, product, argv, prompts differing only by the relocated work directory). Unlike the screen, the replays ran without its filesystem exclusion seals; the replay seats' tool calls show no read outside their copies.

## Findings

1. **The block recurs, and only from Codex.** On the J4 reference span every Codex block is the same scenario: a same-value growth with `noDisposeOnSet: true` evicts an entry whose `disposeAfter` is not delivered before `set` returns, cited as violating "Each evicted entry must receive the existing eviction disposal behavior." As a claim about that clause it does not hold: the existing library defers `disposeAfter` under `noDisposeOnSet` on every set path (RESULT, "Condition 2"; the screen's instance is the one established, audited false alarm). Six of the seven replay blocks add a second argument: the public option documentation says `noDisposeOnSet` suppresses `dispose` "in the case of overwrites" (`src/index.ts` 2147–2149; the option comment at 883–886 says "if the entry key is still accessible within the cache"), and an evicted entry is not an overwrite. That documentation and the base's own behavior already disagree on every set path; whether a public contract the base already contradicts is applicable when the spec asks to keep the existing behavior is exactly what the rubric leaves open (finding 3). The replay blocks are therefore recurrent blocks, not all established false alarms.

   | seat | screen rounds | replays | total |
   |---|---|---|---|
   | Codex primary (codex orientation) | 1/2 | 6/15 | **7/17** |
   | Codex pair (claude orientation) | 0/2 | 1/10 | **1/12** |
   | Claude primary or pair | 0/4 | 0/25 | **0/29** |

   The seat that raised it in the screen made four shell calls (no `git` read of the base) and concluded in 47 s.

2. **All binding claims on reference rounds across three runs came from Codex seats**: 8 of 96 Codex reference seats, 0 of 96 Claude reference seats. By kind: 5 execution-condition (0226 and G3, the Node 22 "offline" wording), 2 coverage (0227 J2), 1 behavioral (the 0227 J4 false alarm). Codex reference seats almost never report below rank 2; Claude reference seats report many LOW findings and never reach rank 2.

3. **The rubric has no explicit procedure for a preservation clause, and the relevant text predates the candidate.** It pushes toward binding ("Small impact, rare inputs, or a pre-existing defect do not excuse that violation"; "neither impact nor pre-existing origin makes an applicable violation advisory") and has general counterweights (do not widen an invariant beyond the spec's words, `verify.md` 55–60; "stronger inferred invariants, genuinely ambiguous clauses, and unrelated pre-existing issues are not demonstrated mandatory violations", 90–92), but nothing tells the judge to establish the existing behavior — on the base, or on the existing path the clause names — before making a violation of a keep-existing clause binding, or how to weigh a public contract the base already contradicts against such a clause. These sentences are word for word in the baseline `366d837a`; the candidate commits did not touch them. The candidate's renderer does add `base_sha` to the prompt, and read-only Codex seats can run `git` reads.

4. **The two coverage-only NEEDS_WORK verdicts were over-blocks.** The gap they name is real (no public test passes `allowStale: false` against a cache whose default is `true`), but the J2 spec leaves unexercised clauses to source review, the precedence clause is met in source, and the rubric says both "For high-complexity behavior, executable coverage must already be declared in sibling `spec.expected.json` or derived risk probes and present in the sealed MECHANICAL evidence. Missing coverage is a verdict-binding finding" (`verify.md` 72–76) and that clauses are accounted for with "cited source/design evidence for pure-design clauses or explicitly retained source-review obligations" (`verify.md` 79). Codex seats split 2/2 on the same observation.

## Diagnosis

The 0227 failure is not a residue of 0226's two causes. It is a separate, recurrent instability of Codex judge seats on J4: on a clause that asks to keep existing behavior, the seat asserts a binding violation without establishing what the existing behavior is (the screen's seat did not read the base), sometimes supported by a public-documentation argument that the base already contradicts; the rubric has no explicit step for either case while telling it that pre-existing origin never excuses a violation. The same seat role also turns a coverage observation into a block when the rubric's coverage and source-review rules conflict. Claude seats did neither on these spans.

What this does not show: that the missing rubric step caused the blocks (the existing counterweights already forbid the original misreading, so the repetition shows unstable adjudication on J4), that the rate generalizes beyond these spans (J4's wording invites the misreading; seats on one task are correlated), or that any particular rubric change removes it without costing recall — 61 of 0227's 69 hits come from checks that fail on the base too, so a rule that treats "same as base" as conforming must be limited to keep-existing wording.

## Consequence for the bar

Under 0227's strict bar a single reference false alarm fails the screen. Each run has 32 Codex reference seats (Claude seats raised none). With a per-seat false-alarm probability p, the chance of a clean run is (1 − p)^32: 80% needs p ≤ 0.7%, 50% needs p ≤ 2.1%. Observed: one established behavioral false alarm in 96 Codex reference seats across three runs (about 1%, a 72% clean-run chance). Separately, the J4 span drew a Codex block in 7 of 17 primary seats; those are recurrent blocks, not all established false alarms (finding 1), so they bound how unstable the adjudication is rather than the false-alarm rate. Seats on one task are correlated, so these numbers are rough; they show that the outcome turns on how often a corpus contains a clause like J4's. Changing the bar, the rubric or the engine roles is a registration decision for the user.
