# 0164 — BUILD_GATE preflight failure handoff

2026-09-13. User selected default BUILD_GATE failure-evidence inspection and
improvement, with Opus5 permitted when Fable5.1 reaches its limit. Root implements
directly, without resolve; native reviewers remain read-only advisers.
**Local checks pass; source acceptance and delivery remain pending review.**

## Failure and minimum repair

**Pre-flight0 / Mission1:** a completed checker rejection must reach the parent
with its original failure evidence. The existing checker exits1 with CRITICAL
`correctness.spec-verify-malformed` when generated criteria are missing, but emits
no current `spec-verify.results.json`. The state writer consequently rejects
`complete --verdict FAIL` as missing results. A previous-round results carrier
instead fails current-round identity. Prediction preceded the actual checker and
binder reproduction in `.devlyn/0164/baseline-handoff.json`; these are component
observations, not a full native resolve or false-PASS demonstration.

The initial invocation-log proposal was rejected: the historical0159 default
worker already recorded interpreter, work root and environment construction.
0163's augmented fixture alone did not prove a default log omission.

Named design delta:0119's `test_interrupted_build_gate` deliberately rejects
FAIL when a checker was interrupted without producing results; it permits only
BLOCKED with preserved partial observations. Broadening that consumer path would
remove a learned distinction. Keep it unchanged. Instead, completed BUILD_GATE
preflight rejections now finalize the existing results file with
`preflight_failure` (run/phase/round and the original finding's path/digest).
Earlier validated current-round language-gate observations are summarized using
the existing runner; no process invocation or successful command is invented.

The binder validates identity and the hashed CRITICAL finding before its
null-carrier path and permits only FAIL/BLOCKED. Only this explicit rejection can
waive absent executable obligations. Existing manifest, summary and raw-stream
validation still applies; capability denial still requires BLOCKED. Dangling
manifest paths count as present evidence and cannot use the null-carrier path.
Malformed evidence prevents finalization and is reported explicitly. Normal
success, interrupted observations, VERIFY and validation-only behavior remain.
The marker is local result metadata, not authentication against an actor able to
rewrite both results and findings.

## Verification

- Checker and state-writer self-tests pass, including the unchanged0119
  interrupted-observation checks. New real checker-to-state CLI controls cover
  fresh rejection, prior language evidence, prior-round results and capability
  denial;32 identity/digest/finding mutations reject without changing state.
- Sixteen additional actual CLI controls pass: source/digest/inline/sibling/
  probe/prestaged failures, healthy execution, validation-only/VERIFY preservation,
  and dangling/corrupt manifests or raw streams. Earlier observations stay intact.
- Removing the preflight finalizer reproduces the original refused FAIL. Removing
  the explicit verdict guard admits an incorrect PASS. These deletions are not
  safe reductions. AST scope checks limit Python changes to main/binding and
  their self-tests; canonical and both installed mirrors match.
- Full `bash scripts/lint-skills.sh`: PASS,319.097s. Final source hashes match the
  review packet; `git diff --check` passes. No hosted CI or delivery is claimed.

Initial harness failures remain in evidence: the first reproduction read the
wrong findings filename; two old self-test assertions equated any results file
with command execution. Updated checks distinguish rejection results from command
observations. The first external risk-format fixture repeated the digest-error
path; the corrected fixture calls the actual digest function and asserts the
intended malformed-probe diagnostic. Initial artifacts were retained separately.

## Review and continuation

Fable's initial log-design advice was usable; its subsequent failure-design reply
contained simulated tool markup and is excluded. Actual observed tool calls were
zero. Later Fable5.1 and the authorized Opus5 fallback both returned the account
session-limit response, resetting at13:50 KST. Neither is a completed source review.
Grok's final source review is pending; its earlier design advice and root's named
0119 correction remain in `.devlyn/0164/`. No accepted source or merge is claimed.

Retained checkout: `/Users/aipalm/.local/share/nx01/core-continuation-20260912`.
Task branch: `codex/0164-build-gate-failure-evidence`; prospective completion receipt
`a8443958e66b4d00ba0ef847`. Resume exact final-source review from
`.devlyn/0164/final/review.prompt.txt`, adjudicate actual findings, then accept and
deliver through the receipt. Preserve all raw failures. No frozen study replay,
customer-file modification, model-performance claim or npm release.

**Principles1–6:** minimum producer/consumer repair for two observed constraints;
no process wrapper or environment dump; explicit failure and evidence
corruption handling; native advice and checks remain separate from shipment.
Worldclass/Production-ready acceptance is pending the outstanding review, not
inferred from green local tests.
