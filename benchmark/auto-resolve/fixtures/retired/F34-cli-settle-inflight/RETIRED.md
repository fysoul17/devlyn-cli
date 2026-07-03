# F34 retired

Retired from the active golden suite after headroom run
`iter-0039-headroom-f34-f35`.

Reason: bare scored 92, exceeding the headroom ceiling of 60, and
`solo_claude` scored 88, exceeding the headroom ceiling of 80. Both arms
solved the settle-inflight task competently (judge: bare 92 vs solo_claude 88,
margin -4) and share the same minor scope slip (touching
`data/gateway-stats.json` outside the expected diff); neither arm hit a hard
disqualifier. The task was not hard enough for bare, let alone solo — there is
no pair-lift headroom to measure.

Future use: rework the visible contract or hidden verifiers so the task
creates a fair pair-risk-probe gap without hiding requirements from the spec.
