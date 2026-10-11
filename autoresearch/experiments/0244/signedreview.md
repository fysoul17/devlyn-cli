# 0244 signed implementation review

Verdict: **SHIP for the registered prospective operational validation**. Zero CRITICAL, HIGH, or MEDIUM findings. This verdict is conditional on the required immutable input seal and unchanged preflight gates; it is not efficacy admission or a regrade of 0242.

Signed: independent review agent `/root/review_0242`, 2026-10-10 UTC. One risk-scaled review round. Read-only source, evidence, runtime and regression review; no native/model/authentication calls and no tests executed by this reviewer. Only this review file was written.

## Source and scope

The implementation matches the reviewed design under **No workaround** and **No overengineering**. Relative to exact 0241 capture discovery, it adds terminal_candidate and applies it only to unbound files and tool-output JSON. Expected carrier files bypass the new predicate and retain all existing unreadable/sessionless/counterless handling. The predicate uses field presence, not truthiness or validity: result/errors/modelUsage/usage fields containing empty or null values remain visible to the unchanged accounting layer. There is no filename or summary-marker exception, gap filtering, inferred usage, or saved-result rewrite.

The small runner inherits 0242, replaces only the private evidence inventory's Claude envelope collector, verifies that identity and usage share that inventory, and seals both new implementation files. Independent Runner instances and separately loaded historical modules keep separate inventories. The CLI entry point reaches the actual underlying 0238 main/Runner binding. Policy, peer-child gates, helper argv, source/delivery checks, task semantics, guides, packages and accounting are inherited unchanged.

**Production ready:** receipt declarations/custody, legacy dispatches and observed capture paths remain unconditional evidence obligations. Actual missing or incomplete terminal counters are not excluded by the new unbound predicate. The existing observed-launch/native-session gates still detect missing results independently. The design correctly acknowledges that an arbitrary summary copying all native terminal fields cannot be distinguished by content alone; the predicate classifies candidates and does not claim universal execution provenance.

## Evidence reviewed

The retained replay changes three candidates to the two actual fresh/resume native captures, without unreadable carriers. I independently hashed all 18 protected replay inputs: no drift. The original 0242 s03 remains STOP/PARTIAL with the recorded 1,325,063 input / 45,755 output lower bound; neither discovery replay nor this review establishes a replacement whole-run verdict.

The new regression run reports **40 tests passed**, exit 0, 2.005 seconds of unittest time (2.127 seconds wall). I inspected assertions and the raw log. This is 34 inherited functional runner cases plus six new cases, with the obsolete exact-old-inventory assertion replaced by the new isolation/sealing case. It covers the exact retained summary as file/custody/inline data, a genuine native result stripped of both usage fields, expected minimal counterless carriers, empty/null terminal or usage keys, inline counterless terminal payload, and private shared inventory wiring. Inherited cases retain arbitrary redirects, missing/malformed/counterless captures, dynamic launches without result carriers, unknown native sessions, interrupted usage, source mutation, ancestry and failed helper attempts. The v1 report records 51 unchanged source hashes; its exact test source is preserved at results/tests-v1-source/test_runner.py. A subsequently added single nonempty invalid-counter case passed in the targeted v2 run (1 test, 0.049 seconds unittest / 0.157 seconds wall), with STOP and the known lower bound retained. This is 40 inherited/new cases plus one targeted addition, not a claim that a 41-case full run occurred. The only v1-to-v2 source change is that added test; all 51 current v2 source hashes match. The unchanged 12 peer/adapter tests use prior evidence and were not represented as rerun here.

The reviewed 0242 manifest's 53 files have no drift. The new runtime differs from 0242 only in output destination. Registration-smoke.md requires one new S2 P/Codex cell, complete fresh/resumed Claude evidence, exact prior packages/controls, all costs, clean teardown, and no overlapping independent reviewer or heavy test. It explicitly requires the exact-summary regression even if the stochastic native run produces no summary. Reusing successful observations on unchanged transport paths is appropriate; a full transport reroll is unnecessary for this collector-only change.

## Bound hashes and remaining gate

- DESIGN.md: `a7883178a282c338a50981b55a261512a1ffff88f42f18a4306a72b897e0c58c`
- capture_discovery.py: `ed34007176d18f1422d009d0eaed3890548eb9fe88d2690e80776bb204ceea63`
- runner.py: `46666d42cdfaefe1abe1393d6df8734e0f4283154a0300c2ba9ba446688406f6`
- test_runner.py (current): `d4dc3f9bdfe7ac148d97d49fee26ceb18e4f317ccc5aacd6894d2a79d633006a`
- results/tests-v1-source/test_runner.py: `d3b3b95aefea72857535506d40b144a59383f8d4e99314926af8be6daeff7b82`
- registration-smoke.md: `2aba03ae9831be39389546da9d7f60270fbc3c1edfc78a4ebefedc3bbfd66caa`
- runtime-smoke.json: `e201a1c3f7bb8634cc99a00000a483bdb20e9b64c0e1292ddc6d1428ec85389c`
- discovery-replay-v1.json: `48b6452fc23f7c87ceeca8b9a895a8b1c3fdc3f8a7c7a2b2b3c1a178563b5267`
- tests-v1.json: `b07e2572c7e184961b49f2a8f6ee83af14751d13cefc9321fbb765b7b06d4535`
- tests-v1.stderr: `1e5275d8e89b52d84ce15090d568d7f8d474e77f6450ab7b2e627c646413430b`

- tests-v2.json: `480f7ae01633ec6b2371a422a57ea6f03e2897129d6e0bc5ecd45b7dafd97c1e`
- tests-v2.stderr: `269d1653e3b4a703bba9eedf5a8feeaaa9b6525af81b53698274ce32946fc0c3`

The parent must seal the execution inputs, selected prior artifacts, registration, review and raw test evidence before the one registered native cell. Authentication margin and all failure gates remain unchanged. Stop on a failed gate; preserve blocked or failed attempts and their costs. A passing native cell can support apparatus validation only; 0243 still needs its separate efficacy registration and freeze.
