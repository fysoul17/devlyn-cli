# 0249 runner review v1

Scope: independent local adapter review only; no final registration review, no remote cross-model claim. Product files are read-only.

## Prediction recorded before probes

2026-10-10T23:37:42.494645+00:00

Before probes: the four committed-in-preparation tests will pass; B5 will invoke exactly the five original 0233 rows, E1 will retain 0234 routing, valid OR1/OR2 mixed rows will survive exit 0, and oracle exit 1/124/None-with-timeout will raise ValueError with full raw evidence. Public exit 1/124 remains an ordinary failed public check, consistent with inherited semantics. Startup exits 125/126/127 remain inherited NoVerdict. Separate runner instances will not mutate each other’s task globals; the seven-legacy CLI entry resolves to 0238. No native model/container calls will be made.

Principles: **No workaround** (restore original B5 oracle), **No overengineering** (narrow adapter), **No guesswork** (prospective prediction and raw probes), **Production ready** (explicit incomplete-verdict STOP).

## Input SHA-256 before probes

```json
{
  "AGENTS.md": "4823ba898cdf99ce24366a3d1983af63cdb14d2e1b95b5bdafea49097f457ff5",
  "autoresearch/experiments/0222/assess.py": "d0bc568d4cabbcbc885087bd2eea5f61db48c0bb33c75b839774452dca2b2f16",
  "autoresearch/experiments/0222/calibrate.py": "52981f4f697fbf2eaa31ded954a83e810f1dd7f0aa6620ffbf01152f1d3157d1",
  "autoresearch/experiments/0222/cell.py": "3fcf90cbecf6ada5ac3a89f8903073f43931db1b1608170745bbea834baa11ce",
  "autoresearch/experiments/0222/check.py": "7035e18e3876c5d80bc8177bff61979a5a8862a376078ec1ac41e3b969dd99d9",
  "autoresearch/experiments/0222/control.py": "314be6c74baab2efcb49b63f7630802210824e023430e0e5ce814a0cd28b16cd",
  "autoresearch/experiments/0222/packet.py": "cc481c058580262e40b9215e93478f1efdf4fc6576288b891e485465812777ac",
  "autoresearch/experiments/0222/prepare.py": "2bf760a2654773290e02dda6c14c7a13dd426242aa10ea2d73ed690348db77bf",
  "autoresearch/experiments/0222/record_usage.py": "303029c25517f31765c8bdc08e200f2cf56c93d2e9cb472f39b52f093952ce89",
  "autoresearch/experiments/0222/review.py": "5f8bcb36ef62638117a81da7f8b7158970e180b95d3f567b601e7b0d39c31f51",
  "autoresearch/experiments/0222/run_cell.py": "cb7cabc044430cf19eaf738bbad2b613ec3df56af7a7b18d21e1f2884b6e2a0b",
  "autoresearch/experiments/0222/test_apparatus.py": "5fddf80e965cac1e6ab3c8d6894f3bdaa97543474d87bab11beed6531d062fd9",
  "autoresearch/experiments/0233/assess.py": "d04c79ebc26f28215ab50be5b932191a465fd0aac214bfadcc2d13a6c30761b1",
  "autoresearch/experiments/0233/calibrate.py": "24e5ff9e56adfbb4e4372d71c375541e95ba1424a264ba60acd7333fc0c44f90",
  "autoresearch/experiments/0233/cell.py": "06c2258058acb4c69371b0a7ad342e1c57939bbe562fa97143a8530cc4247a4b",
  "autoresearch/experiments/0233/check.py": "59f08d3c5ac1a507b1f40385c97e11edb9aad37bbb470418549f2df4038b8b33",
  "autoresearch/experiments/0233/control.py": "44e37999a60fc99c61c29577218d1f02e5220e03a5879b6673f58cd87c5dd0f2",
  "autoresearch/experiments/0233/decide.py": "c9e9836967ce0d4b81182a8182830bcda856734cb28c5939d9c36ab4bc368f16",
  "autoresearch/experiments/0233/diagnostics.py": "6cfd616ff8d71a436608f436d59d875953e5838548096130b20f337e36d1d516",
  "autoresearch/experiments/0233/evidence.py": "72d4374d57f55ea7389e5b4721926450c5397076d04459e33f3bdf4676b61e1a",
  "autoresearch/experiments/0233/generate_cells.py": "c9e58ffbd6f0f505554bc3f77418c65e673d108b6aa97e61fd689f98cb54dac4",
  "autoresearch/experiments/0233/locate.py": "8b51ef1e71723624bdeab9ece12cf109c4dd11b4edd379e818dc977badc84c19",
  "autoresearch/experiments/0233/prepare.py": "22a800339d6dd65c5a8e4fbfaf8e1deca8f099193d57251004325f1a09ba706e",
  "autoresearch/experiments/0233/quota.py": "380f59b077db09f2bad5f4e734bf8a62e0db69b2a154fa5b5da67946378e3790",
  "autoresearch/experiments/0233/record_usage.py": "9d0fd51b8ff34b7b853b4390e0d26f61472125de1a0ebb0b6d35cbd43ab16b8e",
  "autoresearch/experiments/0233/run_cell.py": "f033800e008927faf68101959b2dffd5a9f10fe1d0ede857650c4728cceb021e",
  "autoresearch/experiments/0233/test_apparatus.py": "c7ba3476c7acdf36b5e87fd79c4a2be4517cde09f6b2f89ef5289b03fe2ec4ce",
  "autoresearch/experiments/0234/assess.py": "d04c79ebc26f28215ab50be5b932191a465fd0aac214bfadcc2d13a6c30761b1",
  "autoresearch/experiments/0234/calibrate.py": "247c9a620586121df867773e9fbd455d45a288c8241ab995bfa6de89f67cb7ae",
  "autoresearch/experiments/0234/cell.py": "fabfd55829c2873e06f42abefab598ee8a717e636122a108b03faee0e9e6f0c5",
  "autoresearch/experiments/0234/check.py": "278d62147f5b706b1b203f3a4d2d9b3387863f49ee4e91451b2fafdf4ccf75bc",
  "autoresearch/experiments/0234/control.py": "2b211784578136f73a902fb94556b9e83c59991dfb2d670f53e077c0cf18bc41",
  "autoresearch/experiments/0234/decide.py": "62baeff461e0d707e4b499862cad780e9d7cbe7e3f47e64af72ec38f12a92931",
  "autoresearch/experiments/0234/diagnostics.py": "0a4d620c71384b09c9ce0ee7f5e9a08deacebd44836fbbf3c835247172572c38",
  "autoresearch/experiments/0234/evidence.py": "595f9018b489034a38c7be61b15e046ec66a393d5ea0c12d9f7e13c8b80de691",
  "autoresearch/experiments/0234/generate_cells.py": "083a2136cc7450f957699badf3afa3a8bf662fc567cf3ba71a7a7fcc0579a2f0",
  "autoresearch/experiments/0234/locate.py": "0a3b1aa5a0118e8dfefba9d0e7383e3834e3508672849a452a0b5bc0a83f6360",
  "autoresearch/experiments/0234/prepare.py": "2aad745ad61b38b65e07c80bb7f6974c756d876b5529a3f7227e1de1484f7294",
  "autoresearch/experiments/0234/quota.py": "380f59b077db09f2bad5f4e734bf8a62e0db69b2a154fa5b5da67946378e3790",
  "autoresearch/experiments/0234/record_usage.py": "7692df70d31e2bbef1cec23f081e0040eeb7f58dd7b08bd99df7ff6bdb32f164",
  "autoresearch/experiments/0234/run_cell.py": "e0d4925f02334ead873ce6ac237889a40be78eb81f8f7b9a376dca022ba3349b",
  "autoresearch/experiments/0234/test_apparatus.py": "d38fc91b262b5a15fbbf1d1d94327b7410b7efad2b165501d488d66ebc0b3c51",
  "autoresearch/experiments/0237/build_confirmation_packages.py": "f190b3cce1d5fc980d41360dc8df300d42f73ab8fb21ba4b4498151992a11d82",
  "autoresearch/experiments/0237/cell-init-v1.py": "1312168b0125cedd80f5aefc16f09befc54d05d3fd1177dfa2fcdd9e100ead02",
  "autoresearch/experiments/0237/delivery.py": "df468212467d189dd3d7f75980bcb58948dcaa2a51396fc2d0fda76111d7e0f6",
  "autoresearch/experiments/0237/dispatch.py": "9bd37cc34c6ef31a0754a9b56affc58d427294228c991ee30b9a88897e9db8e7",
  "autoresearch/experiments/0237/runner-init-v1.py": "351d1f2d3e4960d5f49162124bb55880281e6a91fd49a521a657935b0dbdcc91",
  "autoresearch/experiments/0237/runner.py": "e69f8a0a3f24163b349ba3175464997d651ef7ed9341aad30c62222393328f2d",
  "autoresearch/experiments/0237/test_runner.py": "18c4d79e5bb632a9e523cdd1576de5ed53c5caab0fba2755ecca1e86cc909984",
  "autoresearch/experiments/0237/test_runner_init_v1.py": "54460bd78a7cbf788a6b7f7c989095ada28d9f3f9f0ac031b7f2b1563791f384",
  "autoresearch/experiments/0238/build_packages.py": "197d92ae282ba7693d8e6584eba6a3ecd4687b25f5d3d6e36903390db6bb1a51",
  "autoresearch/experiments/0238/cell-init-v1.py": "daa0e64da8b745746b1abb4445317b965ce1dca5d385e993379a71e20022266f",
  "autoresearch/experiments/0238/claude-accounting-v1.py": "706d56f9ec46be57abe1528d7b0c5d320bfcc8a036bcd97cf1dbe8a0f8fa2914",
  "autoresearch/experiments/0238/f23_precision.py": "47124cac8635717d90d22cb5719579e611952e3925ec3ef28a2f678312fe9e89",
  "autoresearch/experiments/0238/peer.py": "d500dc6ca46c5ab1528c6d419530ad89094f36443461979c6aa1d27933fa3294",
  "autoresearch/experiments/0238/policy.py": "d02be3a1700c0a78aab0d141580da7eacc97be97a60ea7cfc27e9bd31b154606",
  "autoresearch/experiments/0238/runner.py": "5370feb1a9e46dc5abd67e6954cb2019b1ba246d216da7254270e79b17781997",
  "autoresearch/experiments/0238/test_claude_accounting.py": "73aba2dd3c04457b072b65ff761630795227fc85f5dd82f2aa18599277e3f300",
  "autoresearch/experiments/0238/test_peer.py": "c06be9e3fa81275b420f305de76aa686d22bc250d5c165aa0aa959aefff02a27",
  "autoresearch/experiments/0238/test_runner.py": "6db017e16cf5822ed3f240834670f1bd357e84bc62210ac59b49bbb9ff013b48",
  "autoresearch/experiments/0240/build_packages.py": "7378de371e30c4bbbc7796d5161a320e82e7fcf042f7e224a269532a727d3c39",
  "autoresearch/experiments/0240/peer.py": "b863d9879c7ef717cfab4c915d277bce822b7ed4887a0eb2c5e9a13afe28c43a",
  "autoresearch/experiments/0240/runner.py": "b0a1ea36de6033db71625f1b265e31fa2acb31addf3e29ac1e79169f96bb84af",
  "autoresearch/experiments/0240/test_adapters.py": "a8375922687e0727c243fa256df0aee532e932fed81ce3bf63852f284f06daa0",
  "autoresearch/experiments/0240/test_peer.py": "c17fbd9e1411bbc8fddb37707c6b7492787dbc440a78c0c455f5675ee278786e",
  "autoresearch/experiments/0240/test_runner.py": "09425562022d100b13d1817ebb7b797a38f5020f7fa25636ce469d96a28ed296",
  "autoresearch/experiments/0241/build_packages.py": "7378de371e30c4bbbc7796d5161a320e82e7fcf042f7e224a269532a727d3c39",
  "autoresearch/experiments/0241/capture_discovery.py": "a74a17a429a4ac1c256913e264a901bdc255ffbadbf1bd3bac24bed023e7d956",
  "autoresearch/experiments/0241/peer.py": "379fd2890b402ba9351d9a922ce0e11dcb33fe986bb095a191fb354e4246c96b",
  "autoresearch/experiments/0241/runner.py": "4cca2cde73b28aa34ded4d347facf76225513990248faa279c3870875d228188",
  "autoresearch/experiments/0241/test_adapters.py": "a8375922687e0727c243fa256df0aee532e932fed81ce3bf63852f284f06daa0",
  "autoresearch/experiments/0241/test_peer.py": "ac05eb7199a77a17d1a8235e6022319a1f497ba2643fafa658e8975f1e9353db",
  "autoresearch/experiments/0241/test_runner.py": "0e269b2dd7907144454878a858b959da370075a17821de8051010b7755195029",
  "autoresearch/experiments/0242/build_packages.py": "7378de371e30c4bbbc7796d5161a320e82e7fcf042f7e224a269532a727d3c39",
  "autoresearch/experiments/0242/peer.py": "f3f4c878847e6d33149cb9d6ebfe6a78dd12eba82d5ce417fdef79ee6af28d95",
  "autoresearch/experiments/0242/policy.py": "04438db12016d0bca6283b7baa9dfd38c609b21973f373b8a35273f6cd0b2975",
  "autoresearch/experiments/0242/runner.py": "9989c055e847aeb84eaae04d0f3f19d9e74144da3423848a3321a7bfc9aea200",
  "autoresearch/experiments/0242/test_adapters.py": "a8375922687e0727c243fa256df0aee532e932fed81ce3bf63852f284f06daa0",
  "autoresearch/experiments/0242/test_peer.py": "fea5a3e9af06714cf6d930a489a1e63f34b09094db068bfbb331fb47b1fda8a0",
  "autoresearch/experiments/0242/test_runner.py": "1344962cadc5ef8c17686f776551d52fba02047afe87d9513b180b8b30e08540",
  "autoresearch/experiments/0244/capture_discovery.py": "ed34007176d18f1422d009d0eaed3890548eb9fe88d2690e80776bb204ceea63",
  "autoresearch/experiments/0244/runner.py": "46666d42cdfaefe1abe1393d6df8734e0f4283154a0300c2ba9ba446688406f6",
  "autoresearch/experiments/0244/test_runner.py": "d4dc3f9bdfe7ac148d97d49fee26ceb18e4f317ccc5aacd6894d2a79d633006a",
  "autoresearch/experiments/0245/build_packages.py": "926854cba40d4b2de912f48073f1b5cc18d63a2bc1bc4792c57b37687f88cd99",
  "autoresearch/experiments/0245/peer.py": "b51b8c9db0b0d6c1b95e0134e6e3b9f83f27d4b63f6fece79b8e852d3d49d095",
  "autoresearch/experiments/0245/runner.py": "504799d9e2f877b095185081e73c82f77a85e23d69cfc81a0ea359cb663390c8",
  "autoresearch/experiments/0245/test_peer.py": "fee0931dbbe2087ae3b8972c0386ebc1b6e17040fe41466c97594e6c20843e8c",
  "autoresearch/experiments/0247/build_packages.py": "8dcfbe5a77aee059477e3e1f5cb1c0ddbb2ade10605f017b7a00541d22fdf022",
  "autoresearch/experiments/0247/capture_discovery.py": "e4b858c182955b5bb17b3a2db0897cd65ce04bf8900e3e6da5f55501fa592a54",
  "autoresearch/experiments/0247/peer.py": "fcd21c454a61135b6d571bfda928efbe78771a30e29f52946e19dd3b7c0e8266",
  "autoresearch/experiments/0247/runner.py": "9ca3adecdce426f071cec509df068632853161ebc4ca3b5c73006a28960989a1",
  "autoresearch/experiments/0247/test_machinery.py": "460577cc30e7ec6986b26893c4ab7864f1c1f876f80c45a30a7c7734d728bad5",
  "autoresearch/experiments/0233/tasks.json": "4034b86cb44e6333c1d86a9e3a7f74bde3841500f0250f9629b0adb78a1665e3",
  "autoresearch/experiments/0234/tasks.json": "ba7e6c7b30ba51cae0b91aae960aa03be123ca84c79e8ba87d49893474050c10",
  "autoresearch/experiments/0237/tasks.json": "eb0bde7363c5c80d7c46202b77a64be5f2d9dac16c7e9c906ff873feb2c7d0c5",
  "autoresearch/experiments/0247/tasks-smoke.json": "61ad6122942e8146460b21c7127f5b438e90cbabcdd2eb7c908011471881ba17",
  "autoresearch/experiments/0249/runner.py": "a2b22bac4e2847580ceb58d337be80f49d9c28d9b45942fee74c2c96638cb41c",
  "autoresearch/experiments/0249/test_runner.py": "58da814e76abf6b34a6d1226dfaf8e51f618a0616b750e838765d0a82eedf3a7",
  "autoresearch/experiments/0249/build_packages.py": "a2b25fe1ac4116ece5480a7efc73a5d31403b6b3a24dc1e4870a7fd2ca9b043e",
  "autoresearch/experiments/0249/fixtures/OR1/task.json": "517ec0d64bdf20eabc29a632a476458ec8427a81c78ca338f426bc8bac88d793",
  "autoresearch/experiments/0249/fixtures/OR1/hidden/oracle.py": "616987477897d0234e78c7749879ba2ba039eca0524498042fd763cbe4d0678c",
  "autoresearch/experiments/0249/fixtures/OR2/task.json": "2b290682b6a5e184868884c3bc60c2150bc3ba9afef89cc6a8ff6312cba2f6f2",
  "autoresearch/experiments/0249/fixtures/OR2/hidden/oracle.py": "cc52f5e8f399f707febe5f6e772520bc7b2280495a018e2920238133c60eb78b"
}
```

