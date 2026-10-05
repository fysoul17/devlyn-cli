# Planning and elicitation

How `plan` applies the question and autonomous policies in SKILL.md; [package-format.md](package-format.md) defines what it writes. No turn target, question quota or confirmation step applies.

## Inspect first

Read what the project already answers before asking: the code paths, tests and conventions the intent touches, the installed instructions and completion mode, `docs/specs/queue.md` and earlier loop packages, and any document the user supplied. Infer `kind` from the framing (investigate or explore → `spike`, a rough version → `prototype`, otherwise `feature`) instead of asking.

## What to ask

Only an answer that changes authorized behavior, scope, data semantics, acceptance or delivery:

- **Behavior** — the exact input, output and failure a user observes.
- **Scope** — what may change and what must not.
- **Data semantics** — persisted state, ordering, idempotency, migration.
- **Acceptance** — the smallest decisive check for each requirement.
- **Delivery** — local-only, PR or merge.

Lead with the recommendation and its consequence, for example: "Should `--lang fr` exit 1 naming the rejected code? Recommended: yes, so bad input stays visible instead of silently falling back to English." Decide preferences the user has no stake in.

## Autonomous planning

With `--autonomous`, or when a drain plans a legacy row, take only the defaults the autonomous policy allows and record each once under `## Decisions and assumptions`. Material ambiguity that affects the whole intent stops planning with its concrete question. Ambiguity confined to separable work leaves that work out of the package, named with its question under `## Constraints and exclusions`, while the independent authorized work is planned.

## Tasks and checks

- One task per independently verifiable deliverable.
- A check must fail on the wrong behavior. When requirements interact (state with ordering, idempotency, error priority or an exact output shape), add one compound check that exercises the interaction end to end. Validate each new guard with a violating control that fails and an allowed control that passes.
- Semantic or source judgments are review requirements, not regular expressions. A requirement that resists a mechanical check becomes a review requirement; it is never weakened into something checkable.
