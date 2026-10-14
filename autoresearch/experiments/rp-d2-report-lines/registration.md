# rp-d2 registration — report lines

This registration is written before any measured exposure. Its input
identities are in [registration.json](registration.json). That file's
`apparatus_commit` is the commit whose files the `inputs` hashes cover; this
registration commit follows it. From this commit on, the prediction, the
schedule, the grading and the raw data are never edited.

[DESIGN.md](DESIGN.md) is the contract. Its full text applies, including:

- the token gate;
- artifact identity;
- the adoption rule;
- the qualification record;
- Grok's recorded dissent.

## Prediction (frozen)

> On the same 4.2.18 tree, Y's paragraph raises Codex's success over X (BV/Z0,
> 2 repetitions each, paired and interleaved), and neither engine's quality or
> cost per success gets worse.

**Smoke evidence known at registration.** On SM, Codex Y read the new
paragraph in full, yet still reported only "PR #1 merged, and the local
checkout is clean. Nothing remains unresolved." This is one observation on an unrelated task. It lowers
expectations and leaves the prediction unchanged.

## What runs

- **Arms.**
  - X is the registry `devlyn-cli@4.2.18` tarball.
  - Y is the same archive with only the reporting paragraph of
    `task-completion.md` replaced.
  - Both are verified by SHA-256, SHA-512 and their extracted manifest.
  - Each attempt installs its own arm through the unchanged rp-d1 installer
    path.
- **Engines.**
  - Claude Code 2.1.296 runs `claude-opus-5-5` at effort `max`.
  - Codex 0.162.1 runs `gpt-6-sol` at effort `high`.
  - Native children use the owner's model.
- **Unchanged from rp-d1:**
  - the prompt [common.txt](../rp-d1-delivery-cost/common.txt);
  - the tasks and hidden oracle;
  - the image definition. The image itself was rebuilt, because the rp-d1
    image had been pruned. Its ID is in `registration.json`, and both arms
    use it.
- **Schedule.** Serial, with no replay:

  | Pair | Task / engine | Order | Slots |
  |---|---|---|---|
  | 1 | BV / Claude | X, Y | m01, m02 |
  | 2 | BV / Codex | Y, X | m03, m04 |
  | 3 | Z0 / Codex | X, Y | m05, m06 |
  | 4 | Z0 / Claude | Y, X | m07, m08 |
  | 5 | Z0 / Claude | X, Y | m09, m10 |
  | 6 | Z0 / Codex | Y, X | m11, m12 |
  | 7 | BV / Codex | X, Y | m13, m14 |
  | 8 | BV / Claude | Y, X | m15, m16 |

- **Repositories.** Each slot uses its own empty private repository,
  `fysoul17/rpd2-20261014a-<slot>`. The rp-d1 lifecycle applies:
  1. a precheck that the remaining repositories are still empty;
  2. archive, then verify the archive;
  3. delete the repository and confirm it returns 404;
  4. PAT scans.
- **Watchdogs.** 5400 s per owner and 600 s per evaluator or review. There is
  no token or cost budget.
- **Credentials.** The model auth snapshot may be renewed only between pairs,
  and only on the same Claude account pair and the same Codex account digest.
  Every launch keeps the 6300-second lifetime floor.

## Success, cost and decision

- **Success per request.** These are the four rp-d1 conditions, graded by the
  unchanged rp-d1 code:
  1. requirements and scope;
  2. exactly one correctly merged PR;
  3. preserved user files and sentinel;
  4. a truthful verification, merge, cleanup and checkout reconciliation
     report, with each claim supported by both Astra ultra and Grok 4.7
     reading the raw evidence.
- **Cost.** Every dispatched attempt counts, and every number comes from
  [summarize.py](summarize.py). For each arm and engine it reports:
  - successes and attempts;
  - total wall, input and output;
  - cost per success.
- **Decision.** `summarize.py` applies the DESIGN.md adoption rule
  mechanically and prints ADOPT, REJECT or INCONCLUSIVE with the reason for
  each row.
- **STOP rule.** An instrumentation STOP is recorded as `NOT_ASSESSED`. That
  includes UNKNOWN usage, as in rp-d1. The remaining slots become `NOT_RUN`,
  and the run is inconclusive. No attempt is ever retried or replaced.

## Qualification

**Smoke attempt 1 stopped** on Claude X. Its delivery was correct, but its
usage was UNKNOWN after a dropped-connection retry
(`api_error`/`api_retry`; the transcript names ECONNRESET). The other three cells did not run.

**Smoke attempt 2**, the registered spares, qualified all four cells.

| Cell | Owner s | Input | Output | Usage | Done-check | Repository |
|---|---:|---:|---:|---|---|---|
| Claude X | 639.0 | 1,376,277 | 60,605 | COMPLETE | ADJUDICATE | archived, deleted (404) |
| Claude Y | 613.9 | 2,195,861 | 58,835 | COMPLETE | ADJUDICATE | archived, deleted (404) |
| Codex X | 165.2 | 353,955 | 5,607 | COMPLETE | ADJUDICATE | archived, deleted (404) |
| Codex Y | 173.2 | 470,647 | 5,878 | COMPLETE | ADJUDICATE | archived, deleted (404) |

The verdict hashes and both schedule hashes are in
[registration.json](registration.json). Smoke reports are not graded and are
never pooled with measured data.

## Freeze revision before exposure

The first registration review returned SHIP from Grok and REVISE from Astra,
which raised one MEDIUM ([Astra](results/registration-r1-review-astra.md),
[Grok](results/registration-r1-review-grok.md)): `summarize.py` let REJECT win
over a STOP. It now returns INCONCLUSIVE whenever a row is UNKNOWN, matching
the STOP rule above. Grok's three wording LOWs are corrected.

Before any measured slot ran, the snapshot crossed the 6300-second floor.
Meanwhile the host's Claude login had switched accounts, so the staged
credential could not be renewed on the same account. rp-d1 handled the same
event the same way:

- **Void runtime.** The first measured runtime, which never ran, is kept as
  `runtime-measured-void-account-switch.json`. Its hash is recorded in
  `void_runtime_sha256`.
- **Re-staged account.** The measured run was re-staged on the current Claude
  account pair. The Codex account is unchanged.
- **Recorded smoke accounts.** The smoke qualification accounts are recorded
  as `smoke_account` and `smoke_codex_account`. The apparatus checks the smoke
  verdicts against those recorded accounts.
- **Measured account freeze.** All 16 measured slots must use the one
  registered account pair and the one Codex account. Renewal is allowed only
  between pairs, only on the identical accounts.

[registration.json](registration.json) was regenerated for this commit.

## Review

1. **Before exposure.** Astra ultra and Grok 4.7 review this registration.
2. **After the run.** Both judge every report checklist and the results
   against the raw evidence.
3. **Stopping.** Review stops at SHIP with no HIGH finding, reading each
   reviewer's final verdict line.
4. **Write-up.** If Y is not adopted, the write-up reverts the paragraph
   before merge. The prompt ablation recorded in DESIGN.md is then the next
   candidate.
