# Codex Critic Prompt Template (Phase 3.5)

> Invocation flag set: `config/skills/_shared/codex-config.md`.

Used by `devlyn:ideate` when `--engine auto` or `--engine claude` (role reversal). Run `bash .claude/skills/_shared/codex-monitored.sh -C <project root> -s read-only -c model_reasoning_effort=xhigh "<packaged prompt>"` — the wrapper closes stdin and heartbeats every 30s on stderr; rationale in `_shared/codex-config.md`. Codex has no filesystem access under read-only — everything it needs travels in the prompt.

Assemble the prompt with these sections in this exact order, filling in placeholders:

```
## Problem framing (from FRAME phase)
[problem statement, constraints, success criteria, anti-goals]

## Confirmed facts vs assumptions
Confirmed by user: [list each fact the user explicitly confirmed]
Assumptions (not yet confirmed): [list each assumption the agent made]

## Plan (post-solo-CHALLENGE)
Vision: [one sentence]
Phase 1 ([theme]): [items with one-line descriptions and dependencies]
Phase 2 ([theme]): ...
Architecture decisions: [each with what / why / alternatives considered]
Deferred to backlog: [items + reason]

## Findings from the solo rubric pass
[list each with: severity, axis, quote, why, fix, whether applied]

## Rubric
[INLINE the full text of references/challenge-rubric.md here verbatim — Codex needs the rubric definition in the prompt itself]

## Your job
You are applying an independent rubric pass to the PLANNING document above. This is a roadmap, not code — judge the shape of the plan, not implementation details. The user explicitly asked to be challenged because soft-pedaled plans waste their time.

You are running AFTER a solo pass by Claude. Catch what the solo pass missed; do not just agree with what it already caught. For each existing solo finding, reply either "confirmed" (with one-line agreement) or "I would frame this differently" (with a reason). Then add your own findings that the solo pass missed.

Use the finding format from the rubric above: Severity / Quote / Axis / Why / Fix. The Quote field is load-bearing — anchor each finding to a specific line from the plan.

Respect explicit user intent. If the user confirmed something in the "Confirmed facts" section, the rubric does not override it silently. Raise the conflict as a note and let the orchestrator surface it to the user.

End with a verdict: PASS / PASS WITH MINOR FIXES / FAIL — REVISION REQUIRED, plus a one-line explanation.
```

## Why a separate file

Inlining the rubric and the boilerplate instructions into the orchestrator SKILL.md burned ~30 lines per load of the ideate skill. The critic packaging runs exactly once per session; the template only needs to be read at Phase 3.5 time. On-demand loading matches the progressive-disclosure pattern used across the devlyn harness.
