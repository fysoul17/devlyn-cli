# Intent Queue

Ordered backlog for the loop-engineering drain (`/devlyn:queue`; contract in
CLAUDE.md / AGENTS.md "Intent queue"). One line per intent; link a spec dir
once specced. `[x]` done · `[F]` blocked/needs-review.

- [x] Activate + measure Tier-1 headroom fixtures F34/F35 (written and
  self-validated in `benchmark/auto-resolve/fixtures/staging/` — follow
  `staging/README.md`: mv into `fixtures/`, lint, bare+solo arms via
  `run-full-pipeline-pair-candidate.sh`, `headroom-gate.py` bare ≤ 60 /
  solo ≤ 80; on FAIL retire honestly, never tune the oracle).
  — done 2026-07-03, gate FAIL 0/2 (F34 bare 92/solo 88; F35 bare 50/solo 97
  + timeout); both retired honestly, commit ae7711d, run
  iter-0039-headroom-f34-f35.
- [x] superseded: precondition failed — no headroom-passing fixtures exist
  (F34/F35 failed the gate above; Tier-2 F36/F37 on the performance/scale
  axis also failed in iter-0041-headroom-f36-f37, solo 96 on both, commit
  0520ff6). Two design generations solo-saturated.
  — resolved 2026-07-05 by iter-0058 (user evolution mandate 2026-07-04):
  stop authoring harder synthetic feature fixtures; the evolution gate is
  now the N-rep violation-rate matrix (`benchmark/probes/README.md`
  § Violation-rate gate; baseline `results/iter0058-base-matrix.{json,md}`).
  Cross-engine comparison arms (`--engines-config`) re-enter through the
  violation-rate matrix, not score-lift.
- [x] Cross-CLI smoke (user direction 2026-07-03: harness must run on Codex
  CLI and oh-my-pi, not only Claude Code): install via `npx devlyn-cli` with
  codex/omp targets, then run `/devlyn:queue` status and one trivial
  `/devlyn:resolve` item from each CLI; log every asymmetry found (subagent
  spawning semantics for VERIFY fresh-context independence is the predicted
  gap) as iter-0040 candidates.
  — done 2026-07-03: `/devlyn:queue` status PASS on both CLIs (correct, no
  mutation). `/devlyn:resolve` produced correct code+tests on both, but the
  predicted gap was confirmed and broader — neither CLI ran the phase-gated
  pipeline at all (no `.devlyn/` state, no VERIFY subagent); root cause is
  hardcoded `.claude/skills/_shared/*.py` paths that don't exist on
  Codex/omp's global install locations. 5 findings (F1-F5) logged, findings
  only, no fix applied — see `autoresearch/iterations/0040-cross-cli-smoke.md`.
- [x] iter-0060: engine-symmetric pair-judge invocation — reverse direction
  (codex/omp orchestrator → Claude pair judge) never fires today; evidence,
  fix order (mechanical pair_judge-null state fix → claude adapter
  `## Invocation` → symmetric preflight probes → engine-neutral verify.md
  dual-declaration update), and gates G1-G4 locked in
  autoresearch/iterations/0060-engine-symmetric-pair.md. (user direction
  2026-07-05)
  — done 2026-07-05, commits b02e53a + 3fd034d: all gates PASS. G2 = first
  reverse-direction fire (codex orchestrator spawned a real headless Claude
  pair judge, run iter0060-g2-pair); G3 = omp spawned a codex judge per
  role resolution (run iter0060-g3-pair); G4 = claude path no-regression.
- [x] iter-0058: run the N=4 violation-rate baseline matrix per
  autoresearch/iterations/0058-violation-rate-axis.md (sonnet + one other
  model; fable never a test arm; document per-probe flip-band before any
  A/B claim).
  — done 2026-07-05: sonnet+opus N=4 (48 runs), baseline artifact
  `benchmark/probes/results/iter0058-base-matrix.{json,md}`; flip-band
  documented in the iter file (10/12 cells band 0; sonnet
  DB-silent-catch band 1, DB-tempting-state-file band 2).
- [x] VERIFY dual-judge becomes the DEFAULT whenever a second engine is
  available — delete the conditional-fire route for code VERIFY: every
  shippable code run dispatches both judges CONCURRENTLY (wall=max,
  iter-0071 mechanism); capability-gated (single-engine users unaffected,
  proceed solo with skip report), `--no-pair` stays the explicit opt-out,
  explicit routes still fail closed. Plan-stage risk-probes stay
  conditional. Grounds: user adjudication 2026-07-13 (no
  coverage-reduction-for-efficiency; wall savings via concurrency) +
  tri-seat consensus 2026-07-14 (Fable × codex 5.6-sol × grok 4.5, D1
  AGREE×3). Validate: run archives show dual dispatch on 100% of shippable
  code runs when a second engine is available, pair wall ≈ max(judges) not
  sum; sync all 3 skill mirrors (config/.agents/.claude) +
  CLAUDE.md/AGENTS.md conditional-default wording. (user go-ahead
  2026-07-14, candidate 1 of the harness-comparison discussion)
  — done 2026-07-16: schema-v3 `pair.default` shipped (Codex sol 24-file
  packet + Grok review, net −24 lines); validator self-tests, lint (6b +
  6j + 3 checks' needles retargeted), archived 0071 replays (v2-conc
  merges, v2-seq stays BLOCKED preknown), and live canary
  `dualjudge-default-20260716` PASS (pair_trigger `["pair.default",
  "judge.warning"]`, both judges, dispatch overlap Δ5.8s). Known gap:
  sonnet orchestrator skipped `judge_durations_ms` this run
  (instruction intact, validator non-enforcing) — noted, not rescued.
