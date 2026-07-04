# iter-0060 — engine-symmetric pair-judge invocation (piece 1 in flight)

**Status**: IN-PROGRESS 2026-07-05 — piece 1 (mechanical state fix)
implemented + pair-reviewed; G1 cell rerun pending (prediction registered
below BEFORE the run). Pieces 2-4 still STUB; their pre-registration is
filled before their first run.
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

## Piece 1 execution record (2026-07-05)

**Root cause confirmed** (2-question why-chain): `verify-merge-findings.py`
`read_findings()` initialized ALL sources — including `pair_judge` — to
`"PASS"` and left it untouched when no pair findings file existed;
`write_state()` copied that into `sub_verdicts`. Writer confirmed as the
script (not the orchestrator prompt): both 2026-07-04 cells' `merged` state
block byte-matches `write_state()`'s shape and equals the sibling
`verify-merge.summary.json`. Violated invariant: a verdict must come from a
judge that ran.

**Fix shipped (3 files, mirrors synced)**:
1. `_shared/verify-merge-findings.py` — `pair_judge` starts `None`; promoted
   to a real verdict only on spawn evidence (pair findings file exists, or
   `codex-judge.stdout` exists); contract-violation blockers unchanged.
   Self-test: first scenario now expects null; new scenario reproduces the
   2026-07-04 auto-skip shape.
2. `_shared/state-phase-write.py` — Codex R0 ship-blocker: stale round-0
   VERIFY artifacts survive fix-loop respawn and would read as current-round
   spawn evidence. New `clear_verify_round_artifacts()` deletes
   `verify*.jsonl` + `codex-judge.*` + `verify-merge.summary.json` on VERIFY
   spawn (per-round reset contract extended from JSON fields to round-owned
   files; single layer at the root — merge-side filter rejected as
   defense-in-depth). Self-test covers the stale shape incl. the
   `verify.findings.judge-codex.jsonl` glob edge the first draft missed.
3. `devlyn:resolve/references/state-schema.md` § Write protocol step 1
   declares the artifact deletion.

**Pair rounds**: R0 adversarial (Codex GPT-5.5 xhigh, read-only, own
citations; log `/tmp/codex-iter0060-state/response.log`) — verdict
SHIP-WITH-EDITS; all 4 of my falsifiers REFUTED with file:line; new decisive
criterion adopted: **current-round spawn evidence**. R1 reconciliation on the
implemented diff: log `/tmp/codex-iter0060-state/r1-response.log`.

**Replay evidence (before G1)**: fixed script replayed on copies of both
2026-07-04 cell run dirs → codex cell `{"judge": "PASS", "mechanical":
"PASS", "pair_judge": null}` overall PASS unchanged; claude cell pair_judge
null, PASS_WITH_ISSUES unchanged.

**G1 predictions (registered BEFORE the cell rerun)**:
- P1: codex-small compliance cell rerun records `sub_verdicts.pair_judge:
  null` in pipeline.state.json.
- P2: `pair_trigger.skipped_reason` stays `auto_pair_other_engine_unavailable`
  (reverse invocation contract is piece 2, not yet shipped).
- P3: `check-compliance-cell.py` verdict PASS — it requires only
  `sub_verdicts.judge` non-null (`check-compliance-cell.py:135`).
- P4 (G4 guard): claude-small cell rerun also PASS with `pair_judge: null`.
- Failure classification pre-agreed: a codex-orchestrator pipeline skip would
  be the F6 class (task-shape dependent), not a piece-1 regression — decided
  by whether the claude-small cell shows the same shape.

**G1/G4 raw results (2026-07-05, fix committed as `b02e53a`)**:
- P1 CONFIRMED: codex-small rerun (`iter0060-g1-codex`, run
  rs-20260704T163231Z-d23ceb5cb395) records `sub_verdicts.pair_judge: null`.
