# Codex Cross-Model Integration

Instructions for using OpenAI Codex as an independent evaluator/reviewer in the auto-resolve pipeline. Only read this file when `--with-codex` is enabled.

Codex is accessed via `mcp__codex-cli__*` MCP tools (provided by codex-mcp-server). This creates a GAN-like adversarial dynamic — Claude builds and Codex critiques, reducing shared blind spots between model families.

---

## PRE-FLIGHT CHECK

Before starting the pipeline, verify the Codex MCP server is available by calling `mcp__codex-cli__ping`.

- **If ping succeeds**: continue normally.
- **If ping fails or `mcp__codex-cli__ping` tool is not found**: warn the user and ask how to proceed:
  ```
  ⚠ Codex MCP server not detected. --with-codex requires codex-mcp-server.

  To install:
    npm i -g @openai/codex
    claude mcp add codex-cli -- npx -y codex-mcp-server

  Options:
    [1] Continue without --with-codex (Claude-only evaluation/review)
    [2] Abort pipeline
  ```
  If the user chooses [1], disable `--with-codex` and continue. If [2], stop.

---

## PHASE 2-CODEX: CROSS-MODEL EVALUATE

Run after the Claude evaluator (Phase 2) completes, only if `--with-codex` includes `evaluate` or `both`.

### Step 1 — Get Codex's evaluation

Call `mcp__codex-cli__codex` with:
- `prompt`: Include the full content of `.claude/done-criteria.md` and the output of `git diff HEAD~1`. Ask Codex to evaluate the changes against the done criteria and report issues by severity (CRITICAL, HIGH, MEDIUM, LOW) with file:line references.
- `workingDirectory`: the project root
- `sandbox`: `"read-only"` (Codex should only read, not modify files)
- `reasoningEffort`: `"high"`

Example prompt to pass:
```
You are an independent code evaluator. Grade the following code changes against the done criteria below. Be strict — when in doubt, flag it.

## Done Criteria
[paste contents of .claude/done-criteria.md]

## Code Changes
[paste output of git diff HEAD~1]

For each criterion, mark VERIFIED (with evidence) or FAILED (with file:line and what's wrong).
Then list all issues found grouped by severity: CRITICAL, HIGH, MEDIUM, LOW.
For each issue provide: file:line, description, and suggested fix.
End with a verdict: PASS, PASS WITH ISSUES, NEEDS WORK, or BLOCKED.
```

### Step 2 — Merge findings

Spawn a subagent using the Agent tool with `mode: "bypassPermissions"` to merge Claude's and Codex's evaluations.

Agent prompt:

Read `.claude/EVAL-FINDINGS.md` (Claude's evaluation) and the Codex evaluation output below. Merge them into a single unified `.claude/EVAL-FINDINGS.md` following the existing format. Rules:
- Take the MORE SEVERE verdict between the two evaluators
- Deduplicate findings that reference the same file:line or describe the same issue
- When both evaluators flag the same issue, keep the more detailed description
- Prefix Codex-only findings with `[codex]` so the fix loop knows the source
- Preserve the exact structure: Verdict, Done Criteria Results, Findings Requiring Action (CRITICAL/HIGH), Cross-Cutting Patterns

Codex evaluation:
[paste Codex's response here]

---

## PHASE 4B: CODEX REVIEW

Run after the Claude team review (Phase 4A) completes, only if `--with-codex` includes `review` or `both`.

### Step 1 — Run Codex review

Call `mcp__codex-cli__review` with:
- `base`: `"main"` — review all changes since main
- `workingDirectory`: the project root
- `title`: `"Cross-model review (Codex)"`

This runs OpenAI Codex's built-in code review against the diff. The review tool returns structured findings automatically — no custom prompt needed.

### Step 2 — Reconcile both reviews

Spawn a subagent using the Agent tool with `mode: "bypassPermissions"` to reconcile both reviews.

Agent prompt:

Two independent reviews have been conducted on recent changes — one by a Claude team review and one by OpenAI Codex. Reconcile them:

Claude team review findings: [paste Phase 4A agent's output summary]
Codex review findings: [paste mcp__codex-cli__review output]

1. Deduplicate findings that describe the same issue
2. For unique Codex findings not caught by Claude's team, prefix with `[codex]` and assess severity
3. Fix any CRITICAL issues directly. For HIGH issues, fix if straightforward.
4. Write a brief reconciliation summary to stdout listing: findings from both (agreed), Claude-only, Codex-only, and what was fixed
