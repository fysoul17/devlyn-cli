# iter-0059 — North-Star audit round: contract preamble, engine-status honesty, pair-protocol v2

**Status**: SHIPPED 2026-07-04 (guards recorded below before commit).
**Trigger**: user direction 2026-07-04 (verbatim intent): deep agent-perspective
audit of whether CLAUDE.md/AGENTS.md capture the North Star ("any agent —
Fable, Opus, GPT, GLM — world-class CONSISTENT performance, hands-free via
loop engineering"), where the harness stands, and visibly evidence-backed
improvements including more effective adversarial pair collaboration.
**Pair rounds**: Codex GPT-5.5 R0 (adversarial, xhigh, read-only, 418s,
independent file:line citations) + R1 (reconciliation on the implemented
diff). First round pair run under the upgraded protocol this iteration ships.

## Audit verdict (evidence-first)

1. **The North Star was written nowhere the runtime reads.** CLAUDE.md
   (176 lines / 6004 tok c4) and AGENTS.md (110 / 2419) carried principles +
   process but zero purpose statement; `bin/devlyn.js:728-732` copies
   CLAUDE.md verbatim into every downstream project, so installed agents got
   rules with no goal to resolve ambiguity against. R0 decisive criterion:
   "cold-start ambiguity resolver."
2. **Engine-consistency claim exceeded the measurement.** "Contract is
   symmetric" implied orchestrator parity; measured reality: Claude Code +
   omp run the full phase-gated pipeline (iter-0040 R2, iter-0052 cells);
   Codex CLI skips it by choice on trivial tasks in minimal repos —
   re-verified REPRODUCED this date (iter-0040 § Round 3 addendum,
   codex-cli 0.141.0, stamped skills, task-triviality/repo-shape dependent).
   R0 criterion: "ordinary-invocation non-skippability" → honest
   experimental label, not silent asymmetry and not premature demotion.
3. **The evolution loop's primary instrument was saturated.** Two fixture
   generations solo-saturated (F34-F37, solo 88-97) → headroom gate has zero
   passing fixtures → pair-mode roadmap deadlocked; meanwhile drift-bait
   violations persist on every tier (Fable 3/6, Opus 2-3/6, Sonnet 1-2/6,
   iter-0045 P3). Pivot pre-registered as iter-0058. R0 criterion: "oracle
   matches North-Star failure mode."
4. **Local-backend surface had zero passing product-quality measurement**
   (iter-0055/0056 gemma3:4b judge = model ceiling) while remaining
   pin-eligible. Deleted as iter-0057. R0 criterion: "pin-eligible routes
   require measured non-harm."

## Shipped in this iteration

- `CLAUDE.md` + `AGENTS.md`: identical `## North Star` section (3 sentences:
  engine-consistent hands-free engineer-quality; harness must out-earn bare;
  ambiguity resolves toward the goal).
- `CLAUDE.md` engine-roles orchestrator row + `AGENTS.md` engine-roles
  paragraph: measured-status label (Codex-CLI orchestration experimental,
  iter-0040 F6) + AGENTS.md-channel instruction to Codex: phase machinery is
  mandatory; refusal must be explicit, never a silent degrade.
- `autoresearch/HANDOFF.md` pair-collab protocol v2: round budget R0
  adversarial + R1 reconciliation; further rounds need NEW evidence
  (anti-asymptotic, iter-0033g); per-round prompt carries source packet
  (file:lines), supersession map, criterion-before-arguments, falsifiers.
- `autoresearch/iterations/0040-cross-cli-smoke.md` Round-3 addendum: F6
  re-verification evidence + latent stamping-guard finding (iter-0059+
  candidate, not fixed — unexercised, omp pass mechanism unestablished).
- `autoresearch/iterations/0058-violation-rate-axis.md` pre-registration
  (separate file; measurement not run in this iteration).
- iter-0057 local-backend removal implemented by a delegated agent under
  this session (separate iteration file + ledger).

## Guards

- `bash scripts/lint-skills.sh` → "All checks passed." (pre- and post-edit).
- Mirror parity `config`/`.claude`/`.agents` → clean (post iter-0057).
- Compliance cells re-run on the combined tree, results recorded below
  before commit: claude-small (MODEL=sonnet) + codex-small
  (`benchmark/probes/results/iter0059-guard-{claude,codex}/`).
- Codex R1 reconciliation verdict recorded below before commit.

## Guard results (filled before commit)

- Codex R1 (231s, high effort): A/B/C/D/E SHIP; one FIX-FIRST — the
  iter-0040 addendum phrase "same stamped skills" overstated iter-0052
  evidence (its sync is plain `cp -R`, placeholder unstamped in the saved
  transcript). Fixed before commit; R1 independently verified byte-identical
  North-Star blocks, omp-status evidence backing, protocol-rewrite fidelity,
  0058 artifact support, and clean engine-doctor rendering.
- claude-small (MODEL=sonnet): PASS, failed_assertions [] —
  `benchmark/probes/results/iter0059-guard-claude/`.
- codex-small: PASS, failed_assertions [] —
  `benchmark/probes/results/iter0059-guard-codex/`. (Reinforced-prompt cell;
  per R0, its PASS is a regression guard, NOT evidence of
  ordinary-invocation non-skippability — that claim stays bounded by the
  iter-0040 F6 addendum.)
