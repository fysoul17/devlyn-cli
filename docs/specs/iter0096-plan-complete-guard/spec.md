---
complexity: medium
---

# iter-0096 — SPW CLI guard: standalone `plan complete` with a continuing verdict fails closed

Adjudicated at the iter-0096 R0 round (2026-08-05, receipts
`~/.local/share/nx01/iter0096-reg/`; registration
`autoresearch/iterations/0096-transition-compliance-delivery-regate.md`
§ R0 adjudication). Motivating live failure: DECISIONS 0095.1 — a Sonnet
parent completed PLAN via standalone
`state-phase-write.py --phase plan complete --verdict PASS`, leaving
`phases.implement = null` at `plan.completed_at` (atomic-carrier
violation the watcher fail-closes on). A PLAN PASS always opens a next
phase; standalone completion is only legal for halts.

## Requirements

### R1 — CLI-layer guard in `config/skills/_shared/state-phase-write.py`

At the EFFECTIVE-VERDICT site of the `complete` verb for `--phase plan`
[Outer-loop amendment 2026-08-05 after R1 Codex EFFECTIVE-VERDICT
CONSERVATION delta]: a supplied `PASS`/`PASS_WITH_ISSUES` that REMAINS
the effective verdict (i.e. is not converted to terminal `BLOCKED` by
the writer's attestation-failure conversion, `:1453-1475` region) exits
nonzero with an error naming the `transition` verb, WITHOUT writing
state (pre/post bytes identical). A supplied PASS that the attestation
check converts to `BLOCKED` remains a LEGAL standalone completion and
writes normally. `do_complete` unit paths stay valid; the CLI-only
rejection moves only as far inward as needed to see the effective
verdict. ADD self-test case: supplied PASS + failing attestation →
BLOCKED written (legal), plus the existing guard cases unchanged. `BLOCKED`, `FAIL`,
`NEEDS_WORK`, and all non-plan phases are untouched. Three-way mirrors
(`.agents`, `.claude`) synced in the same commit.

### R2 — co-land fixture rewrites (replay-parity, F2)

1. SPW in-file self-test: the `plan_cli(... complete PASS ...)` fixture
   (~`:1659` region) is rewritten through the `transition` verb (or a
   halt verdict where the case's intent is a halt); ADD guard cases:
   plan+PASS standalone → nonzero exit, transition-directed error,
   state file bytes unchanged; plan+PASS_WITH_ISSUES standalone → same;
   plan+BLOCKED standalone → legal; plan transition PASS→implement →
   legal (existing).
2. `benchmark/ceiling/scripts/plan-dispatch-oracle.py` e2e block
   (~`:2555-2562` region): its standalone plan-complete-PASS invocation
   is rewritten through `transition` (preserving the e2e assertions'
   intent); the oracle self-test stays green.

## Out of scope

- No changes to `do_complete` internals, `transition` semantics,
  LEGAL_TRANSITIONS, other verbs, or any other phase's completion rules.
- No SKILL.md prose changes (guard-only per adjudication).
- No watcher/scorer changes (F4 ruling lives in the registration).

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {
      "cmd": "python3 config/skills/_shared/state-phase-write.py --self-test",
      "exit_code": 0,
      "timeout_sec": 120
    },
    {
      "cmd": "python3 benchmark/ceiling/scripts/plan-dispatch-oracle.py --self-test",
      "stdout_contains": ["SELFTEST PASS"],
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "diff -q config/skills/_shared/state-phase-write.py .agents/skills/_shared/state-phase-write.py && diff -q config/skills/_shared/state-phase-write.py .claude/skills/_shared/state-phase-write.py",
      "exit_code": 0
    },
    {
      "cmd": "bash scripts/lint-skills.sh",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "git diff --check",
      "exit_code": 0
    }
  ],
  "max_deps_added": 0
}
```