## Raw probe result

Command: `python3 -B autoresearch/experiments/0249/results/runner-review-probe-v1.py`

Exit: 0. Raw combined tool output:

```text
test_b5_timeout_preserves_inherited_failed_row (__main__.EdgeTests.test_b5_timeout_preserves_inherited_failed_row) ... ok
test_b5_uses_original_five_orphan_rows_and_retains_source_failure (__main__.EdgeTests.test_b5_uses_original_five_orphan_rows_and_retains_source_failure) ... ok
test_existing_e1_route_stays_on_0234 (__main__.EdgeTests.test_existing_e1_route_stays_on_0234) ... ok
test_fixture_timeout_and_nonzero_preserve_full_raw (__main__.EdgeTests.test_fixture_timeout_and_nonzero_preserve_full_raw) ... ok
test_incomplete_fixture_exit_stops_and_preserves_raw_diagnostics (__main__.EdgeTests.test_incomplete_fixture_exit_stops_and_preserves_raw_diagnostics) ... ok
test_instance_globals_and_cli_entry (__main__.EdgeTests.test_instance_globals_and_cli_entry) ... ok
test_or2_valid_product_failure_and_startup_stop (__main__.EdgeTests.test_or2_valid_product_failure_and_startup_stop) ... ok
test_public_failure_is_preserved (__main__.EdgeTests.test_public_failure_is_preserved) ... ok
test_valid_fixture_failure_keeps_per_obligation_verdict (__main__.EdgeTests.test_valid_fixture_failure_keeps_per_obligation_verdict) ... ok

----------------------------------------------------------------------
Ran 9 tests in 0.223s

OK
```

