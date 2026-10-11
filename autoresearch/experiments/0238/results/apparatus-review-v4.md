# 0238 owner-init integration review v4

2026-10-10. REVISE the staging freeze check before staging against v4. No HIGH finding; one MEDIUM finding below. The two-line runner integration and new owner lifecycle are otherwise sound in this bounded source review. No product, native CLI, Docker, or staging operation was performed.

## MEDIUM — staging does not enforce the new native-dependency freeze

`results/stage.py`, in `stage`, validates `freeze["files"]` and `freeze["shared_process_dependency"]`, but never reads `pair_native_dependencies`, newly added to apparatus-review-manifest-v4.json. Consequently a change to the reviewed 0234 cell.py, evidence.py or record_usage.py between review and staging is accepted by that staging boundary. The runner's later inputs seal records those current bytes, so it detects subsequent drift but does not establish equality to the reviewed v4 dependency identities.

Validate every path/hash in the native-dependency map before creating the destination, just as the shared process dependency is validated. A bounded negative test can change an expected hash in a copied manifest and verify rejection before destination creation; no real Docker, authentication, or staging output is needed. This is a missing check on an explicit new freeze field, not a request for a broader sealing framework.

## Verified scope

- runner.py has exactly the two expected changes from preserved v3: select local cell-init-v1.py and include it in inputs. Existing usage, source/delivery classification and repaired peer-attempt semantics are unchanged.
- cell-init-v1.py imports the 0234 lifecycle and native evidence, not 0233 identity. The run body preserves 0234 labels, native owner effort validation, ended_at timing, arguments, credentials and teardown; Docker --init is the intended added argument. Usage and identity share the rebound 0234 evidence object.
- stage.py generically validates every freeze.files member, so the newly listed owner file is checked. The identified omission concerns only the separately listed native dependencies.
- All seven source hashes and all three native dependency hashes currently match v4. The manifest SHA-256 is e85487aa88210d7caac68ccaf190386559026af8e604bb286267bb3c75a959fd. Runner SHA-256: 80f14a65f9f0e5af89eaca78cf8170cb5d93ba8e35cd6228f4cdd6be51bd0d48. Owner SHA-256: daa0e64da8b745746b1abb4445317b965ce1dca5d385e993379a71e20022266f.
- Inspected retained targeted output: 14 tests passed in 13.515 seconds, including lifecycle parity, actual recorded create argv, effort mismatch, peer accounting/recovery and existing product classifications. The initial test helper name-shadowing failure and correction remain preserved. Tests were not rerun in this review.

The separate 0237 real init calibration does not prove authenticated 0238 native peer behavior. Those smokes remain pending; historical full-check packets are classification replays, not new evaluations under init. No product admission, registration, efficacy claim or model dispatch is authorized by this review.
