---
name: generate-skill
description: >
  Create well-structured Claude Code skills following Anthropic best practices.
  Generates SKILL.md files with proper frontmatter, workflow structure, and
  prompt engineering patterns for Claude 4.6. Use when building new skills,
  refactoring existing ones, or when user says "create a skill", "new skill",
  "generate skill", "make a command".
allowed-tools: Read, Grep, Glob, Edit, Write, Bash
argument-hint: "[skill description or name]"
---

# Generate Skill — Claude Code Skill Authoring

Create production-quality Claude Code skills with correct frontmatter, structured workflows, and Claude 4.6 prompt patterns.

Reference files in this skill directory:
- `REFERENCE.md` — Complete frontmatter field catalog and validation rules
- `PROMPT-PATTERNS.md` — Claude 4.6 prompt engineering patterns for skill bodies
- `CHECKLIST.md` — Quality verification checklist

## Workflow

### Step 1: Gather Requirements

Parse `$ARGUMENTS` for the skill description or name.

If `$ARGUMENTS` is empty or vague, ask the user:

> What skill do you want to create? Describe:
> 1. **What problem** does it solve?
> 2. **When** should it trigger? (user command, proactive, or both)
> 3. **What tools** does it need? (read-only, code modification, web access, etc.)

Determine the **degree of freedom**:
- **High** — Skill makes decisions autonomously (e.g., code generation, refactoring)
- **Medium** — Skill follows a workflow but adapts to context (e.g., review, analysis)
- **Low** — Skill executes a fixed procedure (e.g., scan, validate, format)

### Step 2: Choose Structure

Estimate the total line count for the skill content:

| Estimated Lines | Structure |
|---|---|
| Under 200 | Single `SKILL.md` file |
| 200–500 | `SKILL.md` + reference files (e.g., `REFERENCE.md`, `PATTERNS.md`) |
| Over 500 | Split into multiple separate skills |

Rules for reference files:
- One level deep only (no nested references)
- Add a table of contents if a reference file exceeds 100 lines
- Reference files use `${CLAUDE_SKILL_DIR}/FILENAME.md` for paths

### Step 3: Write Frontmatter

Read `${CLAUDE_SKILL_DIR}/REFERENCE.md` for the complete field catalog.

Apply these rules:
- `name`: lowercase, hyphens only, max 64 chars, no "anthropic" or "claude"
- `description`: third-person, max 1024 chars, include trigger phrases, no XML tags
- `allowed-tools`: minimal set needed — see tool presets in REFERENCE.md
- `argument-hint`: brief placeholder showing expected input format

### Step 4: Write Skill Body

Read `${CLAUDE_SKILL_DIR}/PROMPT-PATTERNS.md` for Claude 4.6 patterns.

Structure the body in this order:
1. **Title and purpose** — One-line summary of what the skill does and why
2. **Reference file links** — If multi-file, list reference files with descriptions
3. **Workflow** — Numbered steps with clear entry/exit criteria per step
4. **Output format** — What the skill produces (files, messages, reports)

Writing rules:
- Lead each step with an **action verb** (Parse, Read, Generate, Validate)
- Use `$ARGUMENTS` and `$N` for user input substitution
- Use XML tags (`<example>`, `<rules>`, `<output-format>`) for complex structure
- Include concrete examples — Claude treats examples as specifications
- Write "consider" or "evaluate" instead of "think" (for when thinking is disabled)

### Step 5: Add Behavioral Rules

Every skill needs explicit behavioral boundaries:

**Error handling** (mandatory — project convention):
```
When an error occurs, display the error clearly to the user with actionable guidance.
Do NOT silently fall back to defaults or placeholder data.
```

**Guardrails** based on degree of freedom:
- **High freedom**: Add constraints on what the skill should NOT do. Be specific.
- **Medium freedom**: Define decision criteria for branching logic.
- **Low freedom**: Specify exact expected inputs/outputs and validation.

**Common rules to consider**:
- What happens when `$ARGUMENTS` is empty?
- What happens when required files don't exist?
- What are the skill's boundaries? (what it explicitly does NOT do)
- Should it ask for confirmation before destructive actions?

### Step 6: Write Reference Files (if needed)

For multi-file skills, create reference files:

- Each file covers one topic (patterns, field catalog, examples, etc.)
- Start with a heading and brief description of the file's purpose
- Add a table of contents if the file exceeds 100 lines
- Use consistent formatting (tables for catalogs, code blocks for examples)

### Step 7: Validate

Read `${CLAUDE_SKILL_DIR}/CHECKLIST.md` and verify the generated skill against every item.

Fix any issues before presenting the final output.

## Output

After generating the skill, present:

1. **File listing** — All files created with line counts
2. **Installation path** — `.claude/skills/<skill-name>/`
3. **Test invocation** — Example command to test the skill

Offer to:
- Run `/devlyn.review` on the generated skill for quality assurance
- Run `pyx-scan` if the skill will be published

---

## Examples

<example>
**Input**: `/generate-skill A skill that validates PR descriptions against a template`

**Output structure** (single file):
```
.claude/skills/validate-pr/
└── SKILL.md          (~120 lines)
```

Frontmatter:
```yaml
name: validate-pr
description: >
  Validate pull request descriptions against a project template.
  Checks for required sections, formatting, and completeness.
  Use when reviewing PRs or when user says "check PR", "validate PR description".
allowed-tools: Read, Grep, Glob, Bash(gh pr view *)
argument-hint: "[PR number or URL]"
```
</example>

<example>
**Input**: `/generate-skill A comprehensive code review skill with security, performance, and accessibility checks`

**Output structure** (multi-file):
```
.claude/skills/code-review/
├── SKILL.md           (~200 lines) Main workflow
├── SECURITY.md        (~150 lines) Security check patterns
├── PERFORMANCE.md     (~120 lines) Performance anti-patterns
└── ACCESSIBILITY.md   (~100 lines) A11y checklist
```

Frontmatter:
```yaml
name: code-review
description: >
  Comprehensive code review covering security vulnerabilities, performance
  anti-patterns, and accessibility compliance. Produces a structured report
  with severity ratings. Use when reviewing code, PRs, or when user says
  "review code", "security check", "audit this".
allowed-tools: Read, Grep, Glob, LSP
argument-hint: "[file path, directory, or PR number]"
```
</example>
