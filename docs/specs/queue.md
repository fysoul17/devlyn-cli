# Intent Queue

Ordered backlog for the loop-engineering drain (`/devlyn:queue`; contract in
CLAUDE.md / AGENTS.md "Intent queue"). One line per intent; link a spec dir
once specced. `[x]` done · `[F]` blocked/needs-review.

- [ ] Activate + measure Tier-1 headroom fixtures F34/F35 (written and
  self-validated in `benchmark/auto-resolve/fixtures/staging/` — follow
  `staging/README.md`: mv into `fixtures/`, lint, bare+solo arms via
  `run-full-pipeline-pair-candidate.sh`, `headroom-gate.py` bare ≤ 60 /
  solo ≤ 80; on FAIL retire honestly, never tune the oracle).
- [ ] With headroom-passing fixtures: measure engine combinations via
  `run-fixture.sh --engines-config` cross-mix arms; iterate iter-0040+ per
  `autoresearch/PRINCIPLES.md` (findings → next fixture/harness iteration).
- [ ] Cross-CLI smoke (user direction 2026-07-03: harness must run on Codex
  CLI and oh-my-pi, not only Claude Code): install via `npx devlyn-cli` with
  codex/omp targets, then run `/devlyn:queue` status and one trivial
  `/devlyn:resolve` item from each CLI; log every asymmetry found (subagent
  spawning semantics for VERIFY fresh-context independence is the predicted
  gap) as iter-0040 candidates.
