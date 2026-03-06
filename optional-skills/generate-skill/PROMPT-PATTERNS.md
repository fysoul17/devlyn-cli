# Prompt Patterns for Claude 4.6 Skills

Patterns and anti-patterns for writing effective skill body content that works well with Claude 4.6 models.

## Table of Contents

- [Core Principles](#core-principles)
- [Structural Patterns](#structural-patterns)
- [Anti-Patterns](#anti-patterns)
- [Anti-Hallucination Patterns](#anti-hallucination-patterns)
- [Degree of Freedom Guide](#degree-of-freedom-guide)

---

## Core Principles

### 1. Be Explicit

Claude 4.6 follows instructions precisely. Vague prompts get literal interpretations.

```markdown
# Bad — vague
Review the code and fix issues.

# Good — explicit
Review the code for:
1. Security vulnerabilities (SQL injection, XSS, command injection)
2. Performance anti-patterns (N+1 queries, unnecessary re-renders)
3. Missing error handling

For each issue found, output:
- File and line number
- Severity (critical/warning/info)
- Description of the issue
- Suggested fix with code snippet
```

### 2. Provide WHY Context

Claude generalizes better when it understands the reasoning behind instructions.

```markdown
# Bad — no context
Always use `const` instead of `let`.

# Good — with WHY
Use `const` by default because it signals immutability to other developers
and prevents accidental reassignment. Only use `let` when the variable
must be reassigned within its scope.
```

### 3. Use XML Tags for Structure

XML tags create clear semantic boundaries. Use them for complex sections.

```markdown
<rules>
- Never modify files outside the project directory
- Always create a backup before destructive operations
- Ask for confirmation before deleting more than 3 files
</rules>

<output-format>
## Review Report
- **File**: {path}
- **Issues**: {count}
- **Severity**: {critical|warning|info}
</output-format>

<example>
Input: `/review src/auth.ts`
Output: Review report with 3 issues found...
</example>
```

### 4. Avoid "Think"

When extended thinking is disabled, "think" can cause confusion. Use alternatives:

| Instead of | Use |
|---|---|
| "Think about..." | "Consider..." |
| "Think through..." | "Evaluate..." |
| "Think step by step" | "Work through each step" |
| "Let me think" | "Let me analyze" |

---

## Structural Patterns

### Pattern 1: Workflow (Most Common)

Sequential steps with clear entry/exit criteria. Best for medium-freedom skills.

```markdown
## Workflow

### Step 1: Parse Input
Extract the target from `$ARGUMENTS`.
If empty, ask the user for the target.

### Step 2: Analyze
Read the target file(s) and identify {specific things}.

### Step 3: Generate Output
Produce {specific output format}.

### Step 4: Validate
Verify the output meets {specific criteria}.
```

**When to use**: Most skills. Provides clear structure while allowing flexibility within steps.

### Pattern 2: Template (Fill-in-the-Blanks)

Fixed output structure with variable content. Best for low-freedom skills.

```markdown
## Output Template

Generate the following file:

\```yaml
name: {extracted-name}
version: {detected-version}
dependencies:
  {for each dependency}
  - name: {dep-name}
    version: {dep-version}
  {end for}
\```

Rules:
- `name` must be lowercase with hyphens
- `version` must follow semver (x.y.z)
- Dependencies sorted alphabetically
```

**When to use**: Config generation, scaffolding, report generation.

### Pattern 3: Decision Tree

Branching logic based on input analysis. Best for skills that adapt behavior.

```markdown
## Decision Logic

Analyze the input and follow the appropriate path:

### Path A: Single File
If `$ARGUMENTS` points to a single file:
1. Read the file
2. Analyze for {criteria}
3. Output inline suggestions

### Path B: Directory
If `$ARGUMENTS` points to a directory:
1. Glob for relevant files (`**/*.{ts,tsx}`)
2. Analyze each file
3. Output a summary report

### Path C: No Input
If `$ARGUMENTS` is empty:
1. Detect the project type from package.json / pyproject.toml
2. Find the most relevant files
3. Follow Path A or Path B based on results
```

**When to use**: Skills that handle multiple input types or contexts.

### Pattern 4: Conditional Workflow

Workflow with conditional steps based on context. Combines workflow + decision tree.

```markdown
## Workflow

### Step 1: Detect Context
Read the project structure and determine:
- Language (TypeScript, Python, Go, etc.)
- Framework (Next.js, FastAPI, etc.)
- Test runner (Jest, Pytest, etc.)

### Step 2: Analyze (language-specific)

**If TypeScript/JavaScript:**
- Check for type errors with LSP
- Scan for common JS anti-patterns

**If Python:**
- Check for type hints
- Scan for common Python anti-patterns

### Step 3: Report
Output findings in a unified format regardless of language.
```

**When to use**: Skills that work across different project types.

### Pattern 5: Examples-Driven

Heavy use of examples to specify behavior. Best for high-freedom skills.

```markdown
## Behavior

Generate code following these examples exactly:

<example>
Input: "a function that fetches user data"
Output:
\```typescript
async function fetchUserData(userId: string): Promise<User> {
  const response = await fetch(`/api/users/${userId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch user ${userId}: ${response.statusText}`);
  }
  return response.json();
}
\```
</example>

<example>
Input: "a React hook for local storage"
Output:
\```typescript
function useLocalStorage<T>(key: string, initialValue: T) {
  const [value, setValue] = useState<T>(() => {
    const stored = localStorage.getItem(key);
    return stored ? JSON.parse(stored) : initialValue;
  });
  // ...
}
\```
</example>

Key patterns shown in examples:
- Always include error handling
- Use TypeScript generics where appropriate
- Async functions return typed Promises
```

**When to use**: Code generation, formatting, transformation skills.

---

## Anti-Patterns

Common mistakes when writing Claude 4.6 skills:

| Anti-Pattern | Problem | Fix |
|---|---|---|
| Over-triggering | Description matches too many scenarios | Add specific trigger phrases: `"Use when user says X, Y, Z"` |
| Aggressive language | "You MUST", "NEVER EVER", "ABSOLUTELY" | Use calm, clear directives: "Always X", "Do not Y" |
| Vague triggers | "Use when helpful" | Specific: "Use when reviewing TypeScript code for security" |
| Wall of text | No structure, no headings | Break into steps with `###` headings |
| Conflicting rules | "Be concise" + "Include all details" | Prioritize: "Be concise. Include details only for critical issues." |
| No examples | Claude guesses at desired output | Add 1-2 concrete `<example>` blocks |
| Unbounded scope | "Analyze everything" | Limit: "Analyze files in `src/` matching `*.ts`" |
| Silent failures | No error handling instructions | Add: "When X fails, display the error and suggest next steps" |

### Over-Triggering Fix

```markdown
# Bad — triggers on any code question
description: Helps with code. Use for any coding task.

# Good — specific triggers
description: >
  Generate unit tests for TypeScript functions using Jest.
  Use when user says "generate tests", "add tests", "write tests for",
  or when reviewing untested code.
```

### Scope Bounding

```markdown
# Bad — unbounded
Analyze the entire codebase for issues.

# Good — bounded
Analyze files matching `$ARGUMENTS` (default: `src/**/*.ts`).
Limit to 50 files maximum. If more files match, ask the user to narrow the scope.
```

---

## Anti-Hallucination Patterns

Prevent Claude from inventing information in skills:

### 1. Ground in File Content

```markdown
# Bad
Describe the project architecture.

# Good
Read `README.md`, `package.json`, and the `src/` directory structure.
Describe the architecture based ONLY on what these files contain.
Do not infer or assume features not present in the code.
```

### 2. Explicit Unknowns

```markdown
If you cannot determine {X} from the available files:
- State "Unable to determine {X} from the codebase"
- List what files you checked
- Suggest what the user could provide to resolve this
```

### 3. Verify Before Acting

```markdown
Before generating code:
1. Read the existing implementation in `$1`
2. Identify the patterns already used (naming, error handling, imports)
3. Generate code that matches these existing patterns
Do not introduce new patterns or dependencies without explicit instruction.
```

---

## Degree of Freedom Guide

How much latitude to give Claude based on skill type:

### High Freedom
The skill makes autonomous decisions. Requires strong guardrails.

```markdown
## Guardrails
- Do NOT modify files outside `$ARGUMENTS` path
- Do NOT add new dependencies without asking
- Do NOT delete existing code without replacement
- Maximum 200 lines of generated code per invocation
- Always show a diff preview before applying changes
```

**Examples**: code generation, refactoring, migration skills

### Medium Freedom
The skill follows a workflow but adapts to context. Requires clear decision criteria.

```markdown
## Decision Criteria
- If the file has fewer than 50 lines: inline review
- If the file has 50-500 lines: section-by-section review
- If the file has more than 500 lines: focus on public API and entry points only
```

**Examples**: review, analysis, documentation skills

### Low Freedom
The skill executes a fixed procedure. Requires exact input/output specs.

```markdown
## Input
- `$1`: PR number (required, integer)
- `$2`: Template name (optional, default: "standard")

## Output
A markdown report with exactly these sections:
1. Summary (1-2 sentences)
2. Checklist (pass/fail for each template requirement)
3. Missing Items (list of unfulfilled requirements)
```

**Examples**: validation, scanning, formatting skills
