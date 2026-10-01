# 0228 diagnosis — why G still blocked a correct J4 reference once

[0228](../../../iterations/0228-verify-rubric-rescreen.md) stopped at R2 FAIL (Addendum C3). In 40 replays of the four J4 reference rounds, G's Codex primary blocked the correct reference once. Under F, the concurrent control, it blocked 4 of 16. The owner chose (2026-10-01) to diagnose, fix and re-screen. This is diagnostic evidence from the committed R2 records (`../r2/`) and the retained attempt folders; nothing here regrades R2.

## Method

For every R2 attempt, root compared the Codex seat's own record: the commands in its monitored stderr, its findings, and its verdict.

## Findings

1. **G changed how Codex seats work the clause.**
   - **Recorded base reads** (`git show <base_sha>:src/index.ts`; Codex transcripts can omit reads, C1): 38 of 40 G replays and 0 of 16 F replays.
     - Every G Codex primary read the base.
     - 37 of the 38 base-reading seats saw the drain guard (`if (!noDisposeOnSet && this.#hasDisposeAfter && this.#disposed)`).
     - The two G replays with no recorded base read are `G/488c710e81a1/rep-3` and `rep-9`, both Codex pair.
   - **G seats:** two of 40 raised the scenario.
     - `G/1801a5478ae8/rep-3` raised it as advisory MEDIUM: "this guard also exists at the base commit for other set-triggered evictions, and the requirement's phrase 'existing eviction disposal behavior' leaves unclear whether that inherited suppression should be preserved."
     - `G/6f89d26e0ccb/rep-6` bound it (finding 2).
   - **F seats:** all four F blocks argue from the clause and the option documentation (`src/index.ts` 884–886 / 2149), and none cites the base.
   - **Codex primaries on codex-orientation rounds:** they raised the scenario in 4 of 16 F replays and 2 of 20 G replays, and blocked in 4 of 16 versus 1 of 20 (one-sided Fisher p ≈ 0.11). Once raised, F bound 4 of 4 and G bound 1 of 2.
2. **The remaining block saw the base's deferral and still bound it.**
   - **What it read:** `G/6f89d26e0ccb/rep-6` (Codex primary, codex orientation) read the base's `#set` lines 2240–2330. That range holds the drain guard and the replace path's eviction through `#addItemSize`.
   - **What it concluded:** "This violates the new requirement 'Each evicted entry must receive the existing eviction disposal behavior.'" It argued that deferral itself is wrong ("pending until an unrelated operation drains it, potentially forever").
   - **What it did not do:** treat the base's deferral for set-triggered evictions under `noDisposeOnSet` as the existing behavior the clause asks for.
3. **The advisory seat compared with that existing operation.** It named "other set-triggered evictions" under the same option, saw that the base defers there too, and did not bind. Its reading window began at base line 2235 and included the add path's eviction; the blocking seat's began at 2240.
4. **G made three edits, not one:**
   - the comparison sentence after V:86;
   - deleting the pair section's "neither impact nor pre-existing origin makes an applicable violation advisory";
   - the coverage exception.

   The advisory seat's reason fits both the comparison step and the relaxed pre-existing-origin rule. The rubric's general "genuinely ambiguous clauses … are not demonstrated mandatory violations" fits it too.
5. **Engine pattern unchanged.** Every binding claim on a reference round in 0226, G3 and 0227 came from a Codex seat (0227 DIAGNOSIS, finding 2). So did every J4 block in the 0227 diagnosis replays and in R2, almost all from the primary; Claude seats raised none. Under G, the Codex pair (claude orientation) raised none in 20 replays.

## Diagnosis (hypotheses; cause not established, as C3 says)

G changed the process: Codex seats now read the base. The one remaining block had the base's deferral in view and still bound it. Three readings fit the records, and they are not exclusive:
- **(a) Scope.** G's comparison sentence applies to "a clause that requires an existing path's current behavior". The seat read "the existing … behavior" a new eviction path must receive as a plain new requirement.
- **(b) Pre-existing defect.** The seat treated the existing deferral as a pre-existing defect. The unchanged V:85 says such a defect does not excuse a violation, and G's "does not excuse unmet new requirements" supports binding.
- **(c) Chance.** The prompts are byte-identical apart from `workdir`, and one of 40 is within instability.

The rubric does not say two things:
- that the existing-behavior part of such a clause is met by matching the base's existing operation that performs the named behavior under the same options;
- that this existing behavior is not itself a defect under that part.

## What this does not show

- That closing the gap removes the block: one seat in 40 is consistent with random instability.
- That the rate generalizes beyond J4.
- That a wording change costs no recall. In J4, only the capacity overflow departs from every base operation: the base has no same-value eviction, and that eviction is the clause's new duty. Recall on the J4 twin therefore depends on the judge keeping the clause's new duty binding. Several 0227 twins (J2, J3) behave like the base in their trigger scenario while violating a concrete required property, so a comparison rule must never excuse a requirement the base does not already meet. None of this is tested.
