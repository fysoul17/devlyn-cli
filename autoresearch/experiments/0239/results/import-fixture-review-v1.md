# Installer fixture repairs — bounded review

2026-10-10. SHIP. No HIGH or MEDIUM findings in the two fixture-only edits. This review does not reopen the accepted import detector.

The manifestless-history test now seeds the existing exact published 4.1.0 fixture before deleting manifests. The retained diagnosis establishes why installing the unreleased current tree was invalid preparation: its changed shared-skill fingerprint is not in published history. The test still tracks both skill roots in Git, changes all three next-package default directories, installs that next package and asserts the new defaults arrive in both roots. It therefore continues to test historical ownership rather than adding the unreleased hash or weakening refusal rules. The existing seed_4_1 helper extracts the retained publication fixture and creates the manifest that this test deliberately removes.

The incomplete-package lint fixture now includes node_modules alongside its copied package sources. This lets the synchronous bundled Marked import load so the intended missing-devlyn-engines condition is reached. The missing skill remains deliberately removed; both project/global failure messages, partial copied skill evidence and absence of stale/replacement install markers remain required. This repairs package construction rather than bypassing the guard.

No product edits, native/model/auth calls or test reruns were performed in this source review. Root's full test/lint reruns remain the validation gate; their outcomes are not claimed here.

Exact checked identities:

- `scripts/test-windows-portability.py`: `425231bc48b31287a2343c5c3986c7a8ced235571730addeb434ed96b1bf11bb`
- `scripts/lint-skills.sh`: `ee64d473c8de16504eb2dbb867b02433c8a15cc5ba9505bc8679a5b14343a892`
- `scripts/fixtures/installer-4.1.0.tar.gz`: `52ba0a13f10b210fc1ca6d67ebdc70dd12b1b89e4dd729bf1a72378033b90058`
- `bin/instructions.js`: `c2ef3fda7714efab8e1569a4d08ec17abc1a10469133b11b159d0884f7bb2532`
- `autoresearch/experiments/0239/results/installer-fixture-diagnosis-v1.json`: `b1ca26ea5ec15bd1ed26a38f9984576b1e032fd127771cae4e355f1603bc9ccc`
