# 0242 native transport registration

2026-10-10 UTC, before any 0242 inference. This sequence tests the two bounded
repairs in DESIGN.md. All stopped 0238/0240/0241 outcomes and costs remain intact.
No efficacy result or product pair adoption follows from operational success.

The reviewed manifest is results/review-manifest-v1.json, SHA256
e767833b31bc207da1363ccc142e5192cb485de87c1e2fdf1e453089160e37bd.
Astra's first review is SHIP-for-native-validation with no HIGH or MEDIUM finding;
149 review bindings and 47 fixtures pass. Read-only replay recognizes the two
actual helper calls and excludes their quoted acceptance-record copies. It does
not regrade the old STOP/PARTIAL or old native capability failure.

| Arm | Selected archive SHA256 |
| --- | --- |
| B | 050bc8d6f3af071461903f0c7efd77ae445828f232152cd4f52b6e81faa967b3 |
| S | c031f7d5e5ea752bf153092e059684f281cfd55a1241c643f57b525b22d334d5 |
| H | 7d34056c0b12035d306c3afc64e9e9cfafd2958633a6ae90df8865b1f3d98b07 |
| P | 7358c47ce382453e77e1f9b52695b40ff1a3499a23c921ef5a76e58374d6c137 |

All 969 regular payloads and 20 installed bindings match. B/S are byte-identical
to 0241; H/P change only packaged peer.py. Public/oracle trees, F23 task and
inherited preparation/evaluation remain unchanged. Exact prior evaluator
controls are reused, not rerun. Only 0242-live/staged-v1 is selected. Tasks SHA256
is 0f8f531228bbe4e29e3c58b51d226b3c3fe21cbf01ae8ecf7d6b7ca6e86a6e93.

Freeze this registration, runtime, packages, control manifest, execution inputs,
reviews and verification records before the following serial sequence. Stop at
the first failed gate; no favorable reroll or post-result relaxation.

| Cell | Task | Arm | Owner | Peer |
| --- | --- | --- | --- | --- |
| s01-h-codex | S2 | H | gpt-6-astra / max | gpt-6-astra / max |
| s02-p-claude | S2 | P | claude-opus-5-5 / max | gpt-6-astra / max |
| s03-p-codex | S2 | P | gpt-6-astra / max | claude-opus-5-5 / max |

Prediction: fresh and resumed Codex peers receive both agents.enabled=false and
features.multi_agent_v2.enabled=false. Their actual initial native request tool
definitions omit delegation tools, including collaboration, and their native
instructions omit multi_agent_role/multi_agent_mode. Owners retain their native
capabilities. All transports complete at the registered primary/max identity,
with stable source, original-request fidelity, completed answers, an executed
witness, complete whole-run usage, valid local delivery and clean teardown.

Inspect every captured attempt and bind its initial request to its native
session. An absent catalog in an incremental request, correct CLI argv, or no
observed spawn alone proves neither tool removal nor handler denial. No security
boundary claim is made. Reject any peer descendant or independent recursive
launch. Claude peers retain Read/Grep/Glob restrictions; record only CLAUDECODE
presence, never remove it or expose credentials. Missing terminal usage remains
UNKNOWN with known lower bounds. Existing identity/accounting STOP and product
incompleteness gates retain their original distinctions.

S2 forces fresh and same-session resume without a hidden oracle. Source/public
checks still apply. Success does not establish automatic pair activation, better
reasoning, speed or token savings. Reuse 0238 s01-h-claude-v3 only for observed
unchanged Claude-to-Claude launcher, native identity, fresh/resume transport and
teardown facts; it did not execute the new package or discovery/policy adapter.

No independent study model call, reviewer or heavy test may overlap an owner.
Supported login/profile preflight retains its 6300-second lifetime margin. Image
is sha256:0f472bb41685b7daa5923d51d31983f4b3c70053dd773fdf712bd0dcd6d87998;
owner --init/PID256/memory4g/CPU2, owner5400/review600/evaluator600/peer540 seconds.
No token, cost or call budgets, credential edits or background-wait changes.

These operational packs intentionally retain the frozen 4.2.3 study base. Main
has independently advanced to 4.2.4. Any subsequent efficacy comparison must
separately register and install the verified integrated 4.2.4 strongest solo
baseline, with an ordinary unforced F23 request and actual startup catalogs.
