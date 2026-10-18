# rp-d7 design review r0 — Astra ultra

P1 passes the byte check: both replacements occur exactly once; the result is 353 bytes with the stated SHA-256 and trailing newline. The pre-smoke freeze and four-slot scope are appropriate for a routing screen; no additional controls are essential.

1. **MEDIUM — failure classes overlap.** In [DESIGN.md:101](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/DESIGN.md:101), “**skip**: public checks pass and there is no merged PR” overlaps “**quality**: a scope, check, oracle or preservation failure.” A public-check-passing slot can still fail an oracle. Also, “no merged PR” includes an open PR, whereas the parenthetical excludes it.

   Replace the classification block with:
   > Classify each non-delivered slot by the first matching rule: **quality** if any scope, public-check, oracle or preservation check fails; **skip** if all those checks pass and the work remains uncommitted or locally committed, with no push or PR; **other** otherwise, including pushed or opened-but-unmerged work.

   This makes the primary outcome reproducible under **No guesswork**.

2. **MEDIUM — decision ordering contradicts the quality fallback.** At [DESIGN.md:132](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/DESIGN.md:132), “**SKIPS PERSIST:** two or more skips” wins before “**MIXED:** anything else (one skip, or any quality failure).” Two skips, one quality failure and one delivery therefore bypass the stated quality fallback.

   Replace “two or more skips” with:
   > two or more skips and no quality failure.

3. **MEDIUM — reason tags need explicit adjudication rules.** At [DESIGN.md:109](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/DESIGN.md:109), “tag it with the rp-d6 reasons it gives … They are not graded” is insufficient when tags determine both the prediction and next-step routing. Reason 3 also needs to include objections based on the retained `caller.json.allowed`.

   Replace that paragraph with:
   > Both reviewers independently quote and assign every supported reason: 1 = delivery withheld for missing publication request or authorization; 2 = publication withheld because of a stated Git-operation restriction; 3 = delivery withheld because its bookkeeping exceeds allowed paths, including `caller.json.allowed`. Use “none” only when no reason matches. Tags do not affect delivery grading; they evaluate the reason prediction and inform routing. Publish unresolved disagreements and mark the reason prediction unresolved where necessary.

   Replace “reason 1 alone” in rule 4 with “the combined tag set across all skips is exactly `{1}`”; add:
   > Any tag 3 points to option 2. Remaining combinations, including reason 2, “none,” or unresolved disagreement, receive no automatic candidate recommendation.

4. **LOW — interpretation language exceeds the observational design.** The limitations correctly acknowledge the historical control, but three phrases undermine that qualification:

   - Replace “**SENTENCES IMPLICATED:**” at [DESIGN.md:127](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/DESIGN.md:127) with “**NO SKIPS OBSERVED:**”.
   - Replace “so a product change is indicated” with “so a product-change hypothesis merits consideration; this screen does not establish that a change is necessary”.
   - Replace “the reason tags only suggest which one mattered” with “the reason tags record stated rationales; they do not establish either removed clause’s causal contribution”.

   These wording changes preserve the owner’s inexpensive routing decision without requiring more slots.

VERDICT: REVISE
hook: Stop
hook: Stop
hook: Stop Completed
hook: Stop Completed
tokens used
49,476
P1 passes the byte check: both replacements occur exactly once; the result is 353 bytes with the stated SHA-256 and trailing newline. The pre-smoke freeze and four-slot scope are appropriate for a routing screen; no additional controls are essential.

1. **MEDIUM — failure classes overlap.** In [DESIGN.md:101](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/DESIGN.md:101), “**skip**: public checks pass and there is no merged PR” overlaps “**quality**: a scope, check, oracle or preservation failure.” A public-check-passing slot can still fail an oracle. Also, “no merged PR” includes an open PR, whereas the parenthetical excludes it.

   Replace the classification block with:
   > Classify each non-delivered slot by the first matching rule: **quality** if any scope, public-check, oracle or preservation check fails; **skip** if all those checks pass and the work remains uncommitted or locally committed, with no push or PR; **other** otherwise, including pushed or opened-but-unmerged work.

   This makes the primary outcome reproducible under **No guesswork**.

2. **MEDIUM — decision ordering contradicts the quality fallback.** At [DESIGN.md:132](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/DESIGN.md:132), “**SKIPS PERSIST:** two or more skips” wins before “**MIXED:** anything else (one skip, or any quality failure).” Two skips, one quality failure and one delivery therefore bypass the stated quality fallback.

   Replace “two or more skips” with:
   > two or more skips and no quality failure.

3. **MEDIUM — reason tags need explicit adjudication rules.** At [DESIGN.md:109](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/DESIGN.md:109), “tag it with the rp-d6 reasons it gives … They are not graded” is insufficient when tags determine both the prediction and next-step routing. Reason 3 also needs to include objections based on the retained `caller.json.allowed`.

   Replace that paragraph with:
   > Both reviewers independently quote and assign every supported reason: 1 = delivery withheld for missing publication request or authorization; 2 = publication withheld because of a stated Git-operation restriction; 3 = delivery withheld because its bookkeeping exceeds allowed paths, including `caller.json.allowed`. Use “none” only when no reason matches. Tags do not affect delivery grading; they evaluate the reason prediction and inform routing. Publish unresolved disagreements and mark the reason prediction unresolved where necessary.

   Replace “reason 1 alone” in rule 4 with “the combined tag set across all skips is exactly `{1}`”; add:
   > Any tag 3 points to option 2. Remaining combinations, including reason 2, “none,” or unresolved disagreement, receive no automatic candidate recommendation.

4. **LOW — interpretation language exceeds the observational design.** The limitations correctly acknowledge the historical control, but three phrases undermine that qualification:

   - Replace “**SENTENCES IMPLICATED:**” at [DESIGN.md:127](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/DESIGN.md:127) with “**NO SKIPS OBSERVED:**”.
   - Replace “so a product change is indicated” with “so a product-change hypothesis merits consideration; this screen does not establish that a change is necessary”.
   - Replace “the reason tags only suggest which one mattered” with “the reason tags record stated rationales; they do not establish either removed clause’s causal contribution”.

   These wording changes preserve the owner’s inexpensive routing decision without requiring more slots.

VERDICT: REVISE
