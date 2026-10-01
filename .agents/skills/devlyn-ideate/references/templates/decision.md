# Decision Record Template

Generate decision records at `docs/roadmap/decisions/{NNN}-{title}.md`. These capture WHY a decision was made, preventing future agents and collaborators from re-debating settled questions.

---

```markdown
---
id: [NNN]
title: "[Decision Title]"
date: [YYYY-MM-DD]
status: accepted
---

# [NNN] [Decision Title]

## Context
<!-- What situation or question prompted this decision? -->

## Decision
<!-- What was decided. Be specific and concrete. -->

## Alternatives Considered

### [Alternative 1]
- Pros: [advantages]
- Cons: [disadvantages]
- Why rejected: [the deciding factor]

### [Alternative 2]
- Pros: [advantages]
- Cons: [disadvantages]
- Why rejected: [the deciding factor]

## Consequences
<!-- What changes as a result. Include both positive tradeoffs and costs accepted. -->
- [Positive consequence]
- [Cost or constraint accepted]
```

## Guidelines

- Status values: `proposed` | `accepted` | `superseded`
- Number decisions sequentially: 001, 002, 003...
- Focus on the "why rejected" for alternatives — this is what prevents re-debating
- Keep decisions atomic: one decision per record
- If a decision is later reversed, mark the original as `superseded` and create a new record referencing it
- Only create decision records for choices that affect multiple roadmap items or have non-obvious reasoning. Don't document every small implementation choice.
