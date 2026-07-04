# iter-0060 — engine-symmetric pair-judge invocation (STUB, evidence locked)

**Status**: STUB 2026-07-05. Evidence captured; design sketched; NOT
pre-registered (pre-registration belongs to the session that runs it, with
predictions filled before any run).
**Trigger**: user direction 2026-07-04/05 — "codex나 omp가 오케스트레이터일
때도 다른 에이전트와 페어 협업이 일관되어야 한다." Verified NOT true today.

## Evidence (2026-07-04 guard runs, artifacts on disk)

1. **Reverse pair direction never fires.** codex-small compliance run
   (`benchmark/probes/results/iter0059-guard-codex/.../pipeline.state.json`):
   `pair_trigger: {eligible: false, reasons: [], skipped_reason:
   "auto_pair_other_engine_unavailable"}` — yet `command -v claude` resolves
   (`/Users/aipalm/.superset/bin/claude`, v2.1.201, checked same day). The
   codex orchestrator judged Claude unavailable because no invocation
   contract exists for the codex→claude direction: `codex-config.md` +
   `codex-monitored.sh` cover Claude→Codex only; `_shared/adapters/claude.md`
   has NO `## Invocation` section (the deleted ollama adapter had one — that
   was the adapter-declared-invocation pattern); `engine-preflight.md`
   defines no headless-claude availability probe;
   `references/phases/verify.md:161-162` says "the host cannot spawn a
   Claude agent" — which, absent a contract, is literally true for codex.
2. **verify.md is Claude-orchestrator-centric.** `verify.md:149`: "Claude is
   the primary judge; if pair-mode triggers, Codex is still the mandatory
   OTHER-engine judge." On a codex/omp orchestrator the roles invert; the
   text does not. CAUTION: this section is lint dual-declaration-pinned
   (SKILL.md PHASE 5 restates it; `scripts/lint-skills.sh` literal checks —
   iter-0047 Finding 1). Any rewrite must update both copies + lint strings.
3. **State contract violated on skip.** Both 2026-07-04 cells record
   `sub_verdicts.pair_judge: "PASS"` although no pair judge ran
   (codex cell: skipped; claude cell: `pair_trigger: null`). Contract
   (`verify.md:91`): record `pair_judge: null` when the second agent is not
   spawned. Suspect: `verify-merge-findings.py --write-state` defaults to
   PASS when no pair findings file exists (unverified — root-cause first).
   "PASS" from a judge that never ran is exactly the silent-corruption shape
   principle 7 forbids.

## Fix design sketch (4 pieces, smallest-first)

1. **Mechanical state fix** (independent, ship first):
   `verify-merge-findings.py` writes `pair_judge: null` when no pair judge
   was spawned; extend `--self-test`. Root-cause before editing: confirm the
   writer is the script, not the orchestrator prompt.
2. **`_shared/adapters/claude.md` gains `## Invocation`** (orchestrator-side
   contract, mirroring codex-config.md's role): availability probe
   `command -v claude`; headless judge call shape (`claude -p`, model
   inherited from CLI default, output-to-file, no pipe); bounded permission
   design for a judge that may run "at most two targeted probes" (verify.md
   pair contract) — this is the open design question: pick the smallest
   permission surface that lets the judge run repo test commands headless,
   and fail closed (`BLOCKED:claude-unavailable`) when headless spawn fails.
   Per the standing rule, cite the official Anthropic guide for any adapter
   content change.
3. **`engine-preflight.md`**: symmetric availability probes per engine
   (claude: `command -v claude`; codex: `command -v codex`; omp: `command -v
   omp`); delete the now-false asymmetry instead of adding a new branch.
4. **verify.md + SKILL.md PHASE 5 mirror**: engine-neutral judge naming
   ("executor-engine judge is primary; first available OTHER engine is the
   pair judge") — update both lint-pinned copies together.

## Acceptance gates (fill predictions at pre-registration)

- G1: `verify-merge-findings.py --self-test` covers the null-on-skip case;
  a rerun of the codex-small cell records `pair_judge: null` + unchanged
  overall PASS.
- G2: a codex-orchestrator `/devlyn:resolve` run on a fixture whose pair
  trigger fires (e.g. `--pair-verify` explicit route) produces a real
  Claude pair-judge artifact (`verify.pair*.findings.jsonl` written by a
  spawned `claude -p` child) and `pair_mode=true` in state — the
  first-ever reverse-direction pair evidence.
- G3: same for omp orchestrator (omp spawns claude or codex judge — first
  available OTHER engine; omp's backing model family must not silently
  match the judge engine).
- G4: Claude-orchestrator path unchanged (claude-small + codex-small cells
  PASS; no lint regression; mirror parity).

## Non-goals

- No always-on pair (NORTH-STAR: measurement-gated).
- No new wrapper unless the smoke shows `claude -p` needs the same
  starvation protection codex did (evidence first — iter-0009's wrapper was
  justified by an observed watchdog kill, not speculation).
