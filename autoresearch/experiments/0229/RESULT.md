# 0229 VERIFY re-screen — result

Registered in [0229](../../iterations/0229-verify-existing-behavior-rescreen.md), with Addenda D1–D2 and the gate results, which amend 0228 and 0227 by reference.

- **Driver:** [`screen.py`](screen.py) (D2).
- **Freeze:** the frozen [`manifest.json`](manifest.json) is the only commit of freeze PR #154 (`4e706485`), which was opened before the first seat started.
- **Scoring:** labels, checks and Astra's audit were committed and pushed on `candidate/0229-score` (`06614a12`) before the one-shot join.
- **Raw outputs** are in `/Users/Shared/devlyn-vr-0228-dev/screen-0229`, a C2-owned root whose judges ran as `_devlynjudge`. The scoring outputs are copied to [`evidence/`](evidence/).
- **Corpus:** [`corpus/`](corpus/) matches the manifest's 91 digests.

## Outcome: PASS

| # | condition | result |
|---|---|---|
| 1 | 32/32 target hits | **32/32**: both seats hit in 30 twin rounds, Claude alone in 1, Codex alone in 1 |
| 2 | 0 reference false alarms (including the unsupported terminal) | **0**: no reference round ended NEEDS_WORK |
| 3 | 0 unsupported extras | **0** |
| 4 | no invalid reference | **0**: every checked claim holds on the reference |
| 5 | every round non-BLOCKED; every seat completes, is authenticated and accepted; no retry | **holds**: 0 BLOCKED rounds, 128/128 seats accepted, 0 identified Claude re-asks |
| 6 | isolation, overlap, reads, witness | **holds** (details below) |

Condition 6 in detail:
- Sealed inventory unchanged (20,613 files).
- Overlap in 64/64 rounds.
- 0 excluded reads; 2 ambiguous reads, both allowed by root and Astra.
- No instruction attachments.
- Witness intact at start, end, score and join.

**Registered consequence:** bundle development is readmitted (22616b57 + F + G + H, steps 2–5). Nothing ships from 0229. The gates cannot show that H caused the change (registration limit).

## Run

- **Candidate:** H `3afbb18e` on G `607c3cf7` on F `f40da73b` on `22616b57`.
- **Repositories:** dateutil (P1–P4) and markdown-it (J1–J4), chosen by the selection rule ([`selection.json`](selection.json)).
- **Prepare** (inventory `f2`): 64 rounds.
  - The judge opened none of 212 hidden paths.
  - The 64 instruction probes, run as the judge, loaded no instruction file.
  - No MECHANICAL retry.
  - Owner baseline compare: changed 0.
- **First prepare:** it stopped at its first probe on a driver defect (D2's ACL re-grant) and was not frozen. The fix, a third stub dry run and Astra's SHIP preceded the second prepare.
- **Run** (`run --pr 154 --inventory f3`):
  - Before the first round, the judge opened none of 583 hidden paths.
  - 64 rounds ran in frozen order, 20:49:22–21:19:21Z, with no stop, no redispatch, and every round classified `none`.
  - Round wall: median 25.5 s (17.0–38.2 s).
- **Observed identities:** `claude-opus-5-5` (effort unobserved) and `gpt-6-astra` at `high`, in both orientations.
- **Usage:** Claude COMPLETE for all 64 Claude seats (80,164 output tokens). Codex PARTIAL (1,125,210 total tokens; output UNKNOWN).
- **Merged verdicts:** twin rounds 32 NEEDS_WORK; reference rounds 18 PASS_WITH_ISSUES and 14 PASS.
- **Isolation after the run:** owner baseline compare changed 0 (643 compared; the same five baseline paths gone, none removed by the experiment). The judge token appears in 0 of 103,155 files under the screen root, and no Codex login copy is left.

## Hits and the pool

- **Pool:** 115 findings of rank 1 or 2.
- **Final classification:**
  - 62 hit findings, all rank-2 behavioral target matches;
  - 3 twin-only extras: rank-2 behavioral non-matches whose claim fails only on the twin;
  - 26 coverage findings (neutral), 3 of them rank 2;
  - 24 rank-one extras;
  - no execution-condition finding.
- **Hit findings** by seat: Claude 31, Codex 31. By form: 31 HIGH with `verdict_binding: true`, 31 HIGH.
- **Per-seat target hits per task** (twin rounds): 4/4 for both engines on every task, except J1 Codex 3/4 and P3 Claude 3/4.
- **Checks:** 65 rank-2 behavioral claims, each run by `screen.py check` on freshly materialized base, reference and twin trees with one of 22 committed [check scripts](check-scripts/) ([logs](checks/)). All 65 hold on the reference and fail on the twin; the base fails too.

## Labels and audit

- **Root's labels** (`7e44ec4e`) came from masked inputs, before the audit and before any unmasking. They were drafted per task by Claude subagents and reviewed by root. J2, J3 and P3 were relabeled by short index after the first drafts returned mistyped or foreign finding keys, and root wrote one placeholder reason.
- **Astra, stage A** (blind), differed on 5 labels and on no read.
- **Exchange:** root adopted all 5 (`02ff1ac9`):
  - three rank-1 findings, coverage to behavioral;
  - P4 `2c0cde90`, coverage to behavioral, no match, checked;
  - P3 `604c4054`, match to no match: a cache-miss counterexample, not the recorded cache-hit trigger.
- **Final stage:** given each checked finding's own tree, Astra kept every label and reported no remaining dispute.
- Record: [`labels-audit.md`](labels-audit.md), [`audit.json`](audit.json), [`labels.json`](labels.json), [`reads.json`](reads.json).
- **Limits:** the read scan is heuristic, not a completeness proof for arbitrary shell or interpreter execution. Isolation rests on the judge account (0228 C2, 0229 D2) and on the hidden material staying inside the owner-only screen root until this result.

## Against the predictions (registered before H and any call)

- **Root:** gates ≈ 0.3; fresh screen given the gates ≈ 0.5; overall ≈ 0.15.
- **Astra:** all gates ≈ 0.26; screen given the gates 0.50; overall ≈ 0.13.
- **Outcome:** all three gates passed and the screen passed.
