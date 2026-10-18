Round 3 of a read-only apparatus review in the devlyn-cli repository (do not edit files, do not run anything live). A third round runs only because round 2 left HIGH findings.

Read autoresearch/experiments/rp-d7-prompt-delivery/results/apparatus-r2-astra.md and apparatus-r2-grok.md, then the current rp-d7 implementation (autoresearch/experiments/rp-d7-prompt-delivery/*.py, tests, README.md) against DESIGN.md.

Check only: (1) the credential gate — strict ASCII/LF, exact allowlist schema for hosts.yml and config.yml, exactly one fine-grained PAT, checked before any mount, token never printed or recorded; (2) baseline (and any other slot-root input outside the evidence manifest) digest-bound at grading and verified before publication recomputation, with missing → unknown and mutation → explicit failure; (3) any new HIGH or MEDIUM problem these fixes introduced. Do not reopen settled scope.

Report findings with severity, file:line and a concrete fix. End with exactly one final line: `VERDICT: SHIP` or `VERDICT: REVISE`.
