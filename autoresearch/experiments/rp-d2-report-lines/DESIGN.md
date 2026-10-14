# rp-d2 design — report lines

rp-d1 ([results](../rp-d1-delivery-cost/results.md)) refuted its prediction on
report coverage alone: Codex merged a correct PR and cleaned up in 4/4 attempts,
but each final report said only "the local checkout is clean". Both reviewers
found cleanup MISSING and checkout reconciliation AMBIGUOUS. rp-d2 tests one
instruction-only change aimed at that gap. Design reviews:
[Astra](results/design-r0-astra.md) (SHIP) and
[Grok](results/design-r0-grok.md) (REVISE; every finding is resolved below).

## Mechanism

Only the reporting paragraph of
[task-completion.md](../../../config/skills/_shared/task-completion.md) changes,
in place. The paragraph is at line 203, the end of "Deliver and resume".

Control X (`7516ebc9`):

```text
Report verification, delivery and checkout reconciliation separately. A delivery
error does not rewrite an accepted product result; unperformed verification
must never be reported as accepted.
```

Candidate Y:

```text
Report verification, delivery, cleanup and checkout reconciliation separately. A
delivery error never changes an accepted product result; never report unperformed
verification as accepted.
```

- "cleanup" becomes a named report category.
- "checkout" stays. It separates the owner's reconciliation of the original
  checkout from the helper's `reconciled` allocation field
  (`task-completion.md:82`).
- "product result" stays. It is the term `devlyn-ideate` reports with.

**Token gate (tokens never increase).** The gate counts the whole file, before
and after, with [token_gate.py](token_gate.py). Claude uses Anthropic's
`count_tokens` for `claude-opus-5-5`. Codex uses `o200k_base` as a proxy,
because the `gpt-6-sol` tokenizer is not published.

| Wording | Claude | o200k |
|---|---:|---:|
| X (control) | 4,873 | 2,982 |
| Y (candidate) | 4,872 | 2,981 |
| Astra's draft ("Delivery errors do not rewrite …") | 4,875 | 2,979 |

The gate rejected two drafts. Astra's draft adds 2 Claude tokens. Grok's "as
four claims" adds 1 to 4 tokens on the paragraph in every arrangement tried.
`AGENTS.md`, `CLAUDE.md` and the prompt [common.txt](../rp-d1-delivery-cost/common.txt) are unchanged.

## Arms and artifacts

- **Control X** is the published `devlyn-cli@4.2.18` registry tarball, the
  artifact rp-d1 measured (SHA-256 `7b22cce8…393e`, registry integrity
  verified). Its `task-completion.md` must equal the `7516ebc9` blob.
- **Candidate Y** is X with that one file replaced by the candidate commit's
  blob, then repacked. Nothing is regenerated. A source pack would add a
  skill-history fingerprint and other publish-time differences.
- **Identity.** Both arms keep version `4.2.18`, so the version alone does not
  identify them. Each arm's identity is its tarball SHA-256 and SHA-512 plus
  its extracted file manifest.
- **Pre-registration check.** The two extracted trees must differ in exactly
  one file, `config/skills/_shared/task-completion.md`, and that file's diff
  must be exactly this paragraph.
- **The apparatus descends from rp-d1, with three changes:**
  1. two release records, each verified;
  2. a per-attempt arm, X or Y, that selects which package is installed;
  3. summaries grouped by arm and engine.

  Everything else is the rp-d1 apparatus as merged, including the corrected
  Git-mode evaluator, strict archive validation and the PAT scans. Both arms
  run on it.

## Schedule

There are 16 measured attempts: 2 arms × 2 engines × 2 tasks (BV, Z0) × 2
repetitions. They run serially, with no replay.

- **Pairs.** The rp-d1 order of task and engine becomes eight pairs:
  `BV/Claude, BV/Codex, Z0/Codex, Z0/Claude, Z0/Claude, Z0/Codex, BV/Codex, BV/Claude`.
  Odd pairs run X then Y; even pairs run Y then X.
- **Engines.**
  - Claude Code 2.1.296 runs `claude-opus-5-5` at effort `max`.
  - Codex 0.162.1 runs `gpt-6-sol` at effort `high`.
- **Frozen across arms:** the prompt, tasks, oracle, image, model cache,
  accounting and accounts.
- **Credentials.** They may be renewed, on the same account, only between
  pairs. An account change between arms invalidates the run.
- **Watchdogs.** These are the rp-d1 watchdogs. There is no token or cost
  budget.
- **Repositories.** There are 24 private repositories,
  `fysoul17/rpd2-<run>-<slot>`: 16 measured, 4 for smoke cells and 4 spare
  smoke cells. The owner makes one fine-grained PAT edit that selects all 24,
  with the rp-d1 permissions.
- **Smoke.** Each pairing of engine and arm runs one fresh smoke on SM. The
  spares allow one complete repeat. Measured attempts are never replaced.