The probe inherits all four adapter tests and adds five edge-case tests. `subprocess.run` is blocked for the entire test run; evaluator execution is mocked, so these are routing and verdict-contract probes, not native or container validation.

## Findings and verdict

**SHIP — zero CRITICAL, zero HIGH, zero MEDIUM, zero LOW findings.** Stop after this first routine review round.

- `runner.py:27–30,39–40`: original 0233 checker instances receive the registered task inventory and watchdog in both checker and base module. B5’s immutable original five-row inventory matches the current registered B5 rows. Per-instance imports avoid cross-runner global contamination. Actual probes retained B5 row failure and the inherited timeout-as-failed-row semantics.
- `runner.py:41–44`: OR1 and OR2 exit-0 mixed outcomes preserve each obligation. Oracle exit 1, 124, and host timeout (`None`, timeout true) raise `ValueError`; parsed exception JSON retained full stdout, a >3000-character stderr, exit status, and timeout metadata. This is caught by the inherited 0238 run loop and recorded as STOP. Public-check nonzero exits remain public failures and do not trigger the fresh-oracle rule.
- Startup failures 125/126/127 still raise inherited `NoVerdict` before the new guard. Their diagnostic behavior remains inherited (stderr tail); the full-result JSON guarantee applies when inherited evaluation returns a result, including ordinary nonzero and timeout cases. No silent all-FAIL verdict escapes for OR1/OR2 incomplete oracle execution.
- The underlying fresh fixture scripts catch normal import/product exceptions and emit complete exit-0 manifestation inventories. Inherited EQ3 parsing continues to validate manifestation IDs and boolean results. E1 still invokes 0234. The seven-link executable entry resolves to 0238 and binds the new Runner; frame.check.evaluate is bound to the proper instance.
- `inputs()` adds the new runner and builder; inherited 0237 input sealing already covers `0233/*.py`, including the restored checker, and inherited control sealing covers the oracle tree. Native execution, preflight, startup catalogs, evidence/accounting remain inherited; method identity was probed for run/preflight/boot_catalogs. No earlier frozen input changed during review.
- The four supplied tests exercise actual inherited evaluation through mocked process boundaries and catch the observed B5 regression plus nonzero fixture suppression. The review supplement covers OR2, public failures, timeouts, startup refusal, and per-instance globals. Tests require the existing local `0248-live/runtime-measured.json`; that is available for this preparation-scoped harness. No claim of standalone environment portability or final-registration readiness is made.

