# iter-0080 — engine-neutral pair-emission boundary (STUB, not registered)

**Status: STUB.** Not frozen, not built. Needs its own R0/R1 seat rounds before
any build. Opened because **FS-0079-A fired** in iter-0079.

## Why (pre-flight 0)

iter-0079 shipped the N-model pair wiring and proved grok is reachable,
isolated, probe-capable and fail-closed — but its emission dimension recorded
**VALID-NEGATIVE**. Two measured defect classes, both engine-behaviour, neither
patched inline (FS-0079-A's frozen disposition):

1. **INFO pseudo-finding on a clean PASS.** 2 of 3 clean-fixture runs emitted
   `{"id":"pair-judge-pass","severity":"INFO",…}` *alongside*
   `# SUMMARY {"verdict":"PASS"}`, violating P-0079-B's "empty findings list"
   criterion. Pipeline impact is nil — `verify-merge-findings.py:912-917`
   excludes INFO from the verdict-binding set — but the frozen criterion failed.
2. **Narration preamble welded to output line 1.** On runs where grok announced
   an action, it prepended e.g. `Running the mandatory dominance-loss probe…`
   with **no newline** before the first JSON object, so a strict parser rejects
   line 1. This is what falsified P-0079-F despite grok executing the mandatory
   probe correctly and finding the seeded CRITICAL defect. Reproduced in both
   the P-B pilot and the P-F run.

## Sequencing — knob sweep FIRST (binding)

**Arm order is not negotiable and exists because of a named prior mistake.** The
iter-0079 remedy sketch jumped straight to "prompt delta or collector rule",
which is structurally the same omission as that iter's retraction #4 ("zero-MCP
is unachievable" — asserted before searching the vendor's documented knobs, and
two documented knobs then closed it).

1. **Vendor output-format knob sweep.** Search the grok CLI's documented surface
   for an output-format / no-preamble / structured-output control before
   concluding any devlyn layer must change. A negative result here is a
   completed-search receipt, not an assumption.
2. **Only if (1) is empty**: A/B a prompt delta in `adapters/grok.md`, gated by
   `adapters/README.md:56-59` condition 3 (measured lift over the canonical body,
   not preference).
3. **Pre-committed fallback, frozen BEFORE the A/B result is seen**: a strict
   recovery rule at the collector boundary — engine-neutral, never grok-named.
   Pre-committing it is what stops step 3 from becoming a post-hoc relaxation.

## Correction inherited from iter-0079 (do not repeat)

For defect class 1 the failing instrument is the **frozen P-B criterion**, NOT
the collector — `collect-codex-findings.py` already exits 0 on INFO+PASS. A
follow-up drafted from 0079's original remedy sketch would patch code that is not
broken. Re-freezing the clean-route criterion against the verdict-binding set is
a legitimate option **as a fresh freeze here**; it would have been a retroactive
relaxation inside 0079.

## Required controls

- claude and codex default-route behaviour unchanged (unpinned
  `pair_judge_priority` still resolves the binary complement).
- Severity preservation: no fix may drop or rewrite a real finding's severity.
- Malformed / truncated / empty stdout must still fail closed to
  `verify.pair.emission-contract`.

## Related, deliberately NOT folded in

`verify-merge-findings.py:877-878`'s default-to-PASS — iter-0079's separately
named residual, where three failure paths converge on a false PASS. It is
engine-neutral pipeline-wide scope and carries its own registration. Do not
absorb it here without a decision.

## Gate for closing

grok emission-certified ⇒ the `not emission-certified` note comes out of
`engine-doctor.sh` and the certification line out of `adapters/grok.md`, and a
durable `pair grok` pin becomes available subject to the standing seat-fitness
rule.