- **Repository handling.** It follows rp-d1: check that the repository is
  empty, archive it, verify the archive, delete the repository, then confirm
  it returns 404. Raw evidence is kept until final adjudication.
- **UNKNOWN usage STOPs, as in rp-d1.** One proposed rule would have
  continued after an accounting-only UNKNOWN. It was implemented, reviewed
  (REVISE, both: [Astra](results/cont-r1-review-astra.md),
  [Grok](results/cont-r1-review-grok.md)), corrected, then withdrawn before
  exposure, for two reasons:
  - **The rule would not have applied to the real case.** The ECONNRESET cell
    from smoke attempt 1 has its retry rows filtered out, but it still fails
    the unchanged 0254 audit, on two unindexed request bodies
    ([eligibility](results/cont-fix-real-eligibility.json)).
  - **A compared UNKNOWN cost row blocks adoption either way.** Continuing
    would add descriptive data only. It could not change the decision.

  The rp-d1 STOP rule is therefore kept, with no added code. A STOP makes the
  run inconclusive.

## Success and cost

Success per request is the rp-d1 registration's four conditions, unchanged:

1. scope and regression checks;
2. exactly one correctly merged PR;
3. preserved user files and sentinel;
4. a truthful verification, merge, cleanup and reconciliation report, with
   each claim supported by both reviewers.

A truthful `CLEANUP_PENDING` remains allowed. A missing or ambiguous claim
fails.

Every dispatched attempt counts, failures included. The cost metrics are owner
wall seconds, input tokens and output tokens, each divided by the number of
successes. Accounting is the rp-d1 accounting.

## Prediction

> On the same 4.2.18 tree, Y's paragraph raises Codex's success over X (BV/Z0,
> 2 repetitions each, paired and interleaved), and neither engine's quality or
> cost per success gets worse.

## Adoption rule

Adopt Y only if, for each engine, both of the following hold, and at least one
engine improves:

- **Quality.** Y's successes are at least X's.
- **Cost.** Y's wall, input and output per success are each no higher than
  X's. Cost is compared only when both arms of that engine have at least one
  success.

Two edge cases:

- **One arm has zero successes.** With 0 X successes and at least one Y
  success, the engine counts as a quality improvement, and its cost row is
  recorded as "no baseline", neither worse nor infinite. With 0 successes on
  both arms, the engine is unchanged. With 0 Y successes and at least one X
  success, the engine got worse.
- **UNKNOWN usage on a compared cost row.** Adoption is blocked.

Two repetitions support this task and model setting only. Extra artifact
differences, unequal repairs, a mid-pair account or model change, selective
retries, changed grading, missing usage or damaged evidence all void
attribution.

## Qualification and the pre-registration decision

All four repositories were archived, then deleted and confirmed 404.

- **Smoke attempt 1** stopped on its first cell, Claude X. The owner delivered
  correctly, but a dropped connection (`system/api_error`, ECONNRESET) was
  retried. The 0254 accounting therefore returns UNKNOWN, by design.
- **Smoke attempt 2**, the spares, qualified all four cells. Every cell
  delivered, its usage was COMPLETE, and its report checklist was set to
  ADJUDICATE.
  - **Codex, both arms.** The report ended in the rp-d1 shape: "PR #1 merged,
    and the local checkout is clean. Nothing remains unresolved."
  - **Codex Y read the new paragraph.** It ran `cat` on
    `task-completion.md`, and the output was not truncated.
  - **Claude, both arms.** The report named the merge, the fast-forward, the
    clean tree and the removal of the worktree, branch and scratch.

**Decision before registration.** The smoke evidence was put to Astra and Grok
([Astra](results/smoke-decision-astra.md), [Grok](results/smoke-decision-grok.md)).

- **Both reviewers.** Both proposed an accounting-only UNKNOWN continuation.
  It was later withdrawn; see Schedule.
- **Astra.** Register Y unchanged. One SM observation cannot establish no
  effect on BV/Z0.
- **Grok, dissenting.** The prompt's closing sentence ("Finish with what you
  changed, what you verified and anything unresolved") sets Codex's report
  shape. Grok would replace the arms with a prompt ablation.

**Resolution.** Y is measured as designed, because the owner chose a product
instruction fix. The prompt ablation is the registered next candidate if Y is
not adopted.

Interpretation is narrowed accordingly. rp-d2 measures whether Y improves
report coverage under this frozen prompt. A null result does not show that
the product's reporting rule is wrong in general. Delivery outcomes and report
outcomes are shown separately.

## Review

1. **Registration.** Astra ultra and Grok 4.7 approve it before exposure.
2. **Results.** After the run, both review the results against the raw
   evidence.
3. **Write-up.** If Y is not adopted, the write-up reverts the paragraph before
   merge.
