# Skill Quality Checklist

Verify the generated skill against every item below before finalizing.

---

## Frontmatter

- [ ] `name` is lowercase, hyphens and digits only, max 64 chars
- [ ] `name` does not contain "anthropic", "claude", or "official"
- [ ] `description` is third-person, max 1024 chars
- [ ] `description` includes specific trigger phrases ("Use when user says...")
- [ ] `description` first sentence states what the skill does
- [ ] `allowed-tools` uses the minimal set needed (not all tools)
- [ ] `argument-hint` shows expected input format if skill takes arguments
- [ ] No XML tags in any frontmatter field values

## Body Structure

- [ ] Starts with a title (`#`) and one-line purpose statement
- [ ] Lists reference files with descriptions (if multi-file)
- [ ] Workflow uses numbered steps with `###` headings
- [ ] Each step starts with an action verb (Parse, Read, Generate, Validate)
- [ ] Each step has clear entry and exit criteria
- [ ] Output format is explicitly defined

## Content Quality

- [ ] Instructions are explicit, not vague ("Review for X, Y, Z" not "Review the code")
- [ ] Includes WHY context for non-obvious rules
- [ ] Uses XML tags for complex structure (`<example>`, `<rules>`, `<output-format>`)
- [ ] Uses "consider"/"evaluate" instead of "think"
- [ ] Contains at least one concrete `<example>` block
- [ ] Scope is bounded (file limits, directory limits, or explicit boundaries)
- [ ] No conflicting instructions

## Error Handling

- [ ] Handles empty `$ARGUMENTS` (asks user or uses sensible detection)
- [ ] Handles missing files (clear error message, not silent fallback)
- [ ] Handles unexpected input (validation with actionable error)
- [ ] No silent fallbacks to defaults (project convention)

## Prompt Engineering

- [ ] No over-triggering (description is specific, not generic)
- [ ] No aggressive language ("MUST", "NEVER EVER", "ABSOLUTELY")
- [ ] No wall of text without headings or structure
- [ ] No unbounded scope ("analyze everything")
- [ ] Anti-hallucination patterns applied (grounded in file content)
- [ ] Degree of freedom matches skill type (guardrails for high, specs for low)

## Completeness

- [ ] All reference files mentioned in SKILL.md exist
- [ ] Reference files have table of contents if over 100 lines
- [ ] Reference files are one level deep (no nested references)
- [ ] Total SKILL.md is under 500 lines (split if over)
- [ ] Skill is self-contained (works without external dependencies)
- [ ] Installation path is correct (`.claude/skills/<skill-name>/`)
