# CHALLENGE Rubric (single source of truth)

## Contents
- Context — this is a planning rubric
- The 5 axes (NO WORKAROUND, NO GUESSWORK, NO OVERENGINEERING, WORLD-CLASS BEST PRACTICE, OPTIMIZED)
- Hard rule — respect explicit user intent
- Finding format
- Examples (good vs bad findings, plus a detour-sequencing example)

The 5-axis rubric applied in Phase 3.5 CHALLENGE of `devlyn:ideate`. Both the solo Claude pass and the Codex pass (when `--with-codex` is set) use this file — there is exactly one definition of the rubric, and both paths read it directly from SKILL.md.

The rubric exists because plans produced in a single pass, by a single model, in a single conversation almost always fail at least one axis somewhere. The user's historical experience: every time they asked "is this really no-workaround, no-guesswork, no-overengineering, world-class, optimized?", the honest answer was no. This phase makes the answer honestly yes before the user even has to ask.

## Context — this is a PLANNING rubric, not a code rubric

This rubric judges the shape of the roadmap: what items exist, in what order, why. It does NOT judge implementation details, code style, or abstractions in code. "Overengineering" here means overengineering the plan, not overengineering a function. When applying it, keep asking: *is this the most direct, optimized path from the user's stated problem to a working outcome?*

## The 5 axes

### 1. NO WORKAROUND

Does the item solve the actual problem directly, or does it route around a missing capability? If the direct path is "build X" and the item is "work around not having X", it fails.

Canonical failure pattern: the user asks for a feature that papers over a missing foundation. Building the feature adds an item to the plan without solving the real problem, and often makes the real problem harder to fix later.

### 2. NO GUESSWORK

Every requirement must be grounded in something the user explicitly confirmed, or in something verifiable from the problem framing. Silent assumptions, "I think the user probably wants...", and requirements invented to fill gaps all fail.

Canonical failure pattern: vague user input ("improve the dashboard") leads to a fully-specified plan full of invented detail. Correct handling is to mark every assumed fact as [ASSUMED], ask clarifying questions, and keep the plan minimal until the user fills in the gaps.

### 3. NO OVERENGINEERING (planning-stage)

The plan fails this axis when it contains any of:

- **Luxury items** — polish, theming, animations, nice-to-haves that do not serve the stated problem. A polish/theming item in Phase 1 of a tool that does not yet solve its core job.
- **Filler items** — items added to pad a phase or make the plan feel complete. If an item has no testable requirement a real user would notice if absent, it is filler.
- **Detour sequencing** — the plan takes the long way around when a direct route exists. Three items building toward X when one item could deliver X. Separate scaffold / store / deploy items when they could be bundled into the actual feature they enable.
- **Roadmap workarounds masquerading as features** — see axis 1. The same failure can fire on axis 1 (paper-over) and axis 3 (padding the roadmap with the workaround).

The question to ask for every item: *"Is this the most direct, optimized path to the stated goal, or are we decorating / detouring / papering over?"*

### 4. WORLD-CLASS BEST PRACTICE

Would a senior team at a top company structure the roadmap this way for this kind of product today? If a known-good pattern exists for sequencing or decomposing this kind of problem, name it and use it.

Canonical failure pattern: the plan uses a familiar-but-mediocre decomposition when a better-known-good pattern exists for the specific problem type. Example: using manual export/import for cross-device sync when autosave + cloud draft storage is the standard pattern across mainstream editing tools (Notion, Linear, Gmail, Google Docs).

### 5. OPTIMIZED

Does the sequencing minimize wait time, front-load risk, and ship user-visible value at every phase boundary? Dead phases — phases that are pure setup with no visible win for a real user — are a fail.

Canonical failure pattern: Phase 1 is entirely infrastructure (scaffold, models, deploy) and the first user-facing win arrives in Phase 2. Better: Phase 1 ships one thin vertical slice that a real user can use, even if it is small.

## Hard rule — respect explicit user intent

The rubric is a tool to prevent drift from quality, not a tool to override the user. If the user has explicitly and clearly stated a preference ("I want X, not Y"), the rubric does not silently replace X with Y. Instead:

- Run the rubric as normal.
- If an axis flags X, do not rewrite the plan. Record the finding and surface it to the user as an open question: "The rubric flags X on [axis] because [reason]. You explicitly asked for X — confirm you want to proceed, or consider [alternative]."
- The user makes the call. The rubric's job is to make the tradeoff visible, not to make the decision.

This rule exists because the 5-axis rubric is an opinionated lens, and opinionated lenses are wrong sometimes. The user's stated intent is ground truth when it is explicit. The rubric is ground truth only for things the user did not explicitly decide.

## Finding format

For every item that fails any axis, produce a finding in this exact format:

```
Severity: CRITICAL / HIGH / MEDIUM / LOW
Quote: [copy the specific item title or line you are critiquing — one line]
Axis: [which of the five]
Why it fails: [one sentence]
Fix: [one concrete revision — not "reconsider X", say what to do instead]
```

For the plan as a whole, give a one-line pass/fail per axis with one-sentence reasoning.

End with a verdict: `PASS / PASS WITH MINOR FIXES / FAIL — REVISION REQUIRED`.

The Quote field is load-bearing. It anchors each finding to a specific line in the plan, which prevents the common failure mode of generic unanchored critiques ("too much in Phase 1", "consider refactoring"). Anchored findings are actionable; unanchored findings are noise.

## Examples

<example>
BAD finding (too vague, not actionable):
  Severity: HIGH
  Axis: NO OVERENGINEERING
  Why: Phase 1 has too much.
  Fix: Reduce scope.

GOOD finding (anchored, specific, actionable):
  Severity: HIGH
  Quote: "1.3 — Theme customization (light/dark/custom accent colors)"
  Axis: NO OVERENGINEERING (luxury item)
  Why it fails: The product does not yet solve its core job of letting users save a session; theming is a decoration item that does not move the primary problem forward.
  Fix: Move 1.3 to backlog. Phase 1 is shorter by one item. Revisit theming only after the core save flow is shipped and used.
</example>

<example>
BAD finding:
  Severity: HIGH
  Axis: NO WORKAROUND
  Why: Item 2.1 is a workaround.
  Fix: Do it properly.

GOOD finding:
  Severity: CRITICAL
  Quote: "2.1 — Export/import session as JSON file so users can move work between devices"
  Axis: NO WORKAROUND
  Why it fails: The real problem is cross-device sync. File export is a roadmap workaround that asks the user to do the sync manually; it adds an item to the plan without solving the stated problem, and makes the real problem harder to fix later.
  Fix: Replace 2.1 with "Cloud-backed session storage" as a direct cross-device solution. If cloud storage is out of scope for the current phase, explicitly defer cross-device sync to a later phase rather than shipping a manual workaround as if it were the feature.
</example>

<example>
Detour sequencing finding:
  Severity: MEDIUM
  Quote: "Phase 1: 1.1-scaffold, 1.2-data-store, 1.3-log-today, 1.4-streak-display, 1.5-history-view, 1.6-manage-habits, 1.7-deploy"
  Axis: NO OVERENGINEERING (detour sequencing)
  Why it fails: Scaffold, data store, streak display, and deploy are not features a user would notice as separate items — they are implementation steps of the three actual user capabilities (log a habit, see streak, see history). Splitting them into standalone roadmap items pads the plan without delivering value at each boundary.
  Fix: Collapse Phase 1 to 2 items: "1.1 — Log a habit and see streak" (bundles scaffold + store + log + streak), "1.2 — History view". Deploy is part of each item's done criteria, not a standalone item. Result: 7 items → 2 items, same delivered scope.
</example>
