# 0217 — review launcher fixed; two D1 B replicates complete

2026-09-23. User chose the order agreed with Astra (fix first, then two replicates;
Astra FREEZE, `.devlyn/0217/` in the retained base checkout). Root direct, no resolve.

## Fix

[review.py](review.py) parses arguments with `argparse` and then runs the
archived [0210 launcher](../0210/review.py) unchanged (mounted as
`/control/review-0210.py`, byte-identical). Model-free controls in the pinned image
(`review-cli-controls.txt`): `--help` exit 0 and unknown arguments exit 2, both with
no review allocation and unchanged files; no arguments still allocates and
dispatches; an exhausted pool still refuses; `--help` on an exhausted pool exits 0.

## Replicates (serial, 0216 setup, only the launcher changed)

Prompts are byte-identical to 0216 B. Budgets and first-breach stops are unchanged.

| Cell | Result | Owner + review INPUT / OUTPUT | Generations | Reviews | Owner seconds |
| --- | --- | --- | --- | --- | --- |
| rep1 | COMPLETE | 302,399 / 7,521 terminal (native 273,947 + review 28,452) | 11 | 1 | 189.1 |
| rep2 | COMPLETE | 387,985 / 10,162 terminal (native 358,674 + review 29,311) | 16 | 1 | 300.1 |

Both passed four requirement checks, the public suite (0 failed), the format gate
and scope. Blinded assessments returned complete:true with only low/info notes
(rep1 30,525 input, rep2 41,177, one call each, separate from the owner pool).
Every prediction held in both: no review dispatched by a non-review command (rep1
again ran `review.py --help`, which now printed usage only); the single review saw
a passing format result for its exact final source; no post-review format repair.

**Deviation (rep1):** its launch seal and account check were not written before
inference. The profile endpoint returned 429, and the launch command did not stop.
After the run, the same account/organization fingerprints and all input hashes were
bound in `seal-rep1.json`, labeled POST-HOC. rep2 was sealed before launch. The
provider usage endpoint stayed rate-limited (usage UNAVAILABLE).

## Reading

With the color, format and launcher fixes, 2/2 corrected D1 B cells completed below
400,000. 0216 stays a separate pre-fix observation (its accidental review also gave
a hint) and is not pooled. rep2 left 12,015 of headroom, so variance is large;
this is repeat feasibility on exposed D1 only, not reliability, a causal effect,
generality or adoption. Next, per the agreed order: a separately registered D1–D4
A/B/C screen under the 0206 protocol.

Evidence: `.devlyn/0217/` in the retained base checkout, archived as
`.devlyn/0217-evidence.tar.gz`. Credentials stayed in owned 0600 scratch.
