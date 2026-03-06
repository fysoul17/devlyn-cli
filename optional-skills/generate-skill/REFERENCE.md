# Frontmatter Field Reference

Complete catalog of YAML frontmatter fields for Claude Code skill files (`SKILL.md`).

## Table of Contents

- [Required Fields](#required-fields)
- [Optional Fields](#optional-fields)
- [String Substitutions](#string-substitutions)
- [Tool Presets](#tool-presets)
- [Naming Rules](#naming-rules)

---

## Required Fields

| Field | Type | Max Length | Description |
|---|---|---|---|
| `name` | string | 64 chars | Unique skill identifier. Lowercase, hyphens, digits only. |
| `description` | string | 1024 chars | What the skill does and when to trigger it. Third-person voice. |

### `name` Validation

- Lowercase letters, hyphens, and digits only: `[a-z0-9-]+`
- Max 64 characters
- Must NOT contain: `anthropic`, `claude`, `official`
- Must NOT start or end with a hyphen
- Must be unique within the project's skill directory

### `description` Best Practices

- Write in **third-person**: "Validates PR descriptions..." not "I validate..."
- Include **trigger phrases** so Claude knows when to activate:
  - Good: `Use when user says "check PR", "validate PR", "review description".`
  - Bad: `A helpful skill for PRs.`
- No XML tags in the description (they break YAML parsing)
- First sentence = what it does. Second sentence = when to use it.

---

## Optional Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `allowed-tools` | string (CSV) | all tools | Comma-separated list of tools the skill can use |
| `argument-hint` | string | none | Placeholder shown to user (e.g., `"[file path]"`) |
| `user-invocable` | boolean | `true` | Whether users can trigger via `/skill-name` |
| `disable-model-invocation` | boolean | `false` | If `true`, Claude cannot proactively trigger the skill |
| `context` | list | none | Files to inject into context when skill activates |
| `agent` | object | none | Run skill as a subagent with its own context |
| `model` | string | inherited | Override model (`opus`, `sonnet`, `haiku`) |
| `hooks` | object | none | Shell commands to run on skill lifecycle events |

### `allowed-tools` Details

Specify the minimal set of tools needed. Format: comma-separated tool names.

For Bash, use glob patterns to restrict commands:
```yaml
allowed-tools: Read, Bash(npm test *), Bash(npx *)
```

Wildcard `*` matches any arguments. Without a glob, Bash runs any command.

### `context` Field

Inject files into the skill's context automatically:

```yaml
context:
  - type: file
    path: ${CLAUDE_SKILL_DIR}/PATTERNS.md
  - type: file
    path: ./CLAUDE.md
```

Use `${CLAUDE_SKILL_DIR}` for paths relative to the skill directory.

### `agent` Field

Run the skill as an isolated subagent:

```yaml
agent:
  type: general-purpose
  model: sonnet
```

Agent types: `general-purpose`, `Explore`, `Plan`, `haiku`.

### `hooks` Field

Run shell commands on skill events:

```yaml
hooks:
  pre-invoke: "echo 'Starting skill...'"
  post-invoke: "echo 'Skill complete.'"
```

---

## String Substitutions

These placeholders are replaced at runtime:

| Placeholder | Replaced With |
|---|---|
| `$ARGUMENTS` | Full argument string passed to the skill |
| `$1`, `$2`, ... `$N` | Positional arguments (space-separated) |
| `${CLAUDE_SESSION_ID}` | Current session identifier |
| `${CLAUDE_SKILL_DIR}` | Absolute path to the skill's directory |

### Usage Examples

```markdown
Parse `$ARGUMENTS` for the file path.
If `$1` is empty, ask the user for a target file.
Read the config from `${CLAUDE_SKILL_DIR}/config.yaml`.
```

---

## Tool Presets

Common tool combinations by skill type:

### Read-Only (analysis, scanning, review)
```yaml
allowed-tools: Read, Grep, Glob
```

### Read-Only + LSP (code intelligence)
```yaml
allowed-tools: Read, Grep, Glob, LSP
```

### Code Modification (generation, refactoring)
```yaml
allowed-tools: Read, Grep, Glob, Edit, Write
```

### Full Access (build, test, deploy)
```yaml
allowed-tools: Read, Grep, Glob, Edit, Write, Bash
```

### Web Access (API calls, fetching docs)
```yaml
allowed-tools: Read, Grep, Glob, WebFetch, WebSearch
```

### Restricted Bash (specific commands only)
```yaml
allowed-tools: Read, Grep, Glob, Bash(npm test *), Bash(npx prettier *)
```

### Agent-Spawning (team coordination)
```yaml
allowed-tools: Read, Grep, Glob, Edit, Write, Bash, Agent
```

---

## Naming Rules

### Skill Name (`name` field)

| Rule | Good | Bad |
|---|---|---|
| Lowercase + hyphens | `validate-pr` | `ValidatePR`, `validate_pr` |
| Descriptive action | `generate-tests` | `tests`, `t` |
| No reserved words | `code-review` | `claude-review`, `anthropic-scan` |
| Max 64 chars | `validate-pr-description` | (anything over 64 chars) |

### File Naming

| File | Convention |
|---|---|
| Main skill file | Always `SKILL.md` |
| Reference files | `UPPERCASE-WORDS.md` (e.g., `PATTERNS.md`, `REFERENCE.md`) |
| Skill directory | Same as `name` field (e.g., `validate-pr/`) |

### Description Formatting

```yaml
# Good — third person, trigger phrases, clear purpose
description: >
  Validate pull request descriptions against a project template.
  Checks for required sections and formatting completeness.
  Use when reviewing PRs or when user says "check PR", "validate PR".

# Bad — first person, no triggers, vague
description: "I help with PRs"
```
