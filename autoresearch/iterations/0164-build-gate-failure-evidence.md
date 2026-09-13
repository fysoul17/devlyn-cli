# 0164 — BUILD_GATE preflight failure handoff

2026-09-13. User selected default BUILD_GATE failure-evidence inspection and
improvement, with Opus5 permitted when Fable5.1 reaches its limit. Root implements
directly, without resolve; native reviewers remain read-only advisers.
**Root source verdict: PASS. Delivery is tracked separately by the receipt below.**

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
Malformed evidence prevents finalization and is reported explicitly. Retained prior
observations must validate even on ordinary null-carrier completions; unreadable
prior files report `BLOCKED:process-evidence-invalid` without changing state. Normal
success, interrupted observations, VERIFY and validation-only behavior remain.
The marker is local result metadata, not authentication against an actor able to
rewrite both results and findings.

## Verification

- Checker and state-writer self-tests pass, including the unchanged0119
  interrupted-observation checks. New real checker-to-state CLI controls cover
  fresh rejection, prior language evidence, prior-round results and capability
  denial;32 identity/digest/finding mutations and three prior-state/stream controls
  reject without changing state.
- Sixteen additional actual CLI controls pass: source/digest/inline/sibling/
  probe/prestaged failures, healthy execution, validation-only/VERIFY preservation,
  and dangling/corrupt manifests or raw streams. Earlier observations stay intact.
- Removing the preflight finalizer reproduces the original refused FAIL. Removing
  the explicit verdict guard admits an incorrect PASS. These deletions are not
  safe reductions. AST scope checks limit Python changes to main/binding and
  their self-tests; canonical and both installed mirrors match.
- `bash scripts/lint-skills.sh` passes; final run metadata is in
  `.devlyn/0164/lint-opus-fix.json` (earlier runs314.173s/319.097s retained).
  Final source hashes match the review packet; `git diff --check` passes.
- Opus's unreadable-prior-file case was reproduced through the actual CLI, then
  corrected and verified: explicit BLOCKED, no traceback, identical state bytes.
  A portable injected-read-error self-test and ordinary null-carrier valid/invalid
  prior controls pass. Initial open-span fixture setup failure remains recorded.

Initial harness failures remain in evidence: the first reproduction read the
wrong findings filename; two old self-test assertions equated any results file
with command execution. Updated checks distinguish rejection results from command
observations. The first external risk-format fixture repeated the digest-error
path; the corrected fixture calls the actual digest function and asserts the
intended malformed-probe diagnostic. Initial artifacts were retained separately.

## Review and delivery

Fable's initial log-design advice was usable; its subsequent failure-design reply
contained simulated tool markup and is excluded. Actual observed tool calls were
zero. Later Fable5.1 and the authorized Opus5 fallback both returned the account
session-limit response, resetting at13:50 KST. Neither is a completed source review.
Grok's full-source packet timed out at605.057s without a final answer. The
compact retry returned PASS_WITH_ISSUES in326.610s and exposed a null-carrier
return bypassing prior-state integrity checks. Root removed that early return,
added malformed-prior and tampered-prior-stream CLI controls, and reran the state
self-test successfully. Actual Grok delta review PASS143.842s, no HIGH/CRITICAL, zero observed tool
calls. On the user's explicit Opus-available continuation, actual Opus5 final
source review returned PASS_WITH_ISSUES58.035s, no HIGH/CRITICAL. Root accepted
prior validation on ordinary null-carrier completions as intentional; fixed the
reproduced prior-file error classification and named the original findings source
and aggregate destination in guidance. The output override remains supported;
pinning a fixed findings filename would break it.

Actual final delta reviews: Opus5 PASS31.525s and Grok4.6 PASS114.889s, zero observed
tool calls. These are read-only advice; root adjudicated every finding. Opus CLI
also reported15 Haiku output tokens of ancillary usage, separate from the Opus
review answer. Inherited pending-Claude wording in the earlier packet/answer is
stale, not an outstanding review. Root accepts the bounded source change after
local checks; no full native pipeline or performance claim follows from it.

Retained checkout: `/Users/aipalm/.local/share/nx01/core-continuation-20260912`.
Task branch: `codex/0164-build-gate-failure-evidence`; prospective completion receipt
`a8443958e66b4d00ba0ef847`. Final evidence is `.devlyn/0164-evidence.tar.gz`;
`.devlyn/0164-delivery/final-source-audit.json` and the external receipt report
actual hosted CI, merge and cleanup once observed. The earlier checkpoint archive
remains immutable and is not source acceptance. Preserve all raw failures. No
frozen study replay, customer-file modification or npm release.

**Principles1–6:** minimum producer/consumer repair for two observed constraints;
no process wrapper or environment dump; explicit failure and evidence
corruption handling; native advice and checks remain separate from shipment.
Worldclass/Production-ready acceptance includes actual native reviews, root
adjudication and explicit failure-path checks; delivery remains a separate fact.
