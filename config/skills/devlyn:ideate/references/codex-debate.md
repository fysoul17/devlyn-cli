# Codex Cross-Model Rubric Pass

## Contents
- Pre-flight check (verify Codex MCP server availability)
- PHASE 3.5-CODEX: packaging the plan, calling Codex, reconciling findings with the solo pass
- Cost notes (one Codex call per ideation session)

Instructions for using OpenAI Codex as an independent critic during Phase 3.5 CHALLENGE. Only read this file when `--with-codex` is set. The 5-axis rubric itself lives in `challenge-rubric.md` — Claude loads that file directly from SKILL.md, not via this file.

Codex is accessed via `mcp__codex-cli__*` MCP tools (provided by codex-mcp-server). The intent: one opinionated rubric pass from a different model family, applied right before the user sees the plan. Two model families catch different blind spots; one pass at maximum effort catches more than multiple shallow passes.

**Always use `reasoningEffort: "xhigh"` and `sandbox: "read-only"` for every Codex call in this file.** Maximum reasoning is the whole reason the `--with-codex` flag exists — lowering it defeats the purpose of bringing in a second model.

---

## PRE-FLIGHT CHECK

Before starting the pipeline, verify the Codex MCP server is available by calling `mcp__codex-cli__ping`.

- **If ping succeeds**: continue.
- **If ping fails or `mcp__codex-cli__ping` is not found**: warn the user and ask:
  ```
  ⚠ Codex MCP server not detected. --with-codex requires codex-mcp-server.

  To install:
    npm i -g @openai/codex
    claude mcp add codex-cli -- npx -y codex-mcp-server

  Options:
    [1] Continue without --with-codex (Claude-only solo CHALLENGE pass)
    [2] Abort
  ```
  If [1], disable `--with-codex` and continue with the solo CHALLENGE. If [2], stop.

---

## PHASE 3.5-CODEX: Codex rubric pass

Run after the solo CHALLENGE pass completes, before the user-facing summary.

### Step 1 — Package the post-solo plan

Use the plan as it stands after the solo rubric pass. Package the full context Codex needs:

```
## Problem framing (from FRAME phase)
[problem statement, constraints, success criteria, anti-goals]

## Confirmed facts vs assumptions
Confirmed by user: [list]
Assumptions (not yet confirmed): [list]

## Plan (post-solo-CHALLENGE)
Vision: [one sentence]
Phase 1 ([theme]): [items, dependencies, one-line descriptions]
Phase 2 ([theme]): ...
Architecture decisions: [each with what / why / alternatives]
Deferred to backlog: [items + reason]

## Findings from the solo rubric pass
[list each with: axis, quote, why, fix, whether applied]
```

Include the framing and assumptions — Codex can only judge whether the plan fits the user's reality if it sees what the user actually said.

### Step 2 — Codex challenge pass

Call `mcp__codex-cli__codex` with:
- `prompt`: the packaged context above, followed by the instructions below
- `workingDirectory`: the project root
- `sandbox`: `"read-only"`
- `reasoningEffort`: `"xhigh"` — the highest setting in the Codex enum (`none < minimal < low < medium < high < xhigh`). Always pick the top level; this is the entire reason for the flag.

Instructions to append to the packaged context. **Before sending, inline the full text of `references/challenge-rubric.md` into the prompt under a `## Rubric` heading** — Codex does not have filesystem access to this project, so Claude must ship the rubric itself. Claude already has the rubric loaded from Phase 3.5 setup.

Template for the appended instructions:

```
You are applying an independent rubric pass to the PLANNING document above. This is a roadmap, not code — judge the shape of the plan, not implementation details. The user has explicitly asked to be challenged because soft-pedaled plans waste their time.

## Rubric
[Claude inlines the full text of references/challenge-rubric.md here]

## Your job
- You are running AFTER a solo pass by Claude. Catch what the solo pass missed, do not just agree with what it already caught. For each existing solo finding, reply either "confirmed" or "I would frame this differently" with a reason. Then add your own findings that the solo pass missed.
- Use the finding format from the rubric above: Severity / Quote / Axis / Why / Fix. The Quote field is load-bearing — anchor each finding to a specific line from the plan.
- Respect explicit user intent. If the user confirmed something in the "Confirmed facts" section, the rubric does not override it silently. Raise the conflict as a note and let Claude surface it to the user.

End with a verdict: PASS / PASS WITH MINOR FIXES / FAIL — REVISION REQUIRED, and a one-line explanation.
```

### Step 3 — Reconcile solo and Codex findings

Merge the two finding lists:
- Same finding from both → keep the more specific wording, mark "confirmed by both".
- Codex-only → prefix `[codex]` in internal notes so the user-facing summary can show where each push came from.
- Solo-only → keep as-is.
- Conflicts (solo says X, Codex says not-X) → record both, do not silently pick one; if the conflict is material, include it as an open question in the user-facing summary.

If Codex raised CRITICAL or HIGH findings that the solo pass missed, apply the fixes to the plan before presenting the user-facing summary. If fixing would change something the user explicitly asked for, follow the "Respect explicit user intent" rule already loaded from the rubric: do not silently rewrite — surface it.

Do not loop. One Codex pass is enough. If the result is still FAIL after one pass, that is signal that the plan has structural problems the user should see directly, not signal to keep iterating in the background.

---

## Cost notes

- One Codex call at `reasoningEffort: "xhigh"` typically takes 30–90s and is not cheap. This integration is bounded: exactly one Codex call per ideation session.
- In Quick Add mode on a single new item, one Codex call is still worth it — small scope, huge signal, and single-item additions are exactly where workarounds slip in unnoticed.
