# Mode Workflow Detail

SKILL.md keeps the mode invariants inline. This file holds the full workflow and examples for each mode — read when entering that mode.

## Expand Mode

The most common mode after initial setup. User already has Vision + Roadmap and wants to add new capabilities. Careful integration with existing documents is the whole game.

**On entry:**
1. Read `docs/VISION.md`, `docs/ROADMAP.md`, and existing phase `_overview.md` files to understand the established context.
2. Scan existing item specs to understand what's built and what's planned.
3. **Run the Archive Pass first** (see below). Summarizing a stale roadmap to the user wastes the exchange — they'll see "Phase 1 has 4 items" when really all 4 are already Done.
4. Summarize your understanding: *"Here's what exists: [phases, item count, current status]. You want to add [new area]. Does this expand an existing phase or warrant a new one?"*

**During ideation:**
- FRAME is lighter — the vision already exists, focus on framing the NEW area only.
- EXPLORE focuses on the new capability and how it integrates with existing features.
- CONVERGE must consider dependencies on existing items, not just new ones.

**During document generation:**
- Don't overwrite existing VISION.md unless the user explicitly wants to update it.
- Continue numbering from existing IDs (if Phase 2 has 2.1-2.4, new items start at 2.5 or create Phase 3).
- Add new rows to ROADMAP.md — don't regenerate the whole table.
- New item specs can reference existing items in their Dependencies section.
- If new items change the meaning of existing items, flag this: *"Adding [X] may affect the scope of existing item [Y]. Should we update [Y]'s spec?"*

## Replan Mode

Read existing docs first, run the Archive Pass before any reprioritization (can't sensibly reorder work that's already finished), then focus Converge on reprioritizing what remains. The Archive Pass also surfaces Backlog items whose Revisit date has passed — natural candidates when replanning.

## Quick Add Mode

Single concrete idea, bug report, or improvement. User doesn't need a full ideation session, just a new roadmap entry. This is the most common trigger for misuse: the request looks like a simple fix, temptation is to implement it. Don't. Capture it.

**On entry:**
1. Read `docs/ROADMAP.md` and relevant phase `_overview.md` files.
2. **Run the Archive Pass first** (see below) — *before* deciding where the new item goes. A stale roadmap will mislead phase selection and ID numbering.
3. Identify the best-fit phase (or suggest a new phase if nothing fits).
4. Determine the next available item ID (e.g., if phase 2 has 2.1-2.4, new item is 2.5).

**Workflow (minimal — no full Frame/Explore/Converge):**
1. Confirm: *"I'll add this as [item title] in Phase [N]. That sound right?"*
2. Ask 1-2 clarifying questions if the requirement is unclear (skip if user gave enough detail).
3. Generate the item spec per `references/templates/item-spec.md`.
4. Add a row to `docs/ROADMAP.md`.
5. Output confirmation: file path + suggested auto-resolve command.

**Example output:**
```
Added: docs/roadmap/phase-2/2.5-back-to-review-button.md

To implement:
/devlyn:auto-resolve "Implement per spec at docs/roadmap/phase-2/2.5-back-to-review-button.md"
```

Even for single-item additions, run the solo CHALLENGE rubric pass on just the new item — single-item additions are exactly where overengineering and workarounds slip in unnoticed, because the lack of surrounding context makes a bad item look self-contained and harmless.

## The Archive Pass (conditional — Quick Add / Expand / Replan)

**What it is**: ROADMAP.md is the tactical index. Done work should move to a collapsed `## Completed` block at the bottom — it doesn't clutter the active view. The pass is a bookkeeping operation on ROADMAP.md **only**; item spec files stay on disk at `docs/roadmap/phase-N/{id}.md` (never moved, renamed, or deleted). Any downstream tool that needs to re-read a Done item's spec must still find it at its original path.

**When to run:** only when `docs/ROADMAP.md` contains at least one phase where every row is `Done`. A quick scan tells you within seconds. Skip otherwise — running it on a roadmap with no fully-done phases is no-op bookkeeping that burns the user's turn.

**Steps:**
1. Read `docs/ROADMAP.md`.
2. For each phase where every row is `Done`: cut the `## Phase N: …` heading and table, move it into a new or existing `## Completed` block at the bottom as a `<details>` entry (format below). Use the latest completion date found in item spec frontmatter (`completed:`), or today's if absent. Item count is the row count.
3. Individual `Done` rows inside an otherwise-active phase stay put — mixed phases show recent wins alongside open work.
4. Scan the Backlog table; surface any row whose `Revisit` date has passed as a replan candidate (don't auto-promote — that's a conversation).
5. Scan `docs/roadmap/decisions/` for `accepted` decisions whose reasoning is visibly contradicted by newly-Done work; raise them as open questions rather than silently editing.
6. One-sentence report of what was archived, then proceed with the mode's main work. Skip the report if nothing changed.

**Completed block format** (place at bottom of ROADMAP.md, below Decisions):

```markdown
## Completed
<details>
<summary>Phase 1: Foundation (completed 2026-04-15, 4 items)</summary>

| # | Feature | Completed |
|---|---------|-----------|
| 1.1 | Auth & Onboarding | 2026-02-10 |
| 1.2 | Order Management | 2026-03-05 |
| 1.3 | Inventory Tracking | 2026-03-28 |
| 1.4 | Customer Directory | 2026-04-15 |
</details>
```

If `## Completed` already exists and you're archiving another phase, append a new `<details>` block — don't rewrite existing ones.

## Outdated Decisions

When a decision becomes wrong because the world changed under it:
- Don't delete it — set its `status:` to `superseded` in the decision file's frontmatter and add a one-line pointer to the replacement decision record.
- Preserves the reasoning history for future reference, which matters more than a tidy decisions table.