- [ ] Context-engineering (Claude 5 blog "The new rules of context engineering
  for Claude 5-generation models"; user-queued 2026-08-05; rewritten same
  day after Fable×Codex round-2 cross-check, receipts in conversation +
  scratchpad codex-r1/r2) item 1 of 2 — contract-source correctness,
  mechanical fixes only (no violation matrix needed): ① compact-paraphrase
  drift — plan.md:34/37 (and implement.md if it carries the same phrase)
  say "no hardcoded values", materially broader than canonical Core
  Principle #1 "no hardcoded fallback that hides a broken contract"
  (CLAUDE.md:13); restore the canonical narrow wording, no precedence rule
  exists to resolve the conflict today. ② Metadata contradiction —
  devlyn:ideate/SKILL.md:27 claims runtime-principles.md supplies
  No-workaround while runtime-principles.md:5 states No-workaround lives
  only in CLAUDE.md Core Principle #1. (③ withdrawn 2026-08-05 during
  pipeline PHASE 0 verification: runtime-principles.md:3 declares
  binding-scope — "every sub-agent … must satisfy" — not a reader list;
  PLAN is genuinely bound via its compact paraphrase, so the sentence is
  true and "correcting" it would narrow semantic scope. Actual readers for
  the record: IMPLEMENT, BUILD_GATE, CLEANUP, VERIFY, PROBE_DERIVE.)
  Paraphrase drift confirmed in BOTH plan.md:37 and implement.md:36.
  Corrected facts
  vs the original item: the three CLAUDE.md↔runtime-principles.md
  enforcement blocks are byte-identical under lint Check 12
  (lint-skills.sh:3883) — Claude-side co-loading is a token-duplication
  question deferred to item 2, NOT mirror drift; CLAUDE.md↔AGENTS.md parity
  is out of scope (AGENTS.md frozen per user directive 2026-08-05). Keep
  Check 12 until item 2 decides.
- [ ] Context-engineering item 2 of 2 — pre-registered contract-PLACEMENT
  experiment C/K/F, Claude seats only (AGENTS.md + codex/grok adapters stay
  byte-identical, asserted): arm C = current (full CLAUDE.md + phase-time
  runtime-principles reread); arm K = session-source (full CLAUDE.md;
  Claude phase prompts omit the generic reread — note the read directives
  live in shared canonical phase bodies, so K needs an engine-conditional
  assembly path, itself a cost); arm F = phase-source/flip (CLAUDE.md keeps
  the 7 principles + 3 discipline rules verbatim + a load pointer;
  runtime-principles.md becomes sole owner of the three enforcement blocks;
  PLAN repaired to load them). Measure BOTH windows — bare conversation
  (existing instrument: benchmark/probes/scripts/
  run-drift-bait-probe-resolve.sh invokes claude -p without resolve
  framing; iter-0069 completion-evidence incidents happened on this ungated
  surface) and pipeline. Exact pinned identities claude-opus-4-8 (gen-4) +
  claude-opus-5 (gen-5) — same-tier cross-generation pair isolates the
  generation variable (user direction 2026-08-05; the earlier
  opus-4-8+sonnet-5 pairing confounded tier×generation); claude-sonnet-5
  optional third if budget allows. PREREQUISITE: recert-seats.sh
  exact-model-ID support + opus-5/opus-4-8 seat certification (diagnosed
  2026-07-28 as the A/B 선행작업; opus-5 seat currently uncertified).
  iter-0058 debug logs attest BOTH generations show drift pressure under
  the current contract (opus-4-8 12/24, sonnet-5 9/24), so no arm may
  regress either generation. N≥4, interleaved, full
  six-probe panel, per-cell flip bands, clean-cell regression veto, frozen
  arm snapshots + prompt SHA-256s (all-phase prompt hashing is NEW work —
  only PLAN persists prompt_sha256 today; archive_run.py allowlist excludes
  ordinary phase prompts). Decision rule: F passes both generations+windows
  → adopt flip wholesale + delete Check 12; K passes while F regresses →
  adopt K (mirror + Check 12 stay); gen-4/gen-5 split → license ONE
  adapter-boundary conditional only (no flag, no per-generation CLAUDE.md);
  neither → keep current. Tie → F wins by net deletion (Subtractive-first).
- [x] Context-engineering item 3 (rich references over simple specs) —
  rejected 2026-08-05 by Fable×Codex round-2 cross-check, never drained:
  bundles three mechanisms without a demonstrated gap. Failing-test oracles
  already supported (expected.schema.json `verification_commands`); spec
  requirements + VERIFY's four axes already form the judge rubric (resolve
  SKILL.md:286); HTML mockup fidelity is the only plausible gap —
  re-register a focused HTML-reference A/B only after an observed fidelity
  miss. (No overengineering: no generic references block without an
  observed failure.)
- [ ] Measurement phase 3 (user direction 2026-08-05; starts AFTER
  context-engineering item 2 closes): bare < solo < pair performance
  measurement + improvement on Lane A (benchmark/auto-resolve gates).
  Pair seats per user: opus (claude), codex gpt-5.6-terra, grok 4.5 —
  cross-vendor OTHER-engine pairs, direction-symmetric protocol.
  Binding constraints carried in: pair-mode measurement needs benchmark
  headroom first; pair-vs-solo is an empirical per-phase comparison (pair
  fires only where measured lift); fable is never a test arm; grok
  emission remains uncertified — no durable `pair grok` pin. Scope:
  measure first, then register improvements from the observed deltas.
