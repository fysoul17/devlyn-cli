# 0203 — Verify the owner repair boundary before intent integration

2026-09-22 KST. Continue [0201](0201-harness-transformation-plan.md), root direct,
with actual Fable 5.1 and Grok 4.6 review; no resolve invocation. Main already
contains [0202](0202-owner-run-candidate.md) and the 3.2.0 release (`49f57e0`).
The product direction remains one intent entry combining requirement alignment,
execution and necessary review/repair. This is a prerequisite correction, not
completion of that integration or another open-ended research frontier.

## Reproduced and repaired

- Owner CLEANUP accepted staged changes when the worktree matched HEAD. Both
  independent reviewers identified the same gap; root reproduced exit 0 into
  VERIFY with `MM source.txt`. Check the index as well as worktree and HEAD.
- Cleanup-origin IMPLEMENT could skip BUILD and the durability receipt. Both
  reviewers identified it; root reproduced the accepted direct VERIFY handoff.
  Require the next configured gate and the same repair round. Explicit existing
  build/cleanup bypasses remain supported and still require the receipt.
- The new owner repair edge also admitted historical worker CLEANUP. Grok
  identified the expanded edge; the corrected baseline control reproduced exit 0
  with an explicit Claude next worker. Preserve the historical VERIFY edge and
  restrict the repair edge to owner FAIL with its cleanup trigger.

Fable's follow-up found our first receipt-check widening could reject the later
CLEANUP→VERIFY handoff after the cleanup findings changed. Root reproduced the
stale-receipt error and restricted cleanup-origin re-entry checking to the repair
return. The extended CLI control now covers the complete repair→BUILD→CLEANUP→
VERIFY chain. Fixture BUILD evidence is deliberately empty: this exercises the
lifecycle, not actual task/model execution.

Evidence is retained in `.devlyn/0203/`: pre-change predictions, original failed
controls, raw independent review streams, per-round source hashes, root
dispositions and final checks. Initial controls with missing worker identity or
missing fixture BUILD evidence are preserved; they do not establish the intended
counterexamples. Corrected controls carry separate filenames.

Final actual Fable/Grok reviews both return scoped PASS with no binding findings.
The ten CLI regressions pass, including the complete handoff and four bypass
combinations. Grok still exposes tool declarations despite no-tool options; no
assistant tool calls were observed. This is independent source advice, not a
certified clean-context experiment. Final full-suite status is in `FINAL.md`.

## Remaining 0201 work

Step 1 is still open for an actual candidate trace. Metadata-bearing historical
worker APIs remain callable; the lifecycle helper is not a complete scheduler.
Caller-supplied source checkpoints, standalone phase misuse, old VERIFY-origin
scope checks and path-only untracked protection are not universal guarantees.
The next internal intent candidate must demonstrate selected execution, in-owner
planning/cleanup, and review→repair→affected checks→fresh review without separate
PLAN/BUILD/CLEANUP model calls. Keep original constraints and final source/evidence
agreement explicit. Source tests alone cannot close this admission.

Then follow 0201's finite A/B/C registration and decision, with concrete tasks and
whole-run time/usage budgets before draws. Public intent installation, option
migration and retirement of old entrypoints belong to the product transition;
there is no rename, npm release, comparative gain or Mission1/gate15 claim here.
