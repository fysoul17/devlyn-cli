# 0165 — Completion regression gate overhead

2026-09-13. Mission 1. User authorizes the four remaining core priorities,
one at a time through verification and delivery. Root implements directly;
Fable 5.1, or the authorized Opus 5 substitute, and Grok 4.6 review read-only.

## Why this iteration exists

0164's final required lint took 379.541s, including 33 completion regressions
in 166.297s. This iteration decides whether fixture-only Git dispatch can
reduce that required gate cost without deleting assertions or changing the
production completion path. It does not measure model or full-pipeline gains.

The historical ordinary-entry defect was already addressed: 0154's three
route-only customer AGENTS patches were applied with user authorization.
The current HANDOFF has the application receipt; the older iteration's pending
wording is historical. No repeat customer modification is needed. Current
model adherence and general route-selection effectiveness remain unproved.

## Prediction and candidate

Baseline aab3022e8d97881714a2da69fe0131d1e5e33a8b. Evidence root
`.devlyn/0165/`; prospective receipt 3d4eb2fe637a3eec6db882da.
`prediction.json` predates diagnosis. Two existing tests passed in 14.802s.
Three 25-call comparisons of the same read-only Git command took
1.866–1.976s through the original proxy and 0.288–0.307s natively.

An initial Python exec candidate still starts Python. Its coarse block timing
was inconsistent; a separate 40-pair interleaved diagnostic gave medians
78.529ms original and 53.760ms candidate. These are exposed microbenchmarks,
not suite savings. Its exact replacement is retained separately. Opus's
independent source diagnosis identified interpreter startup as the remaining
cost and suggested shell dispatch; root adopts that as the next candidate.

Subtractive-first / Optimized: bypass the test proxy where it has no transport
or after-effect work. A small POSIX shell dispatch forwards all exact argv
elements push/fetch/ls-remote/remove through the unchanged Python proxy;
other commands exec real Git. The remove match deliberately over-selects.
No new flag, cache, production branch or test omission. Existing Python fixture
bodies and every test method remain unchanged. Four actual argv/exit controls
match, including a path with spaces/semicolon and nonzero exits.

`shell-decision-prediction.json` fixes the adoption rule before full trials:
serial baseline/candidate/candidate/baseline, all 33 assertions pass, and both
adjacent pairs save at least 15 seconds and 15%. Otherwise reject adoption.
Full skill lint, exact source/mirror/diff checks, independent final source
reviews and delivery CI remain required after a successful comparison.

## Observed result and source review

| Order | Arm | Full 33-test suite | Result |
| --- | --- | ---: | --- |
| 1 | baseline | 184.890s | PASS |
| 2 | shell candidate | 77.724s | PASS |
| 3 | shell candidate | 61.160s | PASS |
| 4 | baseline | 120.380s | PASS |

Both registered adjacent pairs pass: 107.166s/57.962% and 59.220s/49.194%
less wall time. The large baseline variation is explicit; these two local
pairs support fixture-suite adoption, not a universal speed ratio or full-route
model-performance claim. No assertion, lsof/mount observation, independent
review or production completion check is removed.

Root adopted the exact candidate after all four returned. Source and both
mirrors matched baseline before writes. Independent final native Opus5
PASS68.284s and Grok4.6 PASS286.238s found no findings; both used zero tools.
Initial Fable429 and advisory Opus/Grok consultations remain in custody. User
subsequently reports Fable5.1 recovered; ongoing valid reviews were retained.

Subtraction control: deleting only the shell's remove token causes the existing
linked-worktree interruption test to fail its nonzero-exit assertion (0 == 0).
The unchanged Python proxy still owns post-effect failure injection; deleting
that routing token loses coverage. The other predicates preserve transport
rewriting and push/delete race assertions exercised in all four suites.

Signals now reach real Git directly on passthrough calls, and those calls no
longer parse simulated gh.json. This is fixture behavior, closer to real Git;
transport/removal interruption paths remain unchanged. No native-Windows
completion-fixture execution or speed improvement is claimed. Final full lint
passes289.683s, including the unchanged wider regression panel. Root accepts
PASS; Linux/native-Windows package CI and exact-source delivery remain separate.

## Custody and remaining work

Prospective task receipt 3d4eb2fe637a3eec6db882da owns branch and disposable
scratch; source/raw evidence live under `.devlyn/0165/`. Completion binds
`.devlyn/0165-evidence.tar.gz` and the exact source commit before publication.
Consult `.devlyn/0165-delivery/FINAL.md` and the receipt for actual CI/merge status.
The original project WIP, A16 and frozen comparisons remain untouched.

This closes a bounded gate-cost decision. General current routing adherence,
semantic recall, matched bare/solo/pair value and independent-human trial15
remain unproved. No npm release or frozen-study rerun follows.
