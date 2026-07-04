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
- [F] needs-review: precondition failed — no headroom-passing fixtures exist
  (F34/F35 failed the gate above; Tier-2 F36/F37 on the performance/scale
  axis also failed in iter-0041-headroom-f36-f37, solo 96 on both, commit
  0520ff6). Two design generations solo-saturated; the solo ≤ 80 ceiling
  needs a rethink of fixture strategy — user direction required.
  With headroom-passing fixtures: measure engine combinations via
  `run-fixture.sh --engines-config` cross-mix arms; iterate iter-0040+ per
  `autoresearch/PRINCIPLES.md` (findings → next fixture/harness iteration).
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
- [ ] iter-0060: engine-symmetric pair-judge invocation — reverse direction
  (codex/omp orchestrator → Claude pair judge) never fires today; evidence,
  fix order (mechanical pair_judge-null state fix → claude adapter
  `## Invocation` → symmetric preflight probes → engine-neutral verify.md
  dual-declaration update), and gates G1-G4 locked in
  autoresearch/iterations/0060-engine-symmetric-pair.md. (user direction
  2026-07-05)
- [ ] iter-0058: run the N=4 violation-rate baseline matrix per
  autoresearch/iterations/0058-violation-rate-axis.md (sonnet + one other
  model; fable never a test arm; document per-probe flip-band before any
  A/B claim).
