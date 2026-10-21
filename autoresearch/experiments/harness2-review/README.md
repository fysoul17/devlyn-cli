# Harness² review (2026-10-20)

The owner asked what devlyn-cli can leverage from
[google-research/harness2](https://github.com/google-research/harness2)
(read at commit `1cfe254`; paper arXiv 2610.14224v1). Root, Astra ultra and
Grok 4.7 answered independently, then cross-critiqued root's synthesis
([rounds/](rounds/); round-1 material paths point to session scratch). Both
round-2 reviews and both round-3 reviews of the resulting docs change were
REVISE; their verified corrections are applied here and in the playbook.
Round 4: Astra SHIP; Grok's remaining finding (state §6's per-task completion
and check-row counts exactly) is applied.

## What Harness² is

Per-task, test-time harness refinement without a ground-truth verifier: base
executions, invariant- and domain-scoped editors that edit the harness tree
from trajectories, one probe execution per candidate, composition, blind
selection when k > 1, and a reflector that stores the adopted tree with
evidence-backed lessons for later tasks. Each task schedules 4k executions and
3k improvement stages, with selection and reflection outside that count
(`harness2/core/ledger.py`).

## Decisions

- **Not adopted into the product:** the runtime recursion, blind selection,
  harness libraries and scoped dual editors. They multiply executions per task
  and have not demonstrated admission under the ladder rule, which counts all
  costs per correctly completed task (0232 §6); 0234 found no completion gain from pair
  reasoning at about 2.3–3.5× input. The released selection pool also excludes
  base outputs despite the KEEP_BASE language (`prompts.py`; pool in
  `selection.py`), and the paper's
  failure analysis reports selections of a weaker candidate (E.6).
- **No blanket move from prose to skills.** Table 6 removes components from an
  already refined k=5 harness; it does not compare adding one skill to an
  instruction-only base. 0233's triggered `failure-paths.md` was not admitted,
  and 0223 showed a deletion can remove useful behavior.
- **Adopted into the research process:** five evidence rules replace the
  retired auto-resolve procedure in
  [playbooks/iteration-loop.md](../../playbooks/iteration-loop.md), plus
  apparatus qualification per engine × arm, which rp-d8 lacked.
- **No hook now.** A completion or delivery hook is Harness²'s lever for clear
  instructions that are repeatedly skipped. 0232 O4 already prices it (all
  costs per correctly completed task), but installing one changes installed
  behavior, the installer removes the retired Stop hook on purpose, and no
  residual skip has been measured on the current package. Reopening it is an
  owner decision.

## Recommended next measurement (owner decision)

Every Harness² gain is a delta over a measured base; ours is stale. 0233's
development panel (n = 8 per arm, never pooled with confirmation) had Claude
bare 4/8 vs installed 4.2.0 2/8 and Codex 5/8 vs 6/8, and quality conditions
(false completions, witnessed defects) failed both package-vs-bare
comparisons. That arm was the whole installed package, not the block alone.
The coherent replay is bare vs the current package on D3, D4, I0185 and B5,
with F10/F11 confirmation, E1/E2 as the reported one-replicate easy panel, a shared local endpoint
(bare opens no PR) and 0233's quality rule. A literal block-only arm is a
broken-dependency ablation, because Quick Start points at skills and helpers
it would lack. Two replicates detect quality defects; settling completion
counts needs far more (Astra's planning example: 14 replicates per fixture for
about 90% power per engine).