- P2 WRONG in the letter, substance holds: `pair_trigger` recorded
  `{eligible: false, reasons: [], skipped_reason: null}` — this run raised
  no pair-trigger reason at all (trivial F1 task), unlike the 2026-07-04
  cell which skipped on `auto_pair_other_engine_unavailable`. Both are legal
  shapes; the reverse-direction invocation gap (piece 2) remains untested by
  this cell and is what G2 exists for. Prediction recorded as-missed, not
  edited.
- P3 CONFIRMED: `check-compliance-cell.py` overall PASS, no failed
  assertions.
- P4 CONFIRMED: claude-small (sonnet) rerun (`iter0060-g4-claude`)
  compliance PASS, `pair_judge: null`, `pair_trigger` written as
  `{eligible: false, reasons: [], skipped_reason: null}`.
- **G1 gate: SATISFIED. Piece 1 CLOSED** (fix + self-tests + lint + pair
  rounds R0→R1 SHIP + archived-cell replay + live G1/G4 cells).

## Pieces 2-4 pre-registration (2026-07-05, BEFORE any G2/G3 run)

**Design facts locked before implementation** (verified this session):
- Local `claude` v2.1.201 supports `-p`, `--allowedTools` (permission-rule
  syntax, prefix `Bash(cmd *)`), `--permission-mode dontAsk`,
  `--setting-sources`, `--strict-mcp-config`, `--output-format`, `--effort`.
- Empirical (this machine): in `-p` mode a non-allowlisted tool call is
  auto-DENIED without prompting; the run completes and reports the denial.
- Official guide (standing rule citation):
  <https://code.claude.com/docs/en/headless> — `--allowedTools` rule syntax,
  `dontAsk` locked-down semantics, `--output-format`;
  <https://code.claude.com/docs/en/cli-reference> — flag inventory. `--bare`
  is documented as the scripted-call recommendation but skips OAuth/keychain
  (requires `ANTHROPIC_API_KEY`) — NOT usable on subscription-auth machines,
  so the judge uses the existing hermetic pattern
  (`--setting-sources project --strict-mcp-config --mcp-config
  '{"mcpServers":{}}'` — raw `'{}'` fails validation, iter-0004 evidence).
- Constraint: Codex CLI default `workspace-write` sandbox denies network
  (probes README + run-compliance-cell.sh:76-79 evidence) — `claude -p`
  inside it cannot reach the API. Availability probe (`command -v claude`)
  is necessary, not sufficient; spawn failure = same fail-closed class.
  G2 smoke must run codex with network enabled
  (`-c sandbox_workspace_write.network_access=true`).

**Predictions**:
- P5 (G2): codex-orchestrator `/devlyn:resolve --pair-verify` on the F1
  test-repo shape (network-enabled sandbox) spawns a real `claude -p` judge:
  `.devlyn/claude-judge.stdout` + `.devlyn/verify.pair.findings.jsonl`
  written; `pair_trigger.eligible: true` with `mode.pair-verify`;
  `sub_verdicts.pair_judge` non-null; terminal verdict not BLOCKED.
- P6 (G3): omp-orchestrator `--pair-verify` run spawns the first available
  OTHER engine per role resolution (executor default claude → codex judge
  via the existing wrapper contract); pair artifacts + non-null pair_judge.
- P7 (G4): claude-orchestrator cells (claude-small, codex-small) still PASS
  after pieces 2-4; lint PASS; mirror parity.
- Failure classification pre-agreed: a G2 spawn failure with
  `BLOCKED:claude-unavailable` reported honestly is a PARTIAL PASS of the
  fail-closed contract but a FAIL of G2's real-fire gate; a codex pipeline
  skip is the F6 class, not a piece-2 regression.

## Non-goals

- No always-on pair (NORTH-STAR: measurement-gated).
- No new wrapper unless the smoke shows `claude -p` needs the same
  starvation protection codex did (evidence first — iter-0009's wrapper was
  justified by an observed watchdog kill, not speculation).
