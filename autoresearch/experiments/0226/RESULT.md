# 0226 recall screen — result

Registered in [0226](../../iterations/0226-verify-recall-screen.md). Driver [`screen.py`](screen.py); frozen [`manifest.json`](manifest.json) is the only commit of freeze PR #128 (`c8aa8277`, created 2026-09-29T05:08:34Z, before the first seat started at 05:08:57Z). Labels, checks and Astra's audit were committed and pushed on `candidate/0226-score` (`31dd059e`) before the one-shot join. Raw outputs: `/Users/Shared/devlyn-vr` (sealed root); copies of the scoring outputs are in [`evidence/`](evidence/); the corpus is in [`corpus/`](corpus/) and matches the manifest's 85 digests.

## Outcome: NOT PASS (condition 5 only)

| # | condition | result |
|---|---|---|
| 1 | 32/32 target hits | **32/32** — both seats hit in every twin round |
| 2 | 0 reference false alarms (incl. unsupported terminal) | **0** — no reference round ended NEEDS_WORK |
| 3 | 0 unsupported extras | **0** |
| 4 | no invalid reference | **0** — every checked claim holds on the reference |
| 5 | every round ends non-BLOCKED; every seat completes, is authenticated and accepted by the merge | **violated: 5 of 64 rounds BLOCKED** (all reference rounds) |
| 6 | seals, overlap, reads, witness | holds — sealed inventory unchanged, overlap in 64/64, 0 excluded reads, no instruction attachments, witness intact at start/end/score/join |

Registered consequence: steps 2–5 stay held; any next move needs a new registration. Nothing ships from 0226.

## Run

- `prepare` (prepare-5) built all 64 rounds on a loaded host (other Codex/Claude sessions running; the user chose to proceed). MECHANICAL passed in every round.
- `run --pr 128`: 64 rounds in frozen order, 05:08:57–05:43:42Z, no stop, no redispatch, every round classified `none` by the frozen infra classifier. Round wall median 26.1 s (15.6–63.9 s). Every seat exited 0 inside its 600 s watchdog.
- Observed identities: `claude-opus-5-5` (effort unobserved) and `gpt-6-astra` at `high`, in both orientations.
- Usage: Claude COMPLETE for all 64 Claude seats (111,992 output tokens); Codex PARTIAL (1,295,983 total tokens, output UNKNOWN).

## Condition 5: the five BLOCKED rounds

| round | primary / pair | cause |
|---|---|---|
| J2 reference, codex, rep 1 | Codex BLOCKED / Claude rejected | both causes below |
| J2 reference, codex, rep 2 | Codex BLOCKED / Claude PASS_WITH_ISSUES | Node 22 evidence |
| J1 reference, codex, rep 2 | Codex BLOCKED / Claude PASS | Node 22 evidence |
| J4 reference, claude, rep 1 | Claude rejected / Codex PASS | prose preamble |
| J4 reference, codex, rep 1 | Codex PASS / Claude rejected | prose preamble |

- **Prose preamble (3 Claude seats, 2 as pair, 1 as primary).** The seat wrote a prose paragraph before its JSONL and verdict (e.g. "The fix works and the test run passed, so I'm not raising any blocking findings."); the remaining lines were LOW findings and PASS_WITH_ISSUES. The merge rejected the seat (`verify-judge-emission-contract-violated`, `claude-judge.r0.stdout: invalid JSONL`), so the round became BLOCKED. This is the mechanism 0225 recorded twice (s6-16-r0): the candidate applies the strict emission contract to both seats and recovers a narrative preamble only for NEEDS_WORK with findings.
- **Node 22 evidence (3 Codex primaries, J1/J2 reference rounds).** The seat emitted one MEDIUM `verdict_binding: true` coverage finding — the spec's verification line requires `npm test` "offline, with Node 22", and the candidate's sealed MECHANICAL record shows neither — and chose verdict BLOCKED. Not an input BLOCKED: `input_flags` is empty in all 64 rounds and the seat states a product evidence gap, not a missing input. The same finding appeared once more (J2 twin, Codex primary), where the verdict was NEEDS_WORK.
- Input BLOCKEDs: 0. No seat timed out, crashed, retried or was unauthenticated for any reason other than the three rejected Claude outputs.

