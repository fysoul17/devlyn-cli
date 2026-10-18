# rp-d7 design review r1 — Astra ultra

P1’s replacements, 353-byte length and SHA-256 match. Grok’s class precedence, delivery flag, decision-label, cost and timing corrections are present.

1. **HIGH — The reused grader cannot mechanically establish `skip`.** [DESIGN.md:117](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/DESIGN.md:117) requires “no push,” but [grading.py:252](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d6-claude-delivery/grading.py:252) leaves that fact unknown when the final remote census is unchanged: it cannot exclude push-and-delete. Publication adjudication covers only g04–g06. All four historical skips retain `pushed: null`. Ordinary refusals could therefore become `other`, defeating the prediction and SKIPS PERSIST rule. **Fix:** keep `delivery_pass` unchanged, but register publication adjudication for measured slots using sealed action history. Require established absence of publication for `skip`; unresolved evidence must yield INCONCLUSIVE. Describe classification as mechanical after that adjudication.

2. **MEDIUM — The claim that every round-0 finding was applied cannot be verified.** [DESIGN.md:3](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/DESIGN.md:3) says both reviewers returned REVISE, but [design-r0-astra.md](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/results/design-r0-astra.md:31) ends with the review prompt. It contains no Astra findings or verdict. **Fix:** restore or link the complete original response and reconcile its findings; correct the opening attribution if no completed response exists.

3. **LOW — Candidate-routing precedence remains implicit.** At [DESIGN.md:172](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/DESIGN.md:172), two skips with tag sets `{3}` and unset satisfy both “any skip tagged 3” and “an unset tag set … gets no automatic candidate.” **Fix:** explicitly order the routing rules. To preserve the stated missing-evidence safeguard: any unset tags or missing report → no candidate; otherwise any tag 3 → option 2; otherwise every set exactly `{1}` → commit-rule hypothesis; otherwise no candidate.

VERDICT: REVISE
hook: Stop
hook: Stop
hook: Stop Completed
hook: Stop Completed
[codex-monitored] heartbeat: elapsed=330s
tokens used
69,187
P1’s replacements, 353-byte length and SHA-256 match. Grok’s class precedence, delivery flag, decision-label, cost and timing corrections are present.

1. **HIGH — The reused grader cannot mechanically establish `skip`.** [DESIGN.md:117](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/DESIGN.md:117) requires “no push,” but [grading.py:252](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d6-claude-delivery/grading.py:252) leaves that fact unknown when the final remote census is unchanged: it cannot exclude push-and-delete. Publication adjudication covers only g04–g06. All four historical skips retain `pushed: null`. Ordinary refusals could therefore become `other`, defeating the prediction and SKIPS PERSIST rule. **Fix:** keep `delivery_pass` unchanged, but register publication adjudication for measured slots using sealed action history. Require established absence of publication for `skip`; unresolved evidence must yield INCONCLUSIVE. Describe classification as mechanical after that adjudication.

2. **MEDIUM — The claim that every round-0 finding was applied cannot be verified.** [DESIGN.md:3](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/DESIGN.md:3) says both reviewers returned REVISE, but [design-r0-astra.md](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/results/design-r0-astra.md:31) ends with the review prompt. It contains no Astra findings or verdict. **Fix:** restore or link the complete original response and reconcile its findings; correct the opening attribution if no completed response exists.

3. **LOW — Candidate-routing precedence remains implicit.** At [DESIGN.md:172](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d7/autoresearch/experiments/rp-d7-prompt-delivery/DESIGN.md:172), two skips with tag sets `{3}` and unset satisfy both “any skip tagged 3” and “an unset tag set … gets no automatic candidate.” **Fix:** explicitly order the routing rules. To preserve the stated missing-evidence safeguard: any unset tags or missing report → no candidate; otherwise any tag 3 → option 2; otherwise every set exactly `{1}` → commit-rule hypothesis; otherwise no candidate.

VERDICT: REVISE
