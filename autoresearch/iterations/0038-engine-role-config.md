# iter-0038 — engine role config: manual mode + benchmark engine-combination arms

**Status**: SHIPPED — R0 Go-with-changes; all 6 ship-list items adopted verbatim
(no deltas). R0 also surfaced a pre-existing contract split: SKILL.md allowed
skip reason `auto_pair_other_engine_unavailable` but state-schema.md's valid
skip-cause list omitted it — `verify-merge-findings.py` already accepted it, so
the schema DOC was the stale leg; reconciled doc-side. Q1 `.devlyn/engines.json`
cwd-only (no parent/global lookup); Q2 explicit routes fail closed through the
priority resolver, auto-only skips stay solo-skips; Q3 `BLOCKED:invalid-engine-config`
is report-level only, `engine` schema widened to adapter-valid names; Q4
`--engines-config` staged pre-baseline (test-repo gitignores `.devlyn`), verbatim
copy to `RESULT_DIR/engines-config.json` as evidence, existing arm launch
commands untouched.
**Trigger**: explicit user direction 2026-07-03 (follow-on to iter-0037). Verbatim
intent: auto-detection is good, but "내가 강제하고 싶을 때가 있잖아 수동모드" —
when the model landscape shifts (e.g. a stronger non-Claude frontier model ships),
the user must be able to PIN roles rather than rely on defaults. Plus: "벤치마크도
더 강력하게 제대로 돌릴 수 있도록" — the benchmark must be able to measure
engine COMBINATIONS, not only the hardcoded arm shapes.

## Problem (evidence)

1. Executor default is `claude`, overridable only per-run via `--engine`
   (SKILL.md PHASE 0). No durable pin: a user whose strongest installed model is
   Codex must remember the flag on every invocation, and the conversational
   handoff (iter-0037) would silently use the wrong default.
2. Pair-judge selection is the binary "OTHER engine" (claude↔codex). With a 3rd
   adapter (`glm`, pi-agent backends — installer already targets omp/Pi since
   v2.6.0), "OTHER" is undefined.
3. `run-fixture.sh` bakes `--engine claude` into arm names (`l2_gated`,
   `l2_risk_probes` — lines 65-77). Measuring executor=codex or any future
   combination requires editing the runner per combination — the reason
   cross-mix measurement (deferred memo 2026-04-26) never became runnable.

## Design

### D1 — `.devlyn/engines.json` (machine-local role pin; resolve consumes)

```json
{ "executor": "codex", "pair_judge_priority": ["claude", "glm"] }
```

- **Precedence**: explicit `--engine` flag > `engines.json.executor` > built-in
  default `claude`. Flags stay per-run overrides; the file is the durable pin.
- **executor** — engine for IMPLEMENT/CLEANUP (exactly what `--engine` sets
  today). Role-level, NOT per-phase: iter-0020 falsified per-phase matrices;
  phases move together.
- **pair_judge_priority** — ordered preference for the VERIFY pair-JUDGE /
  risk-probe OTHER engine. Selection: first entry that is (a) not the primary
  judge engine and (b) available. Absent key → today's binary OTHER-engine rule.
- **Fail-closed**: malformed JSON → `BLOCKED:invalid-engine-config`. Engine name
  with no `_shared/adapters/<name>.md` → `BLOCKED:invalid-engine-config` naming
  the missing adapter (this is how GLM/pi slots in later: ship adapter, name it
  here, zero skill-body changes). A pinned executor whose CLI is unavailable →
  `BLOCKED:<engine>-unavailable` (a pin is an explicit route/promise — same
  class as `--engine`; never silently downgrade).
- **Absent file → byte-identical today's behavior.**
- Not archived per-run (not in PER_RUN_PATTERNS); it is machine config, not run
  artifact. Not committed by convention (engine availability is per-machine).
- state provenance: `state.engine_source ∈ {"flag","engines.json","default"}` —
  one field so benchmark audit and BLOCKED reports show where the engine came
  from.

### D2 — Orchestrator role is a docs contract, not config

The orchestrator is whichever CLI the user opens (Claude Code → Claude family;
Codex CLI → GPT family). devlyn cannot and should not "set" it. The guarantee is
symmetry: CLAUDE.md and AGENTS.md carry the same handoff/loop/queue contract and
the same file artifacts (spec.md, queue.md, state.json), so switching
orchestrator = switching terminal, everything else carries over. Documented as a
3-role map in both files (orchestrator / executor / pair-judge).

### D3 — Benchmark: generic `--engines-config` arm input

`run-fixture.sh` gains optional `--engines-config '<json>'`: staged verbatim as
`.devlyn/engines.json` in the arm worktree before launch. Existing arm names and
their hardcoded flags stay untouched (frozen evidence contracts). New
combinations become runnable as `variant`-class arms + an engines-config value —
no new hardcoded arm per combination. This unblocks the deferred cross-mix
measurement memo without pre-registering any pair iter (headroom-first rule
still binds; this is capability, not a measurement claim).

## Addendum — `/devlyn:engines` utility (same day, explicit user direction)

User asked for a discoverable `/devlyn:xxxx` command to view/pin roles instead of
hand-editing JSON. Shipped `config/skills/devlyn:engines/SKILL.md` (status table
with detected engines + `executor <name>` / `pair <name>,...` / `clear`) and added
it to `DEVLYN_CORE_SKILLS`. NORTH-STAR's locked-surface rule allows deviation on
explicit user direction — cited here. No new Codex round: the skill is a pure
front-end over this iter's already-converged engines.json contract (it adds no
semantics; everything it writes is what PHASE 0 reads).

## Rejected

- Per-phase engine map in config — falsified surface (iter-0020); role-level only.
- Committing engines.json to the repo — availability is per-machine; a committed
  pin breaks teammates without that CLI.
- Auto-detecting "strongest" model — capability ranking changes monthly and is
  not observable locally; pinning is the user's judgment, detection stays
  availability-only.
- New arm names per combination in run-fixture.sh — combinatorial growth; the
  config input replaces it.

## Freeze/benchmark safety

- No behavior change when engines.json absent and no new flag passed (P1).
- Existing arms produce byte-identical launch commands (P2).
- `scripts/lint-skills.sh` passes; 3 mirrors synced (P3).

## Open questions for Codex R0

- Q1: engines.json location `.devlyn/` vs repo root — `.devlyn/` is
  gitignored-by-convention and machine-local (intended), but a fresh clone loses
  the pin. Is machine-local the right call?
- Q2: should `pair_judge_priority` interact with the explicit `--pair-verify`
  promise (pin unavailable → BLOCKED) the same way as executor pins?
- Q3: `BLOCKED:invalid-engine-config` — new report-level reason string; any
  carrier/schema conflict with the bare-enum `phases.*.verdict` rule?
- Q4: any hole in D3 that lets an engines-config arm contaminate frozen-evidence
  arm results (shared caches, mirrored skills, result dirs)?
