Read-only verification, round 2 (final), of root's 0257 judgments in /Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0257-result/autoresearch/experiments/0257. Same rules and evidence as results/judge-r1-prompt.md (read it; never read home/ or auth files; write nothing). Round 1 reviews: results/judge-r1-astra.md and results/judge-r1-grok.md (both BLOCK).

Fixes since round 1 (results/audit-parts/d4.{md,json}, i0185-claude.{md,json}, severe-parts/sev-codex.md; merged results/decisions.json; decide.py output results/decision.json):
- D4: the d4-writer-startup witness ([true,true] on 14 Claude D4 trees) is now applied under m24. False completions added: A d022 d133 d214; B d053 d134 d198 d245. d229 is a coverage close call.
- I0185: d106 removed (its report discloses the K5 race, 0233 d13 precedent); the other six were rechecked and kept.
- sev-codex.md: d137 replaced-lock-owner marked withdrawn.
Now 21 false completions, all Claude: D4 A 6 / B 9, I0185 A 5 / B 1. Token unchanged: claude dev PACKAGE_UNSAFE, conf PACKAGE_LOWERS_QUALITY, D NO_DETECTED_DIFFERENCE; codex dev INCONCLUSIVE, conf PACKAGE_COSTS_MORE, D B_BETTER; predictions 1-6 true.

Check only: (1) each round-1 finding is correctly resolved, each added or removed cell follows m24 the same way in both arms, with the exact sentence and tree evidence (d229 coverage call included); (2) no other cell with a [true,true] witness result in witness-runs/{witnesses,new-witnesses}.json makes a specific claim that the result falsifies and is still missing; (3) decisions.json matches the parts. First line SHIP or BLOCK; then HIGH/MEDIUM/LOW findings with evidence. Be concise.
