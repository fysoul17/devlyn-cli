# 0240 implementation review v1

**SHIP-for-native-validation. No HIGH finding in the reviewed implementation.** This is approval to validate the prospective apparatus, not product adoption, dispatch authorization or proof of native tool removal/efficacy.

The manifest SHA256 is `a266c706c6a350467acd5430ce541cd790e97818e11ef09809b0a1a7d2e79353`; independently rehashed all24 listed files with zero mismatches. Reviewed exact helper/guide/task diffs, adapter implementations, inherited runner/policy/builder/stager integration and the25-test source/raw result. No native/model/auth/container/test execution or source/frozen-input edits performed in this review.

## Findings

The helper difference is exactly one Codex-only `-c features.multi_agent=false` argument pair. It is inserted in the shared fresh/resume argv builder before session/prompt position, so both paths receive it. Claude fresh/resume argv is unchanged. The guide H/P change is exactly the no-delegation sentence; S is byte-identical. S2 preserves calculation semantics and changes only the required peer delegation mechanism/owner clarification; routes and owner child configuration remain inherited. Native CLI acceptance and effective tool definitions remain prospective checks, not conclusions from the mock argv controls.

The runner adapter overrides inputs and wraps the inherited peer policy. It retains existing identity/evidence/accounting/source/delivery checks and marks identified peer descendants as protocol violations without subtracting their costs. Owner descendants are untouched. Unknown ancestry remains governed by the inherited fail-closed evidence policy. This enforces observed native ancestry; it is not a universal prevention of shell-launched independent processes. The design correctly retains capture/session inspection for that limitation.

Builder/stager wrappers rebind only the candidate directory and add their own provenance hash, preserving original implementation hashes. Stage retains24-file manifest validation, process-helper binding, exact three0234 native dependency bindings before destination creation, package archive/payload/helper checks, absent destination, and isolated control/runtime construction. Runner.inputs adds the new wrappers/helper/guides and inherited builder/stager to existing seals. Actual package building, installed payload equality, staging and staged evaluator controls were not performed in implementation-v1.json and cannot be inferred from adapter mocks; they remain explicit pre-native prerequisites.

The recorded25 tests pass in4.368s (outer command4.515s), covering fresh/resume override and receipts, unchanged Claude argv, inherited helper failure/source rules, descendant rejection with retained usage, owner child permission, wrong model STOP, unknown usage STOP, inherited Claude cancellation STOP, seal changes, task scope and stage dependency rejection. Evidence reports245 inherited inputs unchanged. No broad suite rerun was warranted for this bounded review.

**No workaround:** the new treatment leaves0238 STOP/UNKNOWN intact and does not repair cancellation accounting. **No overengineering / Best practice:** the one supported peer-only feature override and small inherited adapters implement the intended scope. Owners can still experience cancellation; native validation must retain the same whole-run accounting gate.

One wording limit: DESIGN.md describes cancellation “when its child answered” and says “not a parser defect.” The raw trace supports temporal association and no demonstrated harness omission; it does not prove every native causal detail or rule out a native terminal-usage producer defect. This does not block the implementation or justify changing the prior diagnosis.

## Exact reviewed file hashes

- `../0238/build_packages.py`: `197d92ae282ba7693d8e6584eba6a3ecd4687b25f5d3d6e36903390db6bb1a51`
- `../0238/cell-init-v1.py`: `daa0e64da8b745746b1abb4445317b965ce1dca5d385e993379a71e20022266f`
- `../0238/claude-accounting-v1.py`: `706d56f9ec46be57abe1528d7b0c5d320bfcc8a036bcd97cf1dbe8a0f8fa2914`
- `../0238/f23_precision.py`: `47124cac8635717d90d22cb5719579e611952e3925ec3ef28a2f678312fe9e89`
- `../0238/peer.py`: `d500dc6ca46c5ab1528c6d419530ad89094f36443461979c6aa1d27933fa3294`
- `../0238/policy.py`: `d02be3a1700c0a78aab0d141580da7eacc97be97a60ea7cfc27e9bd31b154606`
- `../0238/results/stage.py`: `9c288dd37a20f114a9ef2d6167da23502748b634b0d6b08870a95c4626d17500`
- `../0238/results/test_stage_native_dependencies.py`: `97fe00153f2059a50decfec62a183faae7fd293fb0a2ecd7b8aeec704be6c2e2`
- `../0238/runner.py`: `5370feb1a9e46dc5abd67e6954cb2019b1ba246d216da7254270e79b17781997`
- `../0238/test_claude_accounting.py`: `73aba2dd3c04457b072b65ff761630795227fc85f5dd82f2aa18599277e3f300`
- `../0238/test_peer.py`: `c06be9e3fa81275b420f305de76aa686d22bc250d5c165aa0aa959aefff02a27`
- `../0238/test_runner.py`: `6db017e16cf5822ed3f240834670f1bd357e84bc62210ac59b49bbb9ff013b48`
- `DESIGN.md`: `5b5ed9eeffa94643290e87511fe747048fa30ded4a1f99376707c77351f40f88`
- `build_packages.py`: `7378de371e30c4bbbc7796d5161a320e82e7fcf042f7e224a269532a727d3c39`
- `guides/H.md`: `e8b73b4edda4b2476605a34b2535ee79085f09883256950fcde49556d668ff84`
- `guides/P.md`: `9523319d650db1d5176261cb00d254e6216915b86d9d222bfacc85cefa23993a`
- `guides/S.md`: `34287e59aa0e32ba09dacb92115715466e1408de0f0620f92fb6ff2db1e9acc3`
- `peer.py`: `b863d9879c7ef717cfab4c915d277bce822b7ed4887a0eb2c5e9a13afe28c43a`
- `results/stage.py`: `0217f2364da868305d676a5583677a5482e55d8aa7ca4307705873da8c864ec1`
- `runner.py`: `b0a1ea36de6033db71625f1b265e31fa2acb31addf3e29ac1e79169f96bb84af`
- `tasks-smoke.json`: `0f8f531228bbe4e29e3c58b51d226b3c3fe21cbf01ae8ecf7d6b7ca6e86a6e93`
- `test_adapters.py`: `a8375922687e0727c243fa256df0aee532e932fed81ce3bf63852f284f06daa0`
- `test_peer.py`: `c17fbd9e1411bbc8fddb37707c6b7492787dbc440a78c0c455f5675ee278786e`
- `test_runner.py`: `09425562022d100b13d1817ebb7b797a38f5020f7fa25636ce469d96a28ed296`

Implementation evidence SHA256: `ff6ca19385c5de7922f8f8f1132c762b0b93c905ab62db587b93e0bd5079de85`.
