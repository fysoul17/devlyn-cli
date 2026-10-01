# VISION.md Template

Generate `docs/VISION.md` using this structure. Keep it under 100 lines — this is a strategic orientation document, not a detailed specification.

---

```markdown
# [Project Name] Vision

## North Star
<!-- One sentence. Every decision should move toward this. -->

## Principles
<!-- 3-5 guiding principles. Each includes what it means AND the tradeoff it implies. -->
1. **[Principle Name]** — [What this means in practice]. Tradeoff: [what we accept giving up].
2. ...

## Target Users
### Primary
<!-- Be specific: role, context, pain, what they need -->
**[Who]** — [Their situation]. Pain: [what frustrates them]. Need: [what they want].

### Not For
<!-- Explicitly state who this isn't for, so the team doesn't try to serve everyone -->
- [Audience] — Why: [reason this isn't our focus]

## Anti-Goals
<!-- Things we deliberately choose NOT to do, even if they seem like good ideas -->
- **[Anti-goal]** — Why: [the reasoning behind this constraint]
- ...

## Success Metrics
<!-- How we know this is working. Outcomes, not outputs. -->
- [Metric]: [target] (e.g., "Time to first value: under 5 minutes")
- ...
```

## Guidelines

- North Star should be ambitious but specific — "make X better" is too vague
- Principles without tradeoffs are platitudes — if a principle has no cost, it's not a real principle
- Anti-goals prevent scope creep downstream — be generous with these
- Success metrics should be measurable, even if the measurement is qualitative
- Write in the user's primary language, technical terms in English
