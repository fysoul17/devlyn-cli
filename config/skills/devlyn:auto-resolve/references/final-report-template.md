# PHASE 5 Final Report — Required Shape

Render the report exactly in this order. Fields enclosed in `<…>` come from `pipeline.state.json`. The banner line is printed only under exhaustion (`⚠ BUILD GATE EXHAUSTED`, `⚠ BROWSER EXHAUSTED`, `⚠ EVAL EXHAUSTED — open findings: <list file:line>`, `⚠ CRITIC EXHAUSTED`).

The engine line follows the shared contract (`config/skills/_shared/engine-preflight.md`) — when a downgrade happened, include the parenthetical `(downgraded from <requested> — codex-unavailable)`. Otherwise print the effective engine only.

```
### Auto-Resolve Complete — run <run_id>

Task: <original task>
Engine: <engine> (downgraded: <reason or no>)
Route: <selected> (user_override: <t/f>)
  Stage A: <reasons>
  Stage B LITE: <no escalation | escalated from X — reason>

Terminal verdict: <PASS / PASS_WITH_ISSUES / NEEDS_WORK / BLOCKED>
<banner if applicable>

Pipeline summary:
| Phase | Verdict | Notes |
|-------|---------|-------|
| BUILD | <v> | <engine, solo/team> |
| BUILD GATE | <v> | <project types, commands> |
| BROWSER | <v / skipped — no web> | <tier, flow> |
| EVAL (round <N>) | <v> | <finding count by severity> |
| FIX ROUNDS | <N of max> | <triggered_by history> |
| CRITIC | <v / skipped-route / skipped-bypass> | <design: N, security: N, dep-audit: ran/skipped> |
| DOCS | <completed / skipped> | <specs flipped, roadmap archived> |

Guardrails bypassed: <state.route.bypasses or "none">

Commits: <git log --oneline from state.base_ref.sha>

Audit trail: .devlyn/runs/<run_id>/

Next steps:
- Review: git diff <base_ref.sha>
- Squash: git rebase -i <base_ref.sha>
- Re-run fixes: /devlyn:auto-resolve "<narrower task>"
```
