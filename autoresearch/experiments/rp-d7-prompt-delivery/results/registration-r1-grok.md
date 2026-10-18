# rp-d7 registration review r1 — Grok 4.7

I'll review the registration against the frozen design and the apparatus, read-only. First I'll load the registration, design, and prior notes, then check every identity and input hash.The registration text is loaded. Next I’ll hash each listed input and check the worktree against `apparatus_commit`.The registration matches the frozen identities and the sixteen input digests, and it should be revised before exposure because prediction scoring does not follow DESIGN.

**MEDIUM.** The second prediction clause is scored while a skip's tag set is still unset. DESIGN.md line 176 says that if any skip's tag set is unset, the second clause is not scored. `summarize.py` lines 84–85 score that clause false when another skip is a counterexample, and `test_summary.py` lines 107–112 lock that in: one skip with unset tags and another tagged `none` yields `every_skip_includes_1` false and `supported` false. The registration says DESIGN's full text applies, so the published prediction can be scored in a state the contract leaves unscored.

Fix: in `prediction()`, leave `every_skip_includes_1` as None when any skip's `agreed_tags` is None. Update that test to expect the second clause unscored. Keep DESIGN unchanged. Recompute the `summarize.py` and `test_summary.py` input hashes and point `apparatus_commit` at the new commit.

**LOW.** `registration.md` lines 49–50 say there is no prediction score while outcomes are unknown. `test_summary.py` lines 90–103 score `at_least_one_skip` true as soon as one skip exists, even when the other three outcomes are unknown.

Fix: replace that sentence with DESIGN's rule that an unset tag set leaves the second clause unscored. Paste DESIGN's Decision section into `registration.md` unchanged, including the five labels, their conditions, and routing (a)–(d). The current label list is in the right order and does not restate those conditions.

Checked and holding:

- All 16 `inputs` SHA-256 values match the worktree bytes and the blobs at `519aa0d308a57257f53d5a592d71e008acab0345`. The tracked difference from that commit is only `registration.md` and `registration.json`.
- P1 is 353 bytes, SHA-256 `2387ddde…cf2e`, from `common.txt` `2ccc7f6a…50cf` by the two exact replacements in `prepare.py`.
- X is `devlyn-cli@4.2.22`, SHA-256 `799c6091…ca61`, the same SHA-512 integrity and manifest digest as rp-d6 arm X. The models-cache hash is `8597e51f…0a49`.
- The schedule is m01 BV, m02 Z0, m03 BV, m04 Z0, all Claude `high` and P1. Smoke is `smoke-claude`, spare is `smoke2-claude`. The six repositories are `fysoul17/rpd7-20261018a-<slot>`. The effort is `high`. The rp-d6 X reference is m01, m04, m05, and m08, with 2 delivered.
- The prediction quotation matches DESIGN. Neither registration file contains a secret, a VPN hostname, or an IP.

VERDICT: REVISE
