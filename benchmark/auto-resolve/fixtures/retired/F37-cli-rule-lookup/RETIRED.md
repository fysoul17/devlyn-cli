# F37 retired

Retired from the active golden suite after headroom run
`iter-0041-headroom-f36-f37`.

Reason: bare scored 75, exceeding the headroom ceiling of 60, and
`solo_claude` scored 96, exceeding the ceiling of 80 (judge: passed all four
required verification commands including scale, via per-category sorted rule
index + binary search with correct tie-breaks). The solo arm's invoke exited
nonzero (`invoke_exit: 1` at 1247s) yet its working tree still verified
clean — recorded by the gate as `solo_claude invoke failure` but the score
stands on the verified artifacts. Neither ceiling held; no pair-lift headroom.

Future use: the as-of lookup shape (Codex R1 replacement design) was still
within one-shot reach of both arms. Same lesson as F36: the scale axis alone
does not discriminate a full solo pipeline.