## Hits and the pool

- 165 rank ≥ 1 findings pooled. Final labels: 77 rank-2 behavioral matches (all hits), 4 rank-2 behavioral non-matches (twin-only extras: each claim fails only on the twin), 8 rank-2 coverage (neutral), 76 rank-1 (50 behavioral non-match, 25 coverage, 1 detection).
- Hit findings by seat: Claude 45, Codex 32. By form: 65 HIGH, 6 HIGH `verdict_binding: true`, 6 MEDIUM `verdict_binding: true`. Every twin round (32) ended NEEDS_WORK with a hit from each seat.
- Checks: 81 rank-2 behavioral claims, each run by `screen.py check` on freshly materialized base, reference and twin trees with one of 11 committed [check scripts](check-scripts/); all 81 hold on the reference and fail on the twin ([logs](checks/)).

## Labels and audit

- Root labeled the masked pool before any unmasking, then ran the checks. Astra (gpt-6-astra, ultra, read-only) audited blind, from masked inputs only, and differed on 24 labels (whether a coverage finding that only explains a missed defect is behavioral, and whether a bare "F1" reference establishes the target mechanism) and on two checks it judged unfaithful (a nested-attempt claim in J3, a bypassed decimal-place guard in J4). Root adopted all 24 of Astra's verdicts — the stricter reading, committed before unmasking (`e8aaed74`) — and replaced the two checks (`8570f425`). In the final stage, given each checked finding's own tree, Astra confirmed both replacement checks faithful and reported no remaining dispute. Record: [`labels-audit.md`](labels-audit.md), [`audit.json`](audit.json), [`labels.json`](labels.json), [`reads.json`](reads.json).
- Read scan: 0 definite excluded reads; 12 ambiguous reads, all allowed by root and Astra. All 12 come from Codex seats: 11 are shell words the scanner could not resolve as paths (`rg` regex patterns and `-g` globs such as `rg --files -g '*results.json' …`, run in the round's work directory), and 1 is an unparsed exec block of relative reads and a `git diff` in the work directory. That block's tail carried one J4 finding and its seat's NEEDS_WORK verdict, which root and Astra saw while adjudicating reads; root's labels were drafted before then.
- **Correction (after the join):** root's `reads.json` reasons and the audit prompt described the 11 word entries as Claude Read/Grep/Glob path fields; they are Codex shell words, as above. The verdicts do not depend on the origin (patterns and globs evaluated inside the round's work directory), and `reads.json` is left as joined. Astra's record check re-examined the 11 entries under the corrected origin (see the PR record).
- The read scan is heuristic, not a completeness proof for arbitrary shell or interpreter execution; isolation relies on the physical seals and absence of hidden material in the research repository.

## Predictions (registered before authoring)

| | prediction | result |
|---|---|---|
| Astra | 32/32 hits | yes |
| Astra | no false alarm or unsupported extra | yes |
| Astra | ≥ 1 hit labeled MEDIUM `verdict_binding: true` | yes (6) |
| Root | ≥ 31/32 hits | yes (32) |
| Root | ≥ 1 false alarm or unsupported extra; P(PASS) ≈ 0.3 | no (0); NOT PASS for another reason |
| Root | ≥ 1 MEDIUM `verdict_binding: true` hit | yes |
| Root | 0 input BLOCKEDs | yes |
| Root | Codex seats author most hits | no (Claude 45, Codex 32) |
| Root | median round wall ≤ 120 s | yes (26.1 s) |

## Scope

As registered: NOT PASS does not prove regression against step 1, and this screen says nothing about natural recall, recall after repair, population reliability, savings, or steps 3–6.
