Round 2 of a read-only apparatus review in the devlyn-cli repository (do not edit files, do not run anything live).

Contract: autoresearch/experiments/rp-d7-prompt-delivery/DESIGN.md (frozen). Implementation: the other files in autoresearch/experiments/rp-d7-prompt-delivery/. Round-1 reviews: results/apparatus-r1-astra.md and results/apparatus-r1-grok.md in that directory. The fixes are the last commit (`git show HEAD` equivalent: compare the files against the findings).

Check that every round-1 finding is fixed correctly (sealed-evidence revalidation before publication review; strict scoped-only GitHub credential directory; exact CLAUDE.md binding; classification order quality → skip → other with unset only when none matches; `none` tag combinable; unresolved false completion → INCONCLUSIVE; prediction not scored while outcomes are unknown), and look for any new HIGH or MEDIUM problem the fixes introduced, especially in security (token never in argv/records/evidence, scans before sealing, no full-access host token mounted) and evidence integrity. Do not reopen settled design scope.

Report findings with severity HIGH / MEDIUM / LOW, file:line and a concrete fix. End with exactly one final line: `VERDICT: SHIP` or `VERDICT: REVISE`.
