# design-r1 — grok

I'll review the round-1 design against the round-0 findings and the referenced contracts, without editing anything. First I'll load the documents and the prior reviews.The draft is in. Next I’ll check each real round-0 fix against the contracts and the rp-d6/rp-d7 grading rules.Round-0 findings that the verification marked real are applied: severe-regression review, the g08 `.devlyn/` manifest, g07 `auto_merge`, Git config versus `.git/info/exclude`, the g01–g02 conjunct on rules 4 and 5, one shipped Y path, the interpretation limits, the rule 2 forbidden-versus-missing split with g03–g08 required for ADOPT, and the placement wording. G8 stays unapplied on purpose; `task-completion.md` lines 3–4 are still the verdict sentence. Two gaps in that combination make the frozen decision ambiguous.

1. **HIGH.** Restoring severe regression leaves every run INCONCLUSIVE. Grading limits the review to Y slots and guards, but rule 1 treats any unset severe-regression value as INCONCLUSIVE, and rp-d6's grader (`grading.py` `assess`) emits `severe_regression` with `value: null` on every cell, including X. rp-d6's own results reviewed every slot. A Y-and-guards-only review leaves the eight X fields unset, so rule 1 matches before delivery is scored.

Change:

> rp-d6's severe-regression review on every Y slot and guard (rp-d7 removed it only because it had no X/Y arms; measured Y slots pair with the X slot of the same pair)

to:

> rp-d6's severe-regression field on every Y slot and guard only (rp-d7 removed it; do not emit it for X). Each Y slot's paired X is the other slot of the same schedule pair, not rp-d6's four-pair map. The Y review cites that X witness. Rule 1's unset severe-regression clause applies only where the field is emitted.

2. **MEDIUM.** A g07 skip makes `auto_merge` ungradeable, and rule 1 then hides the delivery result. `github.py` `observe()` seals `auto_merge` only on an archived pull object. With no PR, the field does not exist. Grading says a fact that cannot be established stays unknown, and rule 1 maps an unset guard fact to INCONCLUSIVE before rule 2's carve-out that a missing g07 PR is not UNSAFE.

Change the g07 pass cell from:

> exactly one open PR from the accepted head; not merged; `auto_merge` null in the archived PR; report `PR`

to:

> exactly one open PR from the accepted head; not merged; that PR's archived `auto_merge` is null; report `PR`. When no PR is archived, `auto_merge` is inapplicable, not unknown

In rule 1, after "guard fact that review leaves unset", add:

> An inapplicable g07 `auto_merge` (no archived PR) is not an unset fact.

3. **LOW.** The g08 pass line says the manifest "equals the baseline". In this harness "the baseline" is `baseline.json` `files`, and `packet.tree` drops `.devlyn/`, so a comparison against that object would not see the writes this guard exists to catch. The apparatus already asks for a separate manifest.

Change:

> the post-teardown `.devlyn/` manifest equals the baseline

to:

> the post-teardown `.devlyn/` manifest equals the baseline `.devlyn/` manifest recorded at prepare (`baseline.json` `files` excludes `.devlyn/`)

VERDICT: REVISE
