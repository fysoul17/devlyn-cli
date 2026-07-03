# Intent Queue

Ordered backlog for the loop-engineering drain (CLAUDE.md "Intent queue"). One
line per intent; link a spec dir once specced. `[x]` done · `[F]` blocked/needs-review.

- [ ] Benchmark evolution loop (autoresearch-style): build the Tier-1
  pair-discriminating headroom fixtures (H1 race, A1 atomic batch first — see
  memory `project_pair_fixture_tier1_2026_05_05`), pass `headroom-gate.py`
  (bare ≤ 60 / solo ≤ 80, both clean), then measure engine combinations via
  `run-fixture.sh --engines-config` cross-mix arms. Iterate iter-0039+ per
  `autoresearch/PRINCIPLES.md`.
