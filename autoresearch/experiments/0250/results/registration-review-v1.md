# 0250 independent registration review

2026-10-11. **FREEZE — zero HIGH findings.** The concrete registration and
schedule implement the reviewed prospective B/S-only design. This is design
acceptance, not a completed binding audit or permission to dispatch before the
registered freeze/audit gates pass.

## Reviewed identities

| Input | SHA-256 |
| --- | --- |
| `registration.md` | `36210a0c61f1ba1e3b3786bb33d1a80613379c184665e9e980b49b7a4a8af2be` |
| `schedule.json` | `23f37730d52523bc678d3b8177ae8869e64bd4e58575daf9534ff38e67cf636e` |
| `results/auth-observation-v1.json` | `6ab82e59403b0333faef52a04cc9840d6b22b8a0fa75d6ae7ec321b38ccf3cf0` |
| `/Users/aipalm/.local/share/nx01/0250-live/runtime.json` | `d1010d43266b035c6e3bedb31c8b5aaaaba9d785d2423764021ee287a7dc3025` |

The runtime was hashed without exposing its contents. The retained read-only
profile observation reports PASS, identities `cc43a4e02ede`/`2905f4abf05b`,
25326 seconds remaining, and unchanged host authentication during that probe.
This report does not independently repeat authentication or predict continued
availability; each owner still requires the registered current preflight.

## Design rationale and concrete verification

The unresolved question is whether the unchanged S candidate earns admission
over B on both engines. The exposed Claude signal licenses that narrow question;
0249 never observed S. Renewed owner authorization permits a new prospective
study while both prior studies remain closed. Their observations and unknown
costs cannot become fresh draws, successful retries or zero-cost evidence.

OR2 runs first because it has no prior native observations. OR1 is explicitly a
partially exposed replication, not an untouched holdout. Removing the four
descriptive A draws is prospective and leaves every S/B admission contrast
intact. Those draws could not decide this gate or establish bare superiority.
This follows **No overengineering**, **Optimized** and **No guesswork**.

A read-only structural comparison against `0249/schedule-v1.json` removed only
A cells and compared each remaining cell's task, engine, arm, repetition and
role. Raw comparison results:

| Block | Cells | Exact inherited relative order | Entry condition |
| --- | ---: | --- | --- |
| OR2 | 8 | true | REGISTRATION_FREEZE_AUDIT_PASS |
| OR1 | 8 | true | BOTH_ENGINES_OR2_PASS |
| CONTROLS | 8 | true | BOTH_ENGINES_OR2_AND_OR1_PASS |

Thus the 8/16/24 conditional schedule retains two B/two S hard-task draws per
engine, the inherited counterbalance and all eight controls. No old cell is
reused. The gates retain separate engine/task correctness and whole-resource
nonregression, a strict hard-task gain, costs of failed/recovered/child work,
and nonadvancing zero-denominator rules. Controls retain per-task correctness
and per-engine aggregate E1/B5 resource nonregression. No pooling, tolerance,
extra draw or hard-task offset can rescue a failed gate.

The registration also preserves exact S bytes, historical package provenance,
unchanged calibrated executable inputs, current-account prospective pinning,
fresh run state, the authentication margin, fixed routes/catalogs/watchdogs and
serial native execution. The separate installer import fix is expressly outside
both frozen arms. Any final delivery must verify its actual candidate and report
that separation; it cannot retroactively change B.

Accounting, identity, binding and machinery faults require immediate STOP;
valid product failures remain results. Complete blocks get one efficacy gate
after independent integrity/usage audit. No grading follows an accounting or
identity STOP. No favorable retry, automatic apparatus repair, successor study,
S rewrite or pair escalation is authorized. Substantive repair needed merely to
reuse the instrument stops preparation. These boundaries implement **No
workaround** and **Production ready** and prevent another apparatus spiral.

## Remaining pre-dispatch boundary

Root's 621-input verification is reported context, not independently certified
by this review. Package/control equivalence bindings were still being assembled
when requested. The final independent binding audit must verify unchanged
calibration/executable inputs, actual merged-B equivalence, exact S bytes,
controls, runtime and this reviewed registration/schedule against the immutable
freeze. No native dispatch is justified until that audit passes. No new smoke,
calibration campaign or debate round is indicated by these unchanged inputs.

A pass supports only the exact S delta on this small panel, with OR1 exposure
qualified. A nonadvancing result closes this study; a STOP is not an S product
failure. Neither outcome proves a global solo ceiling or superiority to bare.

Only this review report was written. No native owner, authentication operation
or test was launched by the reviewer.
