# Reject a worker's reported model reroute

## Problem and scope

An explicit model selection must not be reported as honored after native evidence says it changed. Current `invocation-receipt.py` validates the requested argv and raw-byte bindings, but does not inspect the retained JSONL. `state-phase-write.py:1921` then copies `model_requested` to `model_effective`; `role-config.py:214` presents that receipt as an observation.

The retained Codex0.153.4 source at `.devlyn/0118-resume-check-20260906T0749/usage-semantics/event_processor_with_jsonl_output.rs:487-500` emits model rerouting as an `item.completed` event with an error item and `model rerouted: ...` message, then continues running. Its lines599-606 emit a thread ID, not a model configuration header, in JSON mode. This is a source-backed reachable contract failure, not an allegation that0132 used the wrong model.

Root owns this separate prospective product correction. Closed0132 and other frozen experiments remain unchanged. No allocation/default change, global-session scanner, new runtime artifact/schema/flag, or benchmark restart. Customer AGENTS.md/CLAUDE.md remain untouched.

## Required behavior

1. Successful phase admission must reject an actual structured native model-reroute event in its existing canonical, receipt-bound worker JSONL, even when the child exits0 or later emits success. Apply at the semantic completion check, preserving structural artifact validation so failed evidence can still be archived.
2. Match the native event boundary, not arbitrary assistant prose, tool output, quoted JSON or ordinary recoverable errors. Malformed JSONL cannot establish absence of the prohibited event. Preserve original raw streams, native exit and receipt; show a specific actionable BLOCKED reason, with no weaker retry or silent substitute.
3. An argv-only receipt proves requested dispatch, not observed effective model. Stop populating effective-model observations from that request. Keep existing requested identity, receipt validation, role argv, phase lifecycle and real Claude/judge observations. Historical states stay readable, but their argv-only worker entries must not be presented as independently observed identities.
4. Preserve existing model/effort resolution, native arguments, timeout/cleanup, sandbox/network, prompt/run/phase/round bindings and report/archive behavior. This change does not add positive provider-identity attestation; unknown stays unknown.

## Prediction and verification, before implementation

Prediction: a synthetic canonical receipt containing the exact native reroute event followed by successful completion is currently accepted and reports the requested model as effective. The corrected source rejects that same completion, while an ordinary successful stream remains accepted with effective model unknown. A phrase appearing only in an assistant/tool item or an unrelated native error does not trigger this rejection.

Retain one before/after reproduction using existing receipt/state functions in a temporary owned repository. Add focused regressions for actual event, later success, text lookalikes, malformed JSONL, unchanged requested/observed handling and archival preservation of rejected raw evidence. Run the affected existing self-tests and required full `bash scripts/lint-skills.sh`; verify normal mirrors. Seek independent source review and one actual Fable5.1/Grok4.6 read-only advisory each of the resulting source, with root adjudication. No native reroute induction, extra worker run, or performance ranking is required for this deterministic contract repair.

Subtractive-first: delete request-as-observation assignments and the status trust shortcut; add only the check for the demonstrated native event to existing receipt validation. Principles: No workaround, No guesswork, No overengineering, Production ready. Acceptance is scoped to reliable failure/status behavior, not model quality, speed, automatic fitness or3.0.0 publication.
