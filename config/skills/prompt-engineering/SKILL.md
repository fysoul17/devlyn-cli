---
name: prompt-engineering
description: Claude 4 prompt optimization for creating, reviewing, or refining prompts. Applies official Anthropic best practices for explicit instructions, context framing, format control, and model-specific tuning. Proactively use this skill when writing system prompts, agent instructions, skill definitions, or meta-prompting.
allowed-tools: Read, Grep, Glob, Edit, Write
---

<!--
  Version: 2026-01 | Claude 4.x (Opus 4.5, Sonnet 4.5, Haiku 4.5)
  Source: https://platform.claude.com/docs/build-with-claude/prompt-engineering/claude-4-best-practices
-->

# Prompt Engineering for Claude 4

Claude 4 models follow instructions precisely. Vague prompts get literal interpretations. Apply these patterns.

## Core Principles

1. **Be explicit** - Claude does exactly what you ask, not what you might mean
2. **Add context** - Explain WHY, not just WHAT (Claude generalizes from reasoning)
3. **Match examples to intent** - Claude treats examples as specifications
4. **Use XML tags** - Structure complex instructions with semantic tags
5. **Avoid "think"** - Use "consider", "evaluate", "analyze" instead (when thinking is disabled)

---

## Decision Tree 1: Writing Instructions

```
START: Writing an instruction
    │
    ├─► Is the desired behavior obvious?
    │       NO → Add explicit detail
    │       Example: "Create a dashboard" → "Create a dashboard with charts,
    │                filters, and export functionality. Go beyond basics."
    │
    ├─► Could Claude interpret this literally in an unhelpful way?
    │       YES → Add context explaining WHY
    │       Example: "NEVER use ellipses" → "Never use ellipses because
    │                text-to-speech can't pronounce them."
    │
    └─► Do I want Claude to be proactive or conservative?
            PROACTIVE → "Implement changes rather than suggesting them"
            CONSERVATIVE → "Default to recommendations; only act when explicitly asked"
```

### Correct: Explicit with Context

```text
<default_to_action>
Implement changes rather than suggesting them. If intent is unclear, infer the
most useful action and proceed. Use tools to discover missing details instead of guessing.
</default_to_action>
```

### Wrong: Vague Instructions

```text
Help me with the code.
```

---

## Decision Tree 2: Format Control

```
START: Controlling output format
    │
    ├─► Want prose instead of markdown?
    │       → "Write in smoothly flowing prose paragraphs."
    │       → Wrap content in <prose> tags
    │
    ├─► Want to minimize bullet points?
    │       → "Incorporate items naturally into sentences.
    │          Avoid ordered/unordered lists unless truly discrete items."
    │
    ├─► Want structured data?
    │       → Use XML tags: "Write in <response_format> tags"
    │       → Specify JSON schema explicitly
    │
    └─► Output still wrong?
            → Match your PROMPT style to desired OUTPUT style
            → Remove markdown from prompt if you don't want markdown output
```

### Pattern: Minimize Markdown

```text
<avoid_excessive_markdown>
Write in clear, flowing prose using complete paragraphs. Reserve markdown for:
- `inline code` and code blocks
- Simple headings (##, ###)

DO NOT use bullets/numbered lists unless presenting truly discrete items or
explicitly requested. Incorporate information naturally into sentences.
</avoid_excessive_markdown>
```

---

## Decision Tree 3: Model Selection

```
START: Which Claude model?
    │
    ├─► Complex reasoning, multi-step analysis, or highest quality?
    │       → Opus 4.5 (claude-opus-4-5-20250929)
    │
    ├─► Balance of quality, speed, and cost?
    │       → Sonnet 4.5 (claude-sonnet-4-5-20250929)
    │
    └─► Fast responses, simple tasks, cost-sensitive?
            → Haiku 4.5 (claude-haiku-4-5-20250929)
```

---

