# 0238 apparatus review v2

REVISE before registration. Two MEDIUM findings; no HIGH finding established. Diagnostic authenticated native smokes can investigate compatibility, but these classification defects should be fixed before results become registration evidence. This is not a product-shipping review or authorization to dispatch models.

Reviewed 2026-10-10 against results/apparatus-review-manifest-v2.json. All six frozen source hashes match. Source was not edited; only this review was written. No external model CLI calls or broad suites were run.

## MEDIUM — recovered peer attempts permanently poison the final verdict

`policy.py:106–107` appends a protocol violation for each unsuccessful completed attempt; `runner.py:180` unconditionally converts any such violation into PRODUCT_INCOMPLETE. A later successful, correctly identified resumed check cannot clear the earlier diagnostic. This contradicts the intended recovery policy confirmed by the owner during review and the guides' instruction to continue remaining solo checks honestly. Attempt outcome, final validation completion, and correct product outcome must remain distinct.

Prediction before reproduction: one fully evidenced failed process followed by a successful resumed peer, with complete accounting, will remain MATCH but retain a permanent protocol violation. Reproduction used the existing ApparatusTests fixture in disposable storage: create receipt/native evidence for turn 1, set its completion to EXITED/17, then create the successful resumed turn 2. Raw result:

```json
{"policy_status":"MATCH","protocol":["peer attempt did not finish successfully"],"usage":"COMPLETE"}
```

The runner's explicit condition then forces PRODUCT_INCOMPLETE even if source checks and delivery pass. Preserve every failed attempt and its usage, but distinguish a recovered attempt from unresolved required validation. Registration must explicitly define whether an unavailable peer followed by solo completion fails quality; do not infer that policy from an attempt-level error flag. Add a recovered-attempt classification regression.

## MEDIUM — deleting an allowed product file becomes apparatus STOP

`f23_precision.py:75–77` returns STOP with no rows when the selected product lacks bin/cli.js. This file is explicitly owner-editable in F23. An owner deleting it is an observable incorrect submission, not broken evaluation machinery. `runner.py:89–99` rejects that supplemental result and the run becomes STOP rather than PRODUCT_INCOMPLETE, removing a valid product failure from normal grading.

Prediction before reproduction: a disposable empty snapshot will yield STOP rather than two FAIL rows. Calling f23_precision.evaluate on that snapshot returned:

```json
{"schema":"0238-f23-precision-v1","rows":[],"status":"STOP","error":"snapshot has no bin/cli.js"}
```

Classify missing/deleted required product code as a valid FAIL and reserve STOP for missing evaluator/runtime machinery or unobservable execution. Add a deleted-product control through the supplemental runner boundary.

## Reviewed properties and limits

- The small automatic trigger is shared by S/H/P and does not expose oracle outcomes. S tests added owner effort; H tests independent context; P changes engine. Claude Read/Grep/Glob versus Codex read-only sandbox/native children remains an explicit capability confound, so a P gain cannot isolate model diversity alone.
- Helper receipts precede dispatch; native stdout is retained; terminal failures do not become helper success. Before/after source identity includes tracked/nonignored bytes, modes, symlink targets and HEAD. It cannot establish that no transient edit-and-revert occurred; the sole-writer/wait protocol remains necessary.
- Shared platform run_process supplies process-group timeout/interruption cleanup. The supplementary oracle executes under the inherited isolated evaluator container with verified container teardown. No new live timeout test was run in this review.
- Policy checks native identity and effort rather than requested argv, includes resumed turn contexts and configurations, and binds peer ancestry. Accounting uses the inherited inference/transcript inventory; the supplied tests cover Codex peer children/resume and partial evidence. Native authenticated smokes are still essential to verify actual CLI schemas, Claude per-turn effort/timestamps, resumed usage semantics, read-only child behavior and actual package installation paths. Synthetic evidence does not prove those live contracts.
- The F23 witness's two inputs exercise timestamp precision and equivalent-offset ties under the visible ISO-date/order contract. It leaves the two original oracle rows required and accepts either omitted or explicit exhausted inventory. Supplied full-check-v3 output records no-op FAIL and positive PASS with delivery/source binding. These controls are not evidence of pair efficacy.
- Reviewed package-preparation-integrity-v1.json: B also regenerates instruction-templates.json, removing one prior fingerprint key, in addition to the two delivery files. This is recorded, not a hidden two-file-only claim. The builder uses the same generator for all arms. The DRAFT still identifies itself as unregistered; exact order, admission rules, source/package/control freezes and native calibration remain prerequisites for measured comparison.

## Reviewed file identities

- `peer.py`: `d500dc6ca46c5ab1528c6d419530ad89094f36443461979c6aa1d27933fa3294`
- `policy.py`: `fb3887a2a897395fa07145f148bb11f4cb10ab535c10241ef8bda5fec5b8f2eb`
- `runner.py`: `c8d893bc2782d3b2f49d5bb203a471168a897ff80a5291cf0840d9093eba0a5e`
- `test_peer.py`: `c06be9e3fa81275b420f305de76aa686d22bc250d5c165aa0aa959aefff02a27`
- `test_runner.py`: `5172af563c0af195ad4348882a4f265b4b7edad274aabfb0a0bc3a6be280b0ae`
- `f23_precision.py`: `8face9ace542d944889bfff8802b352de0a3063d85ae0a8f9ccdbe4133f7f3e2`
- `DRAFT.md`: `b8e2a4e167ffbe7259113a6dd8d4e1564289c80ae40cd226bfa108a85e3c9e8a`
- `guides/S.md`: `34287e59aa0e32ba09dacb92115715466e1408de0f0620f92fb6ff2db1e9acc3`
- `guides/H.md`: `d21f5dc743e9bb9c1bb07cc4d6b143fbd5fd78521d1aa005427bf9fa8c579c13`
- `guides/P.md`: `e11bc49837dd434b8dbcf5deb099e50d53b29c5f609d7e7a9c72ebce31ce6da2`
- `tasks-draft.json`: `101f89014de44f385a232bf1f619dc1a0d9c6e6afb44f65ddd40d94e63fa7358`
- `build_packages.py`: `ace193402c46436c2b4c07e8c0dca34138f3adb0354748257c45d9ac04960b6b`
