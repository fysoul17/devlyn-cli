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
- [ ] VERIFY dual-judge becomes the DEFAULT whenever a second engine is
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
