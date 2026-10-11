# 0240 single-peer native transport registration

2026-10-10, before any 0240 native inference. This is a new reviewer capability
treatment described in DESIGN.md. It does not repair or replace 0238 s02's
unknown cancelled inference, resume that stopped sequence, or admit pair.

The reviewed implementation is bound by results/review-manifest-v1.json, SHA256
a266c706c6a350467acd5430ce541cd790e97818e11ef09809b0a1a7d2e79353.
Its cross-model implementation review is SHIP-for-native-validation. Selected
packages are B 050bc8d6f3af071461903f0c7efd77ae445828f232152cd4f52b6e81faa967b3,
S c031f7d5e5ea752bf153092e059684f281cfd55a1241c643f57b525b22d334d5,
H 029a61be32644a03be3720dc7df0f85002f6d32a88ab8408f38ba35fc4df41e1,
P 5c7bad2e3fe72fd0d052409ebda78113dc7326c57281e0b266490b7a0096ace0.
Tasks SHA256 is 0f8f531228bbe4e29e3c58b51d226b3c3fe21cbf01ae8ecf7d6b7ca6e86a6e93.
B/S archives are byte-identical to 0238 v2. H/P payload changes are limited to
the peer helper and guide. Root trigger, primary models/effort, owner child
configuration, image, quotas, watchdogs and all accounting gates are unchanged.

After actual staged installation checks and evaluator-control input comparison,
freeze runtime, controls, packages, tasks, all runner dependencies, this
registration and the reviewed prerequisites. Dispatch these identities serially:

| Cell | Task | Arm | Owner | Peer |
| --- | --- | --- | --- | --- |
| s01-h-codex | S2 | H | gpt-6-astra / max | gpt-6-astra / max |
| s02-p-claude | S2 | P | claude-opus-5-5 / max | gpt-6-astra / max |
| s03-p-codex | S2 | P | gpt-6-astra / max | claude-opus-5-5 / max |

No independent study model call, reviewer or heavy test overlaps an active owner.
S2 retains its calculation contract and forced fresh/same-session resume check;
only the prior forced peer child is removed, and reviewer delegation is forbidden.
This is operational evidence, not ordinary activation or efficacy evidence.

For every cell require the inherited native identity, complete whole-run usage,
stable source, original-request fidelity, completed answers, executed witness,
source/public checks, attributable local delivery and clean teardown gates.
S2 has no hidden oracle; do not imply otherwise. Inspect every captured attempt,
not just a successful exit. For Codex peers, both fresh and resumed CLI argv must
include features.multi_agent=false. Actual native request tool catalogs must
omit native delegation tools, including the collaboration namespace; absence of
a spawn call alone is insufficient. Owner Codex catalogs must retain delegation
tools. Reject any captured peer descendant or independent recursive launch.
Claude peers must retain the original Read/Grep/Glob-only restriction. Record
only marker presence, never remove CLAUDECODE or print credentials.

Reuse 0238 s01-h-claude-v3 solely for the unchanged Claude-to-Claude launcher,
identity, fresh/resume transport, capture and teardown facts. It did not run the
0240 guide/package. The comparison, 25 fixture tests and archive/source binding
must establish the unchanged branch; the new P-Claude owner also exercises the
revised guide. Do not reuse 0238 s02 as passing transport or cost evidence.

On the first failed gate, preserve the cell and stop the sequence for diagnosis.
No favorable reroll or post-result relaxation. Keep incomplete inference usage
UNKNOWN, full known lower bounds and original STOP. A named treatment repair
requires separate prospective identity/registration; do not assume disabling
peer children prevents owner or unrelated request cancellation.

The selected account is checked before each dispatch using only the supported
login snapshot/profile flow. Keep the 6300-second preflight lifetime margin.
Authentication/network faults do not license credential edits. Image remains
sha256:0f472bb41685b7daa5923d51d31983f4b3c70053dd773fdf712bd0dcd6d87998,
owner --init/PID256/memory4g/CPU2, owner5400/review600/evaluator600/peer540 seconds.
There are no token, cost or call budgets and no background-wait environment changes.

Only passing transport permits a separately registered ordinary F23 comparison.
Its request must omit forced pair instructions, and its measured startup catalogs
must come from retained actual evidence. Efficacy is not authorized by this file.
