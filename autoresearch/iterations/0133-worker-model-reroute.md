# 0133 — Worker model-reroute rejection

Status: REGISTERED_SOURCE_REPAIR; implementation and reproduction pending.

The [spec](../../docs/specs/0133-worker-model-reroute/spec.md) binds a product failure found during source inspection after closed0132: a structured native model reroute can coexist with exit0, but the current worker completion checks only receipt bindings and labels the request effective. Root selects rejection of this observed native event and removal of request-as-observation claims, using existing artifacts. This makes explicit customer model selection and status truthful; no new allocator or measurement framework.

Falsifiable prediction and regression scope are recorded before code changes. Actual Fable/Grok advice is nonbinding; root decides.0132 stays CLOSED_INCOMPLETE_FIXED_CONFIG_DRIFT with its exact trust-stanza attribution, no retry/regrade;0120/0124/0125/0128 stay closed and A16 parked.3.0.0 remains unpublished.
