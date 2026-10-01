# ROADMAP.md Template

Generate `docs/ROADMAP.md` using this structure. This is an **index** — brief descriptions and links to detail specs. No inline specifications.

---

```markdown
# [Project Name] Roadmap

> **North Star**: [One sentence from VISION.md]

## Phase 1: [Theme Name] (Target: [date or timeframe])
<!-- 1-2 sentences: what this phase delivers and why it comes first -->

| # | Feature | Status | Priority | Complexity | Spec |
|---|---------|--------|----------|-----------|------|
| 1.1 | [Feature Name] | Planned | High | Medium | [spec](roadmap/phase-1/1.1-feature-name.md) |
| 1.2 | [Feature Name] | Planned | High | High | [spec](roadmap/phase-1/1.2-feature-name.md) |
| 1.3 | [Feature Name] | Planned | Medium | Low | [spec](roadmap/phase-1/1.3-feature-name.md) |

## Phase 2: [Theme Name] (Target: [date or timeframe])
<!-- 1-2 sentences -->

| # | Feature | Status | Priority | Complexity | Spec |
|---|---------|--------|----------|-----------|------|
| 2.1 | [Feature Name] | Planned | High | Medium | [spec](roadmap/phase-2/2.1-feature-name.md) |

## Backlog
<!-- Ideas acknowledged but not yet phased -->
| Feature | Reason Deferred | Revisit |
|---------|----------------|---------|
| [Name] | [Why not now] | [When to reconsider] |

## Decisions
| # | Decision | Date | Record |
|---|----------|------|--------|
| 1 | [Decision Title] | [YYYY-MM-DD] | [record](roadmap/decisions/001-decision-title.md) |
```

## Guidelines

- Status values: `Planned` | `In Progress` | `Done` | `Blocked`
- Priority: `High` | `Medium` | `Low`
- Complexity: `Low` | `Medium` | `High`
- Feature names should be user-facing descriptions, not technical jargon
- Each phase should deliver usable value — no "infrastructure only" phases
- The spec column links to the detail spec in `roadmap/phase-N/`
- Numbering: `{phase}.{item}` (e.g., 1.1, 1.2, 2.1)
- Slug format for filenames: `{id}-{kebab-case-name}.md` (e.g., `1.1-user-auth.md`)
- Keep this file under 150 lines — it's an index, not a specification
