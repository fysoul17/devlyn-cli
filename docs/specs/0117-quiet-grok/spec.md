---
id: "0117-quiet-grok"
title: "Detect observed Grok review processes before quiet collection"
kind: bugfix
status: planned
complexity: medium
depends_on: []
---

# Detect observed Grok review processes before quiet collection

## Context

Both quiet-process predicates miss the absolute-path versioned Grok executable with `--prompt-file`. [Corrected red evidence](../../../.devlyn/0117/red-v2.json) attests sealed argv and owned live process rows, then replays the binary row: drain returns no reasons and runner returns `(true, "quiet")`. An option-only addition still misses it. The preserved [original red replay](../../../.devlyn/0117/red.json) used a plain `grok` shim; its `observed_form` label was incorrect. Legacy `-p` and quiet controls worked. Actual Fable R0 findings A16-F1/F2 prompted this correction; [Fable R1](../../../.devlyn/0117/fable-design-r1.txt) accepts the revised design only. Root validates actual design reviews before commit and execution.

The [historical audit](../../../.devlyn/resume-0114-20260905T141058Z/quiet-grok-audit.json) attests only the runner's separate active-root-state block; usage/window were not evaluated, and no overall gate PASS or collection launch is established. Accepted 0114/A15 is committed at `4ccb6d7`; its frozen contract forbids drain changes. This separately owned A16 correction precedes fresh collection without rewriting A15 evidence. The harness must earn both quality and efficiency; this task establishes neither empirical lift nor whole-harness readiness.

## Requirements

- **R1 — Detect the attested process.** In both existing regexes, replace only the Grok subpattern with `grok(?:-[^\s/]+)?\s+(?:-p|--prompt-file)`. Cover the observed versioned basename and long option without hardcoding a version. Preserve each regex's existing boundaries, Claude/Codex/legacy Grok matches, independent root-state/usage/window checks, read-only `ps` probe and failure behavior. No new detector helper, framework, flags, CLI invocation or launch workaround.
- **R2 — Prove the bounded correction.** Extend existing `self_test` controls at `gate_reasons` and `real_writer_check(process_probe)`: the attested absolute-path `grok-1.0.13-macos-aarch64 --prompt-file` and plain `grok --prompt-file` block both predicates; runner blocks with root state absent and completed PASS; legacy `-p` blocks; genuine quiet remains quiet; existing active-root-state assertions persist. Add one `groksomething --prompt-file` quiet control to bound the new basename match. Preserve all old assertions and other behavior. State the before prediction (attested form incorrectly appears quiet), cite raw `red-v2.json` failure and the original replay's shim-only limit, then record the focused after result. Use existing injection seams, no real model run or hidden outcomes; full commands belong to BUILD_GATE/VERIFY.
- **R3 — Register A16 before collection.** Finish code/tests/README, compute normalized apparatus, update only `params.apparatus_sha256`, update both runner/scorer parameter pins, then write seven seals. Drain remains intentionally unsealed. Restate the current process rule in A16; preserve historical A9. Keep staged product `ee8f74d4d2a5061c36b1ad2b4459f6801f08af3b0d08d069a756532bdb8a89f1`, model/version/effort seats, corpus/panel, reps 4/1/1, thresholds, arithmetic, deadlines and usage/window policy unchanged. Reserve fresh `~/.local/share/nx01/iter0113/quick-a16-1` / `lift-quick-a16-1`; preserve prior outputs and noncomparability, with no scoring during implementation. Write one concise 0117 iteration record, replace operative HANDOFF/0113 status and append one DECISIONS row. Only root launches after full gates, fresh actual final trio and implementation commit, using the existing quiet-gated drain, actual-pair smoke, one lane, 72 base cells, infra-only attempts 2/3, one evaluation and exact `NEEDS_TOPUP`. No invented PASS or launch; update the final status checkpoint separately after actual closure.

## Constraints

- Implementation paths only: `benchmark/layer-lift/drain-quick.py`, `run-lift-panel.py`, `score-lift.py` (parameter pin only), `registered-params.json` (apparatus field only), `scripts.sha256`, `README.md`; `autoresearch/HANDOFF.md`, `DECISIONS.md`, `iterations/0113-layer-lift-meter-STUB.md`, `iterations/0117-quiet-grok.md`.
- Product config/skills and installed mirrors, root AGENTS/CLAUDE, 0114 owner/evidence, 0115/0116 candidates, corpus/panel/oracles stay byte-identical. No unrelated cleanup, dependencies, options, hidden-outcome reads, measurement during implementation, release, publish or push. Preserve user-verbatim and historical prose; replace stale operative text.
- **No workaround / No overengineering:** retain both gates and legacy detection; the minimum addition is the observed basename/option alternative and focused controls. CLEANUP is inspection-only unless this scoped change creates an allowlisted orphan, which root reviews before proceeding. **No guesswork:** final claims require actual receipts; deterministic checks prove this bounded fix, not runtime lift.

<!-- devlyn:verification -->
## Verification

All commands must exit 0; sibling `spec.expected.json` fixes their bounds:

- `python3 benchmark/layer-lift/run-lift-panel.py --self-test` — 600 seconds.
- `python3 benchmark/layer-lift/drain-quick.py --self-test` — 120 seconds.
- `python3 benchmark/layer-lift/score-lift.py --self-test` — 120 seconds.
- `shasum -a 256 -c benchmark/layer-lift/scripts.sha256` — 60 seconds.
- `git diff --check` — 60 seconds.

Fresh actual Codex, Fable 5.1 and Grok 4.6 final reviews of the final diff are required after full gates and before root commits. Confirm the attested form blocks independently of root state, quiet/legacy controls survive, registration preserves the frozen measurement contract, and evidence claims remain scoped. No installer/skill lint or broader instrument is added.
