# 0263 result: independent acceptance look (candidate D) on owner replays

Measured 2026-10-31 to 2026-11-01. All 16 D runs are final. The comparator is 0262's 16 B outputs, reused because their clone starts and driver policy match. The design is in [DESIGN.md](DESIGN.md). Every raw artifact stays private because the tasks come from the owner's private repositories; this record carries counts only.

**Verdict: REJECT D** by the pre-registered rule:
- (d) D has no correct completion;
- (b) on T2, D has more false completions than B (7 vs 3).

Draft PR #328 was closed without merge.

## Apparatus

- **Tasks, routes, starts.** The same as 0262: two replayed web UI tasks × four routes × two replicates, each from a fresh clone. The D arm is PR #328's head.
  - T1 is a sidebar list feature; T2 moves a guide into a page section.
  - The routes are drain-Codex, drain-Claude, direct Claude, and direct Claude orchestrating Codex.
- **Flag.** The user-facing flag was fixed before each session: in the committed packet for a drain, and in the launch environment for direct work.
- **Delivery boundary.** D counts as delivered only with a final, source-bound `ship` from the controller's reviewer and a finished route. B keeps 0262's boundary.
- **Product change since 0262.** D's arm includes the unattended-tool guard (4.3.20).
- **Rating.** The owner re-rated B and D blind, 32 outputs mixed and shuffled within each task:
  - 16 B outputs;
  - 11 delivered D outputs;
  - 5 blocked D candidates, rated as a false-rejection diagnostic only.

  The guide, captures and question were the same as 0262.
- **Capture check before rating.** One capture defect was found and fixed before the owner saw anything.
  - On one output, the automated tap closed a list that was already open on load.
  - The capture script now skips controls that are already open, and D's T1 packets were recaptured.
  - B's clones no longer existed, so B could not be recaptured. Root verified the fix leaves every B packet unchanged: B's taps all opened closed lists, and the other B outputs had no tap.
- **Definitions.** CC, claimed_done and FC are as in 0262. claimed_done was classified blind by three classifiers, who were unanimous.

## Results

Every delivered output in both arms passed the hidden witness and the checks, so CC and FC rest on the owner's rating.

| | B | D |
|---|---:|---:|
| delivered | 16/16 | 11/16 |
| CC, T1 | 0/8 | 0/8 |
| CC, T2 | 0/8 | 0/8 |
| FC, T1 | 6 | 4 |
| FC, T2 | 3 | **7** |
| claimed done | 9/16 | 11/16 |
| tokens, arm total | 172.5M | 311.4M (1.81×) |
| wall, arm total | 22,098 s | 31,172 s (1.41×) |
| safety violations | (0262's one attempt) | 0 |

- **Owner.** The owner rejected all 32 outputs. Drift on B is 0/16: every B output got the same verdict as in 0262.
- **Reviewer outcomes across the 16 D runs:**
  - 3 shipped on the first review;
  - 8 shipped after one repair;
  - 4 were sent back twice and ended `NOT SHIPPABLE` or `needs-review`;
  - 1 never reached review: a Claude session ended while waiting on its own review subagent.
- **Blocked candidates.** The owner rejected all 5, so the reviewer made no false rejection. Its failure was passing work the owner rejects.
- **Claims.** Every delivered D report claimed done and cited the reviewer's `ship`. The independent pass became the claim, and every claim was a false completion.
- **Cost.** The reviewer sessions used 0.94M tokens. Almost all of D's extra cost came from executor repair and capture work.
- **Why the owner rejected:** design craft, not breakage.
  - a text link where an icon is standard (delete, new item);
  - controls that do not read as buttons, or use a loud colour;
  - an oversized copy button where an icon inside the code field is expected;
  - readability and side padding;
  - mobile placement.

  The ship bar ("nothing broken; minor taste differences ship") passed all of these.
- **Predictions, frozen before any D run:**
  1. D FC ≤ 3: false (11).
  2. 2 ≤ D CC ≤ 5: false (0).
  3. D raw tokens ≥ 1.5× B: true (1.81×).
  4. At least one `NOT SHIPPABLE`: true (4).
  5. Owner drift on B ≤ 2: true (0).

## AI raters (secondary)

Both raters judged the same blind packet with the same guide, before the owner's ratings were opened.

| rater | agrees with owner | accepts (B / D delivered / D blocked) |
|---|---:|---:|
| Astra ultra | 25/32 | 7 (2 / 4 / 1) |
| Opus 5.5 | 26/32 | 6 (1 / 5 / 0) |

- Post-hoc observation, not a result: the in-loop reviewer used the same model and the same bar as the Astra rater, yet shipped 11 outputs, of which the rater accepted only 4. The two looks differ in what they saw:
  - the reviewer saw the executor's own captures, one output at a time;
  - the rater saw root's standard captures, four outputs per call.

## Reading

- Moving "done" to an independent reviewer did not raise acceptance. It raised false completions, because the reviewer's pass became the claim.
- Together with 0262, looking at the screen (C) lifted 2 of 16 outputs to the owner's bar, and an independent look with an explicit bar (D) lifted none. The owner rejected 62 of 64 ratings over the two rounds.
- The gap is in how the change is built (design craft inside an existing product), not in how "done" is verified. The next candidate targets the build.

## Safety

An audit of every D tool call found no use of the owner's browser, desktop, accounts or profile. One session drove a headless browser with a throwaway profile.

## Smoke

Two D runs went first, one at a time, and both stand as pilot rows:
- a drain, sent back twice and ended `needs-review`;
- a direct run, shipped on the first review.

They confirmed that receipts, review custody, captures and the delivery boundary were read as designed. Two recording fixes were made before the remaining runs, with no execution affected:
- a blocked drain records its last reviewed source;
- reviewer tokens are counted.