## Decision Tree 4: Tool Usage

```
START: Claude needs to use tools
    │
    ├─► Want Claude to be proactive with tools?
    │       → "Use tools to discover details instead of asking."
    │
    ├─► Want Claude to parallelize?
    │       → "If calls are independent, make them in parallel."
    │
    ├─► Claude over-triggering on tools?
    │       → Remove aggressive language ("MUST", "CRITICAL", "ALWAYS")
    │       → Use natural phrasing: "Use this tool when..."
    │
    └─► Claude under-triggering?
            → Be more specific about trigger conditions
            → Add "Default to using X tool for Y tasks"
```

### Pattern: Parallel Tool Usage

```text
<parallel_tool_calls>
If multiple tool calls have no dependencies, make them in parallel. When reading
3 files, run 3 tool calls simultaneously. However, if calls depend on previous
results, execute sequentially. Never use placeholders for missing parameters.
</parallel_tool_calls>
```

---

## Anti-Patterns (Claude 4 Specific)

| Anti-Pattern | Why It Fails | Fix |
|--------------|--------------|-----|
| "Can you suggest changes?" | Claude will only suggest, not implement | "Change this function to..." |
| "Think about this carefully" | Triggers thinking sensitivity | "Consider this carefully" |
| "CRITICAL: You MUST..." | Opus 4.5 may over-trigger | "Use this when..." |
| Vague instructions | Literal interpretation | Add explicit detail |
| No context for rules | Claude can't generalize | Explain WHY behind rules |
| Examples with unwanted patterns | Claude mimics examples precisely | Remove unwanted behaviors from examples |

---

## Prompt Templates

### System Prompt: Proactive Agent

```text
<agent_behavior>
Default to implementing changes rather than suggesting them. When intent is unclear,
infer the most useful action and proceed using tools to discover missing details.
</agent_behavior>

<code_exploration>
Always read and understand relevant files before proposing edits. Do not speculate
about code you have not inspected. Be rigorous in searching for key facts.
</code_exploration>

<output_style>
Provide concise, direct updates. Skip verbose summaries unless asked. After tool
use, briefly state what was done and proceed to the next action.
</output_style>
```

### System Prompt: Conservative Agent

```text
<conservative_mode>
Do not implement changes unless explicitly instructed. Default to providing
information, research, and recommendations. Only proceed with modifications
when the user explicitly requests them.
</conservative_mode>
```

### System Prompt: Long-Running Tasks

```text
<context_management>
Your context window will be compacted automatically. Do not stop tasks early due
to token budget. Save progress to files before context refreshes. Be as persistent
and autonomous as possible.
</context_management>

<state_tracking>
Use structured formats (JSON) for tracking test results and task status.
Use unstructured text for progress notes.
Use git for checkpoints that can be restored.
Focus on incremental progress.
</state_tracking>
```

---

## Reducing Over-Engineering

Claude 4 can over-engineer. Counter with:

```text
<minimal_solutions>
Only make changes directly requested. Keep solutions simple and focused.

- Don't add features beyond what was asked
- Don't refactor surrounding code during bug fixes
- Don't add error handling for impossible scenarios
- Don't create abstractions for one-time operations
- Don't design for hypothetical future requirements

The right complexity is the minimum needed for the current task.
</minimal_solutions>
```

---

## Quick Reference

| Goal | Prompt Pattern |
|------|----------------|
| More detail | "Include as many features as possible. Go beyond basics." |
| Less markdown | "Write in flowing prose. Avoid bullet lists." |
| Proactive | "Implement rather than suggest. Infer intent and proceed." |
| Conservative | "Only act when explicitly asked. Default to recommendations." |
| Parallel tools | "Make independent tool calls in parallel." |
| Code exploration | "Always read files before proposing changes." |
| Less verbose | "Skip summaries. Provide direct, concise updates." |
| More verbose | "After tool use, provide a summary of work done." |
