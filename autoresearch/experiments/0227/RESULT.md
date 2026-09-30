# 0227 VERIFY re-screen — result

Registered in [0227](../../iterations/0227-verify-rescreen.md) (addenda B1–B3). Driver [`screen.py`](screen.py); frozen [`manifest.json`](manifest.json) is the only commit of freeze PR #138 (`8ffa61e2`, created 2026-09-30T06:36:08Z, before the first seat started at 06:36:31Z). Labels, checks and Astra's audit were committed and pushed on `candidate/0227-score` (`7874c06c`) before the one-shot join. Raw outputs: `/Users/Shared/devlyn-vr-0227` (sealed root); copies of the scoring outputs are in [`evidence/`](evidence/); the corpus is in [`corpus/`](corpus/) and matches the manifest's 88 digests.

## Outcome: NOT PASS (condition 2 only)

| # | condition | result |
|---|---|---|
| 1 | 32/32 target hits | **32/32** — both seats hit in 28 twin rounds, the Claude seat alone in 4 |
| 2 | 0 reference false alarms (incl. unsupported terminal) | **violated: 1** — J4 reference, codex orientation, rep 1 |
| 3 | 0 unsupported extras | **0** |
| 4 | no invalid reference | **0** — every checked claim holds on the reference |
| 5 | every round non-BLOCKED; every seat completes, is authenticated and accepted; no retry | **holds** — 0 BLOCKED rounds, 128/128 seats accepted, 0 identified Claude re-asks |
| 6 | seals, overlap, reads, witness | holds — sealed inventory unchanged, overlap in 64/64, 0 excluded reads, no instruction attachments, witness intact at start/end/score/join |

Registered consequence: steps 2–5 stay held. No automatic fix-and-rescreen: another registration needs a materially new diagnosis and the user's decision. Nothing ships from 0227.

## Run

