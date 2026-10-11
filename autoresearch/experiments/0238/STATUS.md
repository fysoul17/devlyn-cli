# 0238 current execution

2026-10-10. Pair transport registered in registration-smoke.md; pair efficacy is
still a proposal, and no product pair instruction is adopted.

Accepted solo baseline: original 4.2.3, two delivery fixes and the direct adjacent
AGENTS import correction (../0239/results/import-dedup-decision.md). Root product
instructions remain unchanged. Both withdrawn wording comparisons remain closed.

Apparatus v5 is SHIP. New selected-packs-v2 archives and 969 payload files match;
Node 20 offline install/parser controls pass. Actual staged F23 positive/no-op/
deleted controls classify correctly, missing evaluator is STOP, and all 12 helper
bindings match across the four H/P owner configurations. The first install audit
incorrectly expected a Claude target for Codex-only installation; that failure is
retained and the corrected installed-target audit passes without product changes.
An empty `.claude` tree is expected for Codex-only installation. The installer
upgrade tests use the exact published 4.1.0 fixture, not unreleased shared files
misclassified as published history.

Private runtime:
`/Users/aipalm/.local/share/nx01/0238-live/staged-v1/runtime-smoke-v2.json`
SHA256: 636fca16d1394b6490ed68d2581377ca2844e9b1e8e28f3191625f5d001d98cf.

Execution inputs are frozen in `results/freeze-smoke-v1.json`, SHA256
`fe8e59e862fd677a9ee2474f1eda4e75501b54c423e8b68fdf983efae1642dd1`.
s01-h-claude was **not dispatched**: its token lifetime was 5725s, below the
unchanged 6300s preflight margin. The reason-only rejection is preserved in
`results/auth-preflight-refusal-v1.json` (an exact copy of the private out-smoke
record). The user explicitly switched accounts and confirmed the new login.
Profile verification found 21,008 seconds remaining. Root closed only its old
pending login process, verified by its exact stdout log descriptor.

The original freeze/runtime remain unchanged. registration-smoke-account-v2.md
binds the new account before any inference; only account and fresh auth/scratch/
output paths differ. New freeze-smoke-v2.json SHA256 is
126a1903579270c90e431a336f600b7ce1aad085f03ee37fc58613f525f61cc8.
The unchanged preflight passed. **s01-h-claude-v2 finalized STOP**, owner nonzero,
after 1327.940s: both the fresh peer and later owner requests report EAI_AGAIN
resolving api.anthropic.com. The peer produced no genuine native model response;
whole usage is UNKNOWN/PARTIAL, with 1,852,747 input / 74,086 output lower bounds.
Teardown is CLEAN. All 706 sealed evidence entries and all input/control hashes
match. Preserve this result; no source or efficacy conclusion follows.

The model-free, same-image DNS/HTTPS probe passed at 14:07:07 UTC without setting
changes. registration-smoke-recovery-v3.md prospectively registers a new
s01-h-claude-v3 after observed recovery, using the identical runtime/protocol.
Freeze-smoke-v3.json SHA256:
1069d837258440cc1f9aba1f8f12496d5263f9d8bb905d3774a3a15bee6e4314.
**s01-h-claude-v3 finalized CHECKS_PASS**, exec session 71251 exited 0. Owner
wall 1206.087825s; native whole usage COMPLETE: 4,534,554 input (caches included),
129,558 output (thinking already included). Fresh and resumed peer calls both
exited 0 with stable source; accounting MATCH with no gaps or retries, local
delivery PASS and teardown CLEAN. All 727 sealed evidence files, 55 snapshot
entries and frozen inputs/control hashes match. The independent protocol audit
also passes (results/s01-v3-protocol-audit.md). This is operational transport only.

**s02-h-codex-v2 finalized STOP**, exec session 90970 exited 2, because whole
usage is PARTIAL. The owner itself exited 0 after 635.339556s; peer identity and
protocol MATCH, source stable, fresh/resume and one Sol/high child completed,
local commit ca19872f1fbe9d5c738f14ad37ea6be11edcdf3f, teardown CLEAN. The
independent audit verifies 1,196 evidence entries, all input/control seals and
the native protocol. No source verdict is retroactively added.

The peer primary inference dd112f33-b674-448a-9593-dff63fe76214 was cancelled
after partial reasoning and child-answer incorporation, before provider terminal
usage. Its partial payload has null token_usage and no response/request ID.
The 33 completed inferences reconcile to 1,217,463 input / 27,994 output, but
that is a lower bound, not evidence the cancelled request cost zero. Preserve
STOP and every raw result (results/s02-v2-accounting-diagnosis.md).

The frozen serial sequence is stopped: do not launch s03/s04 or reroll s02.
The single-peer revision is isolated under ../0240. Its design and implementation
reviews approve native validation; 25 model-free controls pass, B/S packages are
byte-identical and H/P change only their guide and peer helper. All old frozen
inputs remain unchanged. New registration and seals govern that work; none of
these results admits pair or removes this STOP. See ../0240/STATUS.md.
