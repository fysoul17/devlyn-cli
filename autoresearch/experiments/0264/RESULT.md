# 0264 result: build-time design fidelity (candidate E) on owner replays

Measured 2026-11-01 to 2026-11-02. All 16 E runs are final. As in 0263, the comparator is 0262's 16 B outputs. The design is in [DESIGN.md](DESIGN.md). Every raw artifact stays private because the tasks come from the owner's private repositories; this record carries counts only.

**Verdict: TRIGGER_MISS** by the pre-registered rule. Only 10 of 16 E runs applied the bullet, and the threshold is 12. The candidate ends here, and this is not a quality result.

Descriptively, the owner rejected all 32 outputs, so E has no correct completion. Had the trigger fired, rules (a), (b) and (c) would each have rejected E.

Draft PR #330 was closed without merge.

## Apparatus

- **Tasks, routes, starts.** These are the same as in 0262 and 0263. The E arm is PR #330's head, which adds one "User-facing UI" bullet to the managed instruction block.
- **Smoke.** Two E runs went first, one at a time, and both stand as pilot rows. Each showed a visible precedent statement before its first UI edit.
- **One rerun.** A host disk block stopped one E run, and it was rerun. The blocked attempt is kept privately and left out of cost, as in 0262.
- **Uptake audit.** The predicate was frozen in the design. A fixed script cut each transcript at the first UI edit, and three blind classifiers judged each run. They were unanimous on 31 of 32; one B run split 2 applied to 1 unknown, and the majority (applied) stands.
  - **B.** B was never told to state a precedent, so B is scored only for observable inspection and reuse. B's diffs no longer exist, so B is judged from the excerpt alone, and a missing trace counts as unknown.
- **Amendment 1.** It was registered before any E output was rated or shown; see [AI answer key](#ai-answer-key-amendment-1-secondary). It changed neither the builders, the bullet, the uptake audit nor any decision threshold.

## Results

| | B | E |
|---|---:|---:|
| delivered | 16/16 | 16/16 |
| bullet applied | not told (7 observed, 9 unknown) | **10/16** |
| CC, T1 | 0/8 | 0/8 |
| CC, T2 | 0/8 | 0/8 |
| FC, T1 | 6 | 6 |
| FC, T2 | 3 | 5 |
| claimed done | 9/16 | 11/16 |
| tokens, arm total | 172.5M | 190.7M (1.11×) |
| wall, arm total | 22,098 s | 23,713 s (1.07×) |
| safety violations | (0262's one attempt) | 0 |

- **Uptake by engine.** Codex-implemented runs applied the bullet 8/8; Claude-implemented runs applied it 2/8 (drain 0/4, direct 2/4).
  - Every Claude miss read comparable surfaces before its first UI edit, and none stated a precedent and pattern before the edit.
  - In the three T2 misses, the diff reused the precedent's patterns anyway. The classifiers' reasons for the three T1 misses do not show reuse.
- **Owner.** The owner rejected all 32 outputs. Drift on B is 0/16. The owner gave the reasons once for the whole set: not refined, not current, not intuitive, not attractive.
- **Order caveat.** Root's result report named the AI key's aggregate (no output ships) before the owner rated. The owner's verdicts are therefore not blind to it.
  - The owner clicked 3 outputs on the page.
  - The owner rejected the other 29 in one message.
  - The verdict does not depend on these ratings.
- **Predictions, frozen before any E run:**
  1. ≥ 12 E applied and ≤ 6 B applied: false (10; 7).
  2. 2 ≤ E CC ≤ 5 with T1 ≥ T2: false (0).
  3. E tokens 0.95–1.15× B and wall ≤ 1.25× B: true (1.11×; 1.07×).
  4. E claimed_done ≥ 6: true (11).
  5. Owner drift on B ≤ 2: true (0).
  6. Coded class 1–2 incidences fewer on E: not evaluable, because there is no per-output note.

## AI answer key (amendment 1, secondary)

- **Owner direction (2026-11-01).** The owner can no longer supply the answer key for every round. AI raters make the key, and the owner grades it.
- **Order.** The owner chose the reviewers' fix for anchoring:
  - the owner clicks ship or send back first;
  - the card's key opens only after that click is stored;
  - the first click is the scored verdict, and a later change is kept apart;
  - per-finding marks and notes are descriptive only.
- **Guide.** The rater guide keeps 0263's framing and four reject reasons. It replaces "minor taste differences ship" with "polished product quality" and adds the owner's recurring reasons from the 0262 and 0263 notes, which include notes on the 16 B outputs. Agreement on B is therefore exposed.
- **Raters.** Astra ultra and Opus 5.5 rated the outputs.
  - Each batch ran in a fresh session that held only that batch's images.
  - Logs were audited for any tool use beyond those images.
  - The combined verdict ships only when both raters ship. Findings stay per rater, and there are no scores.
- **Isolation audit.** It found two defects, both fixed before any owner rating:
  - a relative-path false positive in the audit itself;
  - Opus skipped images in some 4-output batches (12 of 32 opened in two batches).

  Now a batch fails unless every image was opened. One batch was split into one output per session.
- **Result.** The combined key shipped 0/32. Astra accepted 1 (a B output) and Opus accepted 0.
  - Agreement with the owner on B (exposed): combined 16/16, Astra 15/16, Opus 16/16. On E: 16/16 for each.
  - This does not calibrate the key. The owner accepted nothing, so missed accepts cannot be measured, and a key that always rejects scores the same, as amendment 1 anticipated.
  - No finding was marked.
- **Accept direction (post hoc, exposed).** The key also rated the only two outputs the owner has accepted, both C outputs from 0262. The prediction, written before the run, was 0 of 2.
  - The key rejected both. Each rater rejected both, and the audits were clean.
  - The findings name narrow- and phone-width issues on both outputs, and both raters also name a wide-screen placement issue on one. The owner had accepted both outputs, one of them with the note "would ship, but not polished".
  - The key does not reproduce the owner's accepts.

## Reading

- **Applied runs were rejected too.** Codex applied the bullet on all 8 of its runs, and the owner rejected all 8. A repair of Claude's pre-edit statement would be a new, newly frozen candidate, and its effect is unknown.
- **The owner's reasons were taste.** The owner's reasons moved from specific craft (0262, 0263) to overall taste. The design's risk list named this ("owner taste beyond conventions").
- **Three rungs.** Over 0262–0264 the owner rejected 94 of 96 ratings of 64 unique outputs. None of the three rungs passed its decision rule:
  - the builder looks at its screens (C, 0262): 2 accepts, both on T1;
  - an independent reviewer decides "done" (D, 0263): 0 accepts;
  - the builder grounds in a product precedent (E, 0264): 0 accepts.
- **Next.** The frozen next-rung branch is not evaluable under amendment 1. The next step is the owner's.

## Safety

An audit of every E tool call found no use of the owner's browser, desktop, accounts or profile, and no secret. Browser checks used headless browsers with throwaway profiles.