- Candidate `22616b57` + F `f40da73b` (structured Claude output via `--json-schema`; BLOCKED only when essential evidence is unavailable and no authorized change could produce it).
- The first `prepare` was not frozen (B3: one MECHANICAL attempt crashed in V8's code-cache deserializer, which counts as a calibration break under B2); the driver then disabled tap's V8 code cache. The second `prepare` built all 64 rounds; its 14 failed MECHANICAL attempts were all the autopurge re-arm line's coverage timing, classified before the freeze commit (B2).
- `run --pr 138`: 64 rounds in frozen order, 06:36:31–07:13:08Z, no stop, no redispatch, every round classified `none`. Round wall median 28.6 s (16.7–60.4 s). Every seat exited 0 inside its 600 s watchdog.
- Observed identities: `claude-opus-5-5` (effort unobserved) and `gpt-6-astra` at `high`, in both orientations.
- Usage: Claude COMPLETE for all 64 Claude seats (102,250 output tokens); Codex PARTIAL (1,445,615 total tokens, output UNKNOWN).
- Merged verdicts: twin rounds 32 NEEDS_WORK; reference rounds 23 PASS_WITH_ISSUES, 6 PASS, 3 NEEDS_WORK.

## Condition 2: the false alarm

- **J4 reference, codex orientation, rep 1.** The Codex primary (`gpt-6-astra`) raised one HIGH behavioral finding, `4f160373…`: with `noDisposeOnSet: true`, a same-value growth evicts `b` but `disposeAfter` is not called until another operation drains the queue, which it says violates "Each evicted entry must receive the existing eviction disposal behavior." The existing library behaves the same way on every set path: the drain at the end of `#set` is gated by `!noDisposeOnSet`, so insertion and different-value replacement also defer `disposeAfter`. The check (`J4-nodisposeonset-evict-existing-disposal.sh`) runs the finding's own scenario and requires the evicted entry to receive the same `dispose`/`disposeAfter` delivery as the existing different-value eviction path: base false (no remeasurement), reference true, twin false (no eviction). The claim does not reproduce on its own tree, so it is a false alarm, and its NEEDS_WORK round is an unsupported terminal. Astra's calibration review had examined the same interaction and found it insufficient to classify the reference as defective; Astra's label audit accepted the check after the exchange.
- **Reported, not false alarms:** two J2 reference rounds ended NEEDS_WORK on a MEDIUM `verdict_binding: true` coverage finding only (both Codex seats: the codex-orientation primary in rep 1 and the claude-orientation pair in rep 2), each saying the public tests never check an explicit `allowStale: false` against a cache whose default is `true`. The strengthened rule counts such rounds and reports them.

## Hits and the pool

- 146 rank ≥ 1 findings pooled. Final labels: 69 rank-2 behavioral matches (all hits), 8 rank-2 behavioral non-matches (7 twin-only extras — each claim fails only on the twin — and the false alarm), 17 rank-2 coverage (neutral), 2 rank-1 matches (detections), 50 other rank-1 findings. No execution-condition findings.
- Hit findings by seat: Claude 41, Codex 28. By form: 33 HIGH `verdict_binding: true`, 28 HIGH, 8 MEDIUM `verdict_binding: true`.
- Checks: 77 rank-2 behavioral claims, each run by `screen.py check` on freshly materialized base, reference and twin trees with one of 17 committed [check scripts](check-scripts/); all 77 hold on the reference and fail on the twin ([logs](checks/)).

## Labels and audit

- Root labeled the masked pool before any unmasking (drafts per task by Claude subagents from the same masked inputs, reviewed by root; `783f713f`), then ran the checks. Astra (gpt-6-astra, ultra, read-only) audited blind, from masked inputs only, and differed on 10 labels and on one check. Root adopted all 10 labels (four findings root had labeled coverage that also assert the code breaks the clause; four P2 findings whose collection trigger and `TypeError` differ from the recorded attrs-instance trigger and `NotAnAttrsClassError`; two rank-1 J4 findings), added checks for the four newly behavioral findings (`75b338aa`), and disputed the J4 check with cited evidence. In the final stage, given each checked finding's own tree, Astra accepted the J4 check and reported no remaining dispute. Record: [`labels-audit.md`](labels-audit.md), [`audit.json`](audit.json), [`labels.json`](labels.json), [`reads.json`](reads.json).
- Read scan: 0 definite excluded reads; 13 ambiguous reads, all Codex seats, all allowed by root and Astra: 8 shell words holding test-file globs and 5 unparsed exec blocks of relative reads (`src/index.ts`, test files, `package.json`, `.devlyn` results, the round's spec) in the round's work directory. None carried a finding or verdict.
- The read scan is heuristic, not a completeness proof for arbitrary shell or interpreter execution; isolation relies on the physical seals and absence of hidden material in the research repository.

## What changed from 0226

- Both registered causes are gone: 0 rejected Claude outputs (0226: 3), 0 BLOCKED rounds (0226: 5; the Codex BLOCKEDs on an unevidenced "offline, with Node 22" condition), and the fresh specs state no unevidenced execution condition.
- The new failure is of a different kind: one Codex primary read "existing eviction disposal behavior" as immediate delivery and blocked a correct reference. Two further Codex NEEDS_WORK verdicts on reference rounds rested on coverage findings only.

## Predictions (registered before the fix and any probe)

| | prediction | result |
|---|---|---|
| Root | 32/32 hits (P ≈ 0.8) | yes |
| Root | 0 false alarms, unsupported extras and invalid references (P ≈ 0.7) | no (1 false alarm) |
| Root | 0 rejected Claude outputs (P ≈ 0.85) | yes |
| Root | 0 merged BLOCKED | yes |
| Root | median round wall ≤ 40 s | yes (28.6 s) |
| Root | P(PASS) ≈ 0.4 | NOT PASS |
| Astra | 32/32 hits | yes |
| Astra | 0 false alarms, unsupported extras and invalid references | no (1 false alarm) |
| Astra | 128/128 seats accepted | yes |
| Astra | 0 BLOCKED, retries or execution-only repairs | yes |
| Astra | median round wall ≤ 60 s | yes |
| Astra | P(PASS) = 0.5 | NOT PASS |
