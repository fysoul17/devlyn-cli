# 0219 — Click check parity after the 0218 D2 breach (design)

2026-09-24. User: design the fix with Astra. Root direct, no resolve. Opus and
Astra (gpt-6-astra/high, read-only) wrote independent R0s; Astra returned FREEZE
in round 1. Design only: nothing dispatched.

## Root cause

[0218](../0218/RESULT.md) stopped at D2-1-A: 1,007,058 observed input against
800,000 (owner 619,735 + one review 387,323 from a 1.1 MB packet). Why-chain:
the review was huge ← the packet carried every saved check, with only Node TAP
compacted ([packet.py](../0211/packet.py)) ← most large logs came from
investigating pager failures that the evaluator never sees ← the owner's tool
shells are login bash, and the image's `/etc/profile` resets PATH. That drops
`/control/less`, which the evaluator ([check_cell.py](../0211/check_cell.py))
keeps. The violated invariant is owner/evaluator dependency parity, the same class
as 0215's `NO_COLOR` gap. Also, the registered D2 focused check names
`tests/test_exceptions.py`, but that path is a directory, `tests/test_exceptions/`,
so it collects nothing. Legitimate pre-fix regression failures (86, 179 KB) are
real evidence, not noise.

Model-free precheck (`.devlyn/0219/parity-precheck.txt`; owner-like login bash,
pinned image, Click base): plain `python -m pytest` 24 failed / 2,075 passed;
with `env PATH=/control/less/usr/bin:"$PATH"` 2,099 passed. Registered D2 focused
command: no tests ran. With `tests/test_exceptions/`: 110 passed. D4 focused with
the prefix: 109 passed.

## Fix (identical across A/B/C)

A new 0219 wrapper around [0218 preparation](../0218/prepare.py) makes two changes:
- D2/D4 pytest checks are prefixed with `env PATH=/control/less/usr/bin:"$PATH"`.
- The D2 focused path `tests/test_exceptions.py` becomes `tests/test_exceptions/`.
  The allowed-edit list is unchanged.

It rebinds caller, prompt, argv and hashes. Everything else in 0218 is unchanged:
color, format gates, review launcher, usage meter, wait text, targets and models.

Packet compaction for pytest is **not** added yet. After the parity fix, a
model-free replay must first show substantial, mechanically removable redundancy
that still keeps every test identity, outcome, distinct diagnostic, warning,
command and exit status. Exact duplicate removal (the diff appeared twice) is
evaluated in that same step. Unknown formats stay unchanged, and allowed source
such as `CHANGES.md` is never truncated.

## Continuation

0218 stays stopped and archived: six COMPLETE D1 rows, one BUDGET_EXCEEDED row,
seventeen NOT_RUN rows; no resumed calls and no retry of cell 7. Continue with a
fresh, registered 24-cell screen. Historical D1 rows stay separate and are not
pooled. This needs new user authorization that explicitly acknowledges that 0218
already used the protocol's single-redesign allowance. Before inference, reseal all
admission checks: bindings, parity, format gates, calibration, meter, accounting
and teardown. Results stay descriptive, development-only, with UNKNOWN terminal
accounting for any breach. Do not raise targets, change models, weaken checks,
review or repair, or add scheduler/engine hooks.
