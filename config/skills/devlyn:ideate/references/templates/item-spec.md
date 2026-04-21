# Item Spec Template (Auto-Resolve-Ready)

Generate one file per roadmap item at `docs/roadmap/phase-N/{id}-{name}.md`. This is the most critical template — each spec becomes the direct input to `/devlyn:auto-resolve`.

---

```markdown
---
id: "[phase.item]"
title: "[Feature Name]"
phase: [N]
status: planned
priority: [high | medium | low]
complexity: [low | medium | high]
depends-on: []
---

# [id] [Feature Name]

## Context
<!-- 2-3 sentences MAX. Just enough for auto-resolve to understand WHY this exists. -->
<!-- Extract only the relevant context from the vision — don't make the implementation agent read the full vision document. -->
[Project] does [what]. This feature [enables/improves/fixes] [specific user capability].

## Customer Frame
<!-- One sentence. When [situation], [user] wants to [motivation] so they can [outcome]. -->
<!-- Use this to resolve ambiguous requirements: prefer the behavior that best serves this user outcome, and do not add capabilities outside this frame. -->

## Objective
<!-- One sentence: what the user can do after this is implemented. -->

## Requirements
<!-- These become auto-resolve's done-criteria. Quality of these requirements directly determines implementation quality. -->
- [ ] [Specific, testable requirement]
- [ ] [Specific, testable requirement]
- [ ] [Specific, testable requirement]
- [ ] ...

## Constraints
<!-- Technical constraints WITH reasoning. Implementation agents respect constraints significantly better when they understand the motivation. -->
- [Constraint] — Why: [reason]
- ...

## Out of Scope
<!-- What this item explicitly does NOT include. This prevents auto-resolve from over-building. -->
- [Feature/behavior] ([where/when it will be addressed, e.g., "Phase 2, item 2.3"])
- ...

## Architecture Notes
<!-- Technical context that helps implementation. Reference decision records when applicable. -->
<!-- Remove this section if the implementation is straightforward. -->

## Dependencies
- **Internal**: [Other roadmap items that must exist first, e.g., "1.1 User Auth"]
- **External**: [APIs, services, credentials, third-party setup needed]

## Verification
<!-- How to confirm this works. Overlaps with Requirements but focuses on observable user-facing behavior. -->
- [ ] [Observable verification step]
- [ ] ...
```

## Quality Criteria

Before writing a spec, verify each requirement against these criteria:

**Testable**: Can a test assert this, or can a human verify it in under 30 seconds?
- Bad: "The dashboard loads quickly"
- Good: "Dashboard initial render completes within 2 seconds on 3G throttled connection"

**Specific**: Is there exactly one interpretation of what "done" means?
- Bad: "Handles errors gracefully"
- Good: "Failed API calls display an error banner with the message and a retry button"

**Scoped**: Does this belong to THIS item only?
- Bad: "The app supports multiple languages" (cross-cutting concern, not a single item)
- Good: "The settings page displays a language selector with EN and KO options"

**Self-contained**: Can auto-resolve implement this without reading VISION.md or ROADMAP.md?
- If the Context section references principles without explaining them, it's not self-contained
- The spec should carry its own context, not point to other documents

## When a Spec Isn't Ready

If you can't write specific requirements for an item, it needs one of:
1. **More exploration** — go back to Phase 2 for this item
2. **Splitting** — the item is too large; break it into smaller, specifiable pieces
3. **A spike** — mark it as a research task whose output is a proper spec

Never generate a spec with vague requirements just to fill the roadmap. A backlog item with "needs exploration" is more honest and more useful than a spec with untestable requirements.