Scope boundary: no native model calls, no containers, no earlier result reinterpretation, no product edits, and no final registration review. The 0249 candidate package itself is outside this narrow adapter review. Review writes are limited to this report and `runner-review-probe-v1.py`.

## Input SHA-256 after probes

2026-10-10T23:38:43.075065+00:00

Changed inputs: [].

```json
{
  "AGENTS.md": "4823ba898cdf99ce24366a3d1983af63cdb14d2e1b95b5bdafea49097f457ff5",
  "autoresearch/experiments/0222/assess.py": "d0bc568d4cabbcbc885087bd2eea5f61db48c0bb33c75b839774452dca2b2f16",
  "autoresearch/experiments/0222/calibrate.py": "52981f4f697fbf2eaa31ded954a83e810f1dd7f0aa6620ffbf01152f1d3157d1",
  "autoresearch/experiments/0222/cell.py": "3fcf90cbecf6ada5ac3a89f8903073f43931db1b1608170745bbea834baa11ce",
  "autoresearch/experiments/0222/check.py": "7035e18e3876c5d80bc8177bff61979a5a8862a376078ec1ac41e3b969dd99d9",
  "autoresearch/experiments/0222/control.py": "314be6c74baab2efcb49b63f7630802210824e023430e0e5ce814a0cd28b16cd",
  "autoresearch/experiments/0222/packet.py": "cc481c058580262e40b9215e93478f1efdf4fc6576288b891e485465812777ac",
  "autoresearch/experiments/0222/prepare.py": "2bf760a2654773290e02dda6c14c7a13dd426242aa10ea2d73ed690348db77bf",
  "autoresearch/experiments/0222/record_usage.py": "303029c25517f31765c8bdc08e200f2cf56c93d2e9cb472f39b52f093952ce89",
  "autoresearch/experiments/0222/review.py": "5f8bcb36ef62638117a81da7f8b7158970e180b95d3f567b601e7b0d39c31f51",
  "autoresearch/experiments/0222/run_cell.py": "cb7cabc044430cf19eaf738bbad2b613ec3df56af7a7b18d21e1f2884b6e2a0b",
  "autoresearch/experiments/0222/test_apparatus.py": "5fddf80e965cac1e6ab3c8d6894f3bdaa97543474d87bab11beed6531d062fd9",
  "autoresearch/experiments/0233/assess.py": "d04c79ebc26f28215ab50be5b932191a465fd0aac214bfadcc2d13a6c30761b1",
  "autoresearch/experiments/0233/calibrate.py": "24e5ff9e56adfbb4e4372d71c375541e95ba1424a264ba60acd7333fc0c44f90",
  "autoresearch/experiments/0233/cell.py": "06c2258058acb4c69371b0a7ad342e1c57939bbe562fa97143a8530cc4247a4b",
  "autoresearch/experiments/0233/check.py": "59f08d3c5ac1a507b1f40385c97e11edb9aad37bbb470418549f2df4038b8b33",
  "autoresearch/experiments/0233/control.py": "44e37999a60fc99c61c29577218d1f02e5220e03a5879b6673f58cd87c5dd0f2",
  "autoresearch/experiments/0233/decide.py": "c9e9836967ce0d4b81182a8182830bcda856734cb28c5939d9c36ab4bc368f16",
  "autoresearch/experiments/0233/diagnostics.py": "6cfd616ff8d71a436608f436d59d875953e5838548096130b20f337e36d1d516",
  "autoresearch/experiments/0233/evidence.py": "72d4374d57f55ea7389e5b4721926450c5397076d04459e33f3bdf4676b61e1a",
  "autoresearch/experiments/0233/generate_cells.py": "c9e58ffbd6f0f505554bc3f77418c65e673d108b6aa97e61fd689f98cb54dac4",
  "autoresearch/experiments/0233/locate.py": "8b51ef1e71723624bdeab9ece12cf109c4dd11b4edd379e818dc977badc84c19",
  "autoresearch/experiments/0233/prepare.py": "22a800339d6dd65c5a8e4fbfaf8e1deca8f099193d57251004325f1a09ba706e",
  "autoresearch/experiments/0233/quota.py": "380f59b077db09f2bad5f4e734bf8a62e0db69b2a154fa5b5da67946378e3790",
  "autoresearch/experiments/0233/record_usage.py": "9d0fd51b8ff34b7b853b4390e0d26f61472125de1a0ebb0b6d35cbd43ab16b8e",
  "autoresearch/experiments/0233/run_cell.py": "f033800e008927faf68101959b2dffd5a9f10fe1d0ede857650c4728cceb021e",
  "autoresearch/experiments/0233/test_apparatus.py": "c7ba3476c7acdf36b5e87fd79c4a2be4517cde09f6b2f89ef5289b03fe2ec4ce",
  "autoresearch/experiments/0234/assess.py": "d04c79ebc26f28215ab50be5b932191a465fd0aac214bfadcc2d13a6c30761b1",
  "autoresearch/experiments/0234/calibrate.py": "247c9a620586121df867773e9fbd455d45a288c8241ab995bfa6de89f67cb7ae",
  "autoresearch/experiments/0234/cell.py": "fabfd55829c2873e06f42abefab598ee8a717e636122a108b03faee0e9e6f0c5",
  "autoresearch/experiments/0234/check.py": "278d62147f5b706b1b203f3a4d2d9b3387863f49ee4e91451b2fafdf4ccf75bc",
  "autoresearch/experiments/0234/control.py": "2b211784578136f73a902fb94556b9e83c59991dfb2d670f53e077c0cf18bc41",
  "autoresearch/experiments/0234/decide.py": "62baeff461e0d707e4b499862cad780e9d7cbe7e3f47e64af72ec38f12a92931",
  "autoresearch/experiments/0234/diagnostics.py": "0a4d620c71384b09c9ce0ee7f5e9a08deacebd44836fbbf3c835247172572c38",
  "autoresearch/experiments/0234/evidence.py": "595f9018b489034a38c7be61b15e046ec66a393d5ea0c12d9f7e13c8b80de691",
  "autoresearch/experiments/0234/generate_cells.py": "083a2136cc7450f957699badf3afa3a8bf662fc567cf3ba71a7a7fcc0579a2f0",
  "autoresearch/experiments/0234/locate.py": "0a3b1aa5a0118e8dfefba9d0e7383e3834e3508672849a452a0b5bc0a83f6360",
  "autoresearch/experiments/0234/prepare.py": "2aad745ad61b38b65e07c80bb7f6974c756d876b5529a3f7227e1de1484f7294",
  "autoresearch/experiments/0234/quota.py": "380f59b077db09f2bad5f4e734bf8a62e0db69b2a154fa5b5da67946378e3790",
  "autoresearch/experiments/0234/record_usage.py": "7692df70d31e2bbef1cec23f081e0040eeb7f58dd7b08bd99df7ff6bdb32f164",
  "autoresearch/experiments/0234/run_cell.py": "e0d4925f02334ead873ce6ac237889a40be78eb81f8f7b9a376dca022ba3349b",
  "autoresearch/experiments/0234/test_apparatus.py": "d38fc91b262b5a15fbbf1d1d94327b7410b7efad2b165501d488d66ebc0b3c51",
  "autoresearch/experiments/0237/build_confirmation_packages.py": "f190b3cce1d5fc980d41360dc8df300d42f73ab8fb21ba4b4498151992a11d82",
  "autoresearch/experiments/0237/cell-init-v1.py": "1312168b0125cedd80f5aefc16f09befc54d05d3fd1177dfa2fcdd9e100ead02",
  "autoresearch/experiments/0237/delivery.py": "df468212467d189dd3d7f75980bcb58948dcaa2a51396fc2d0fda76111d7e0f6",
  "autoresearch/experiments/0237/dispatch.py": "9bd37cc34c6ef31a0754a9b56affc58d427294228c991ee30b9a88897e9db8e7",
  "autoresearch/experiments/0237/runner-init-v1.py": "351d1f2d3e4960d5f49162124bb55880281e6a91fd49a521a657935b0dbdcc91",
  "autoresearch/experiments/0237/runner.py": "e69f8a0a3f24163b349ba3175464997d651ef7ed9341aad30c62222393328f2d",
  "autoresearch/experiments/0237/test_runner.py": "18c4d79e5bb632a9e523cdd1576de5ed53c5caab0fba2755ecca1e86cc909984",
  "autoresearch/experiments/0237/test_runner_init_v1.py": "54460bd78a7cbf788a6b7f7c989095ada28d9f3f9f0ac031b7f2b1563791f384",
  "autoresearch/experiments/0238/build_packages.py": "197d92ae282ba7693d8e6584eba6a3ecd4687b25f5d3d6e36903390db6bb1a51",
  "autoresearch/experiments/0238/cell-init-v1.py": "daa0e64da8b745746b1abb4445317b965ce1dca5d385e993379a71e20022266f",
  "autoresearch/experiments/0238/claude-accounting-v1.py": "706d56f9ec46be57abe1528d7b0c5d320bfcc8a036bcd97cf1dbe8a0f8fa2914",
  "autoresearch/experiments/0238/f23_precision.py": "47124cac8635717d90d22cb5719579e611952e3925ec3ef28a2f678312fe9e89",
  "autoresearch/experiments/0238/peer.py": "d500dc6ca46c5ab1528c6d419530ad89094f36443461979c6aa1d27933fa3294",
  "autoresearch/experiments/0238/policy.py": "d02be3a1700c0a78aab0d141580da7eacc97be97a60ea7cfc27e9bd31b154606",
  "autoresearch/experiments/0238/runner.py": "5370feb1a9e46dc5abd67e6954cb2019b1ba246d216da7254270e79b17781997",
  "autoresearch/experiments/0238/test_claude_accounting.py": "73aba2dd3c04457b072b65ff761630795227fc85f5dd82f2aa18599277e3f300",
  "autoresearch/experiments/0238/test_peer.py": "c06be9e3fa81275b420f305de76aa686d22bc250d5c165aa0aa959aefff02a27",
  "autoresearch/experiments/0238/test_runner.py": "6db017e16cf5822ed3f240834670f1bd357e84bc62210ac59b49bbb9ff013b48",
  "autoresearch/experiments/0240/build_packages.py": "7378de371e30c4bbbc7796d5161a320e82e7fcf042f7e224a269532a727d3c39",
  "autoresearch/experiments/0240/peer.py": "b863d9879c7ef717cfab4c915d277bce822b7ed4887a0eb2c5e9a13afe28c43a",
  "autoresearch/experiments/0240/runner.py": "b0a1ea36de6033db71625f1b265e31fa2acb31addf3e29ac1e79169f96bb84af",
  "autoresearch/experiments/0240/test_adapters.py": "a8375922687e0727c243fa256df0aee532e932fed81ce3bf63852f284f06daa0",
  "autoresearch/experiments/0240/test_peer.py": "c17fbd9e1411bbc8fddb37707c6b7492787dbc440a78c0c455f5675ee278786e",
  "autoresearch/experiments/0240/test_runner.py": "09425562022d100b13d1817ebb7b797a38f5020f7fa25636ce469d96a28ed296",
  "autoresearch/experiments/0241/build_packages.py": "7378de371e30c4bbbc7796d5161a320e82e7fcf042f7e224a269532a727d3c39",
  "autoresearch/experiments/0241/capture_discovery.py": "a74a17a429a4ac1c256913e264a901bdc255ffbadbf1bd3bac24bed023e7d956",
  "autoresearch/experiments/0241/peer.py": "379fd2890b402ba9351d9a922ce0e11dcb33fe986bb095a191fb354e4246c96b",
  "autoresearch/experiments/0241/runner.py": "4cca2cde73b28aa34ded4d347facf76225513990248faa279c3870875d228188",
  "autoresearch/experiments/0241/test_adapters.py": "a8375922687e0727c243fa256df0aee532e932fed81ce3bf63852f284f06daa0",
  "autoresearch/experiments/0241/test_peer.py": "ac05eb7199a77a17d1a8235e6022319a1f497ba2643fafa658e8975f1e9353db",
  "autoresearch/experiments/0241/test_runner.py": "0e269b2dd7907144454878a858b959da370075a17821de8051010b7755195029",
  "autoresearch/experiments/0242/build_packages.py": "7378de371e30c4bbbc7796d5161a320e82e7fcf042f7e224a269532a727d3c39",
  "autoresearch/experiments/0242/peer.py": "f3f4c878847e6d33149cb9d6ebfe6a78dd12eba82d5ce417fdef79ee6af28d95",
  "autoresearch/experiments/0242/policy.py": "04438db12016d0bca6283b7baa9dfd38c609b21973f373b8a35273f6cd0b2975",
  "autoresearch/experiments/0242/runner.py": "9989c055e847aeb84eaae04d0f3f19d9e74144da3423848a3321a7bfc9aea200",
  "autoresearch/experiments/0242/test_adapters.py": "a8375922687e0727c243fa256df0aee532e932fed81ce3bf63852f284f06daa0",
  "autoresearch/experiments/0242/test_peer.py": "fea5a3e9af06714cf6d930a489a1e63f34b09094db068bfbb331fb47b1fda8a0",
  "autoresearch/experiments/0242/test_runner.py": "1344962cadc5ef8c17686f776551d52fba02047afe87d9513b180b8b30e08540",
  "autoresearch/experiments/0244/capture_discovery.py": "ed34007176d18f1422d009d0eaed3890548eb9fe88d2690e80776bb204ceea63",
  "autoresearch/experiments/0244/runner.py": "46666d42cdfaefe1abe1393d6df8734e0f4283154a0300c2ba9ba446688406f6",
  "autoresearch/experiments/0244/test_runner.py": "d4dc3f9bdfe7ac148d97d49fee26ceb18e4f317ccc5aacd6894d2a79d633006a",
  "autoresearch/experiments/0245/build_packages.py": "926854cba40d4b2de912f48073f1b5cc18d63a2bc1bc4792c57b37687f88cd99",
  "autoresearch/experiments/0245/peer.py": "b51b8c9db0b0d6c1b95e0134e6e3b9f83f27d4b63f6fece79b8e852d3d49d095",
  "autoresearch/experiments/0245/runner.py": "504799d9e2f877b095185081e73c82f77a85e23d69cfc81a0ea359cb663390c8",
  "autoresearch/experiments/0245/test_peer.py": "fee0931dbbe2087ae3b8972c0386ebc1b6e17040fe41466c97594e6c20843e8c",
  "autoresearch/experiments/0247/build_packages.py": "8dcfbe5a77aee059477e3e1f5cb1c0ddbb2ade10605f017b7a00541d22fdf022",
  "autoresearch/experiments/0247/capture_discovery.py": "e4b858c182955b5bb17b3a2db0897cd65ce04bf8900e3e6da5f55501fa592a54",
  "autoresearch/experiments/0247/peer.py": "fcd21c454a61135b6d571bfda928efbe78771a30e29f52946e19dd3b7c0e8266",
  "autoresearch/experiments/0247/runner.py": "9ca3adecdce426f071cec509df068632853161ebc4ca3b5c73006a28960989a1",
  "autoresearch/experiments/0247/test_machinery.py": "460577cc30e7ec6986b26893c4ab7864f1c1f876f80c45a30a7c7734d728bad5",
  "autoresearch/experiments/0233/tasks.json": "4034b86cb44e6333c1d86a9e3a7f74bde3841500f0250f9629b0adb78a1665e3",
  "autoresearch/experiments/0234/tasks.json": "ba7e6c7b30ba51cae0b91aae960aa03be123ca84c79e8ba87d49893474050c10",
  "autoresearch/experiments/0237/tasks.json": "eb0bde7363c5c80d7c46202b77a64be5f2d9dac16c7e9c906ff873feb2c7d0c5",
  "autoresearch/experiments/0247/tasks-smoke.json": "61ad6122942e8146460b21c7127f5b438e90cbabcdd2eb7c908011471881ba17",
  "autoresearch/experiments/0249/runner.py": "a2b22bac4e2847580ceb58d337be80f49d9c28d9b45942fee74c2c96638cb41c",
  "autoresearch/experiments/0249/test_runner.py": "58da814e76abf6b34a6d1226dfaf8e51f618a0616b750e838765d0a82eedf3a7",
  "autoresearch/experiments/0249/build_packages.py": "a2b25fe1ac4116ece5480a7efc73a5d31403b6b3a24dc1e4870a7fd2ca9b043e",
  "autoresearch/experiments/0249/fixtures/OR1/task.json": "517ec0d64bdf20eabc29a632a476458ec8427a81c78ca338f426bc8bac88d793",
  "autoresearch/experiments/0249/fixtures/OR1/hidden/oracle.py": "616987477897d0234e78c7749879ba2ba039eca0524498042fd763cbe4d0678c",
  "autoresearch/experiments/0249/fixtures/OR2/task.json": "2b290682b6a5e184868884c3bc60c2150bc3ba9afef89cc6a8ff6312cba2f6f2",
  "autoresearch/experiments/0249/fixtures/OR2/hidden/oracle.py": "cc52f5e8f399f707febe5f6e772520bc7b2280495a018e2920238133c60eb78b"
}
```
