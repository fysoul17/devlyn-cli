# 0133 — Worker model-reroute rejection

Status: SOURCE_IMPLEMENTED_AND_TESTED; actual Fable/Grok source advice pending.

The [spec](../../docs/specs/0133-worker-model-reroute/spec.md) binds a product failure found during source inspection after closed0132: a structured native model reroute can coexist with exit0, but the current worker completion checks only receipt bindings and labels the request effective. Root selects rejection of this observed native event and removal of request-as-observation claims, using existing artifacts. This makes explicit customer model selection and status truthful; no new allocator or measurement framework.

Falsifiable prediction and regression scope are recorded before code changes. Actual Fable/Grok advice is nonbinding; root decides.0132 stays CLOSED_INCOMPLETE_FIXED_CONFIG_DRIFT with its exact trust-stanza attribution, no retry/regrade;0120/0124/0125/0128 stay closed and A16 parked.3.0.0 remains unpublished.

One unchanged synthetic reproduction confirms the prediction: baseline2949b241 accepted the exact native-format reroute followed by success as PASS and labeled the request effective; after-fix7d5afe54 blocks with the line-specific reroute reason and null observations. Existing archive CLI check239619ad preserves failed raw prompt/session/receipt and terminal state byte-for-byte. Independent source reviewbb5d6e98 confirms the completion/archival separation and unchanged atomic transition failure behavior; its two in-progress notes corrected test fixture reuse and stale receipt wording.

Root's first focused test failed because the newly added synthetic cases reused an occupied receipt path; that original failure is retained in `.devlyn/0133-root-validation-r0/`. Only test setup was corrected. R1 existing receipt/state/roles/archive self-tests all pass (1.334/16.019/0.313/0.429s), and full lint passes208.206s. `.devlyn/0133-root-validation-r1/SOURCE-FREEZE.json` binds the six canonical files and checked normal mirrors. Native argv, worker calls and role defaults are unchanged. Actual Fable5.1/Grok4.6 advice is being prepared against this source; no native performance or positive worker-model attestation claim follows.
