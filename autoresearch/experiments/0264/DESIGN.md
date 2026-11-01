# 0264 design — build-time design fidelity for user-facing UI (candidate E)

Status: frozen after design check round 3 (Astra ultra SHIP; Grok 4.7's one remaining item, the fallback branch of the uptake predicate, applied with the matching bullet wording). Design check rounds 1 and 2 both returned REVISE from both Astra ultra and Grok 4.7, and both rounds' must-change items are applied. Nothing is implemented or measured.

## Why

0262 and 0263 moved the "done" decision; both lost on the owner's blind rating.
- **C (0262):** the builder looked at its own screens. CC 2/16; FC rose.
- **D (0263):** a fresh independent reviewer judged against a written ship bar. CC 0/16; FC rose; 1.81× tokens.
- **Owner's ratings.** The owner rejected 62 of 64 ratings, covering 48 unique outputs (the 16 B outputs were rated twice). B drift between the two rounds was 0.

Three studies followed, on the owner's direction of 2026-11-01: use the available skills and methodologies, and keep only what is genuinely meaningful.

1. **Builders.** No B, C or D run invoked a design skill or method; a search of every tool call found none.
   - Builders may still have read nearby components; that is unmeasured, and this pilot measures it in B as a baseline.
   - The design skill that is auto-available in both engines targets greenfield distinctiveness.
   - The installed rules aimed at existing products are never loaded automatically.
2. **Owner notes.** 57 notes in total, 45 of them specific; a note can fall in several classes.
   - Four classes dominate:
     - a secondary action ignores the product's control vocabulary;
     - an action's weight does not match its importance;
     - a standard affordance is missing;
     - content lacks structure.
   - A narrow-width layout and placement come second.
   - The owner's only accepts followed the product's existing visual language.
   - In one task, the only existing precedent was itself the wrong weight. Copying the nearest control would reproduce that defect.
3. **Evidence.** None of the popular design packs publishes a measured effect.
   - Self-revision without an external signal, and generic LLM design judges, are weak. That is consistent with C and D.
   - Generating against a concrete reference is far easier for a model than inventing. Reusing a product's own components is standard practice, though only vendors have measured it. Both are plausible, not proven, for this setting.

**Hypothesis (plausible and causal, not established).** The builder does not deliberately ground new UI in a suitable precedent from the product before writing it, so it invents controls, weights and structure.

## Candidate E, one rung

**Mechanism.** One bullet in the managed instruction block's Quick Start, kept identical in `CLAUDE.md`, `AGENTS.md` and `_shared/runtime-principles.md`.
- It is inline text, with no file hop: a pointer to another file is the 0261 pattern that was never opened.
- Lint's canonical span (Check 12) stops at `## Quick Start`, so the implementation must also keep this bullet identical across the three files, using the smallest check that does so.

> **User-facing UI** — before the first UI edit, the implementing executor inspects the product's relevant surfaces and picks a suitable precedent: one that already does this job at the same role, scope and importance. Build from its components, tokens, icons, type, spacing, colours, control weight and responsive behaviour; the product's language outranks generic design guidance unless the request changes it. Do not copy a one-off or a known usability or accessibility defect. Where no suitable precedent exists, use the product's primitives to make a familiar, operable control whose weight matches its importance, keep secondary actions subordinate to and next to their content, and keep content and actions reachable at supported widths. Before editing, state the precedent's path and the pattern you will reuse, or the surfaces you checked, why none is suitable and the fallback.

- **Not in E:**
  - a reviewer or gate;
  - a separate reference file or a persistent `DESIGN.md`;
  - task-shaped conventions (icon lists, code-copy blocks, drawers);
  - few-shot examples from owner notes;
  - a deterministic detector;
  - C's capture transport;
  - any change to reporting or claiming.

  The pre-edit statement is visible working text before the first UI edit. It is not a final-report requirement.
- **Exposure.** The classes that motivated E came from owner notes on the two pilot tasks. The text names no task element, and a passing screen licenses only a held-out confirmation.

## Pilot (historical-baseline screen)

- **Runs.** 16 E runs on 0262's apparatus: T1/T2 × 4 routes × 2 replicates, with the same clone starts, task text, delivery boundary and driver policy. The E arm is main at the candidate commit.
  - The historical B arm predates the unattended-tool guard (4.3.20). This is a listed confound.
  - This is a screening study. Adoption requires a held-out confirmation with fresh B and E on the same base.
- **Uptake audit (frozen; transcript, not self-report; blind to ratings).**
  - **Scope.** Only the implementing executor and its implementing children:
    - Claude's stream-json events;
    - Codex session JSONL from `~/.codex/sessions`, matched by cwd and time, including direct Claude→Codex child sessions.
  - **Evidence.** Visible messages and successful source reads, up to the first UI edit.
  - **Excluded.** Private reasoning, parent-only text, echoed instructions and directory listings.
  - **Applied** means either branch holds.
    - **(A) Precedent.**
      - A relevant product surface was read before the first UI edit.
      - A visible statement names it and the pattern to reuse.
      - The diff reuses that pattern or records a justified departure.
    - **(B) Fallback.**
      - Relevant surfaces were read before the first UI edit.
      - A visible statement names the surfaces checked, why none is suitable and the fallback.
      - The diff follows that fallback.
  - **Judging.** A fixed script extracts the ordered excerpt and the diff. Three blind classifier agents judge applied or not applied, and the majority decides. Root does not change votes.
  - **B baseline.** The 16 B transcripts are scored for observable inspection and reuse only, separately: B was never told to state a precedent. A missing trace is UNKNOWN, not evidence of non-use.
- **Rating.** The owner rates all 16 B and 16 E outputs blind and mixed, on the 0263 page and guide. Fewer B anchors would leak the arm, because the owner has seen every B output twice. AI raters rerun as a secondary measure.
- **Definitions and accounting.**
  - CC, claimed_done and FC are as in 0262. CC requires delivered, witness PASS, checks pass and owner accept.
  - Tokens and wall are arm totals over every executor, orchestrator, subagent, repair and failed attempt, using unrounded recorded counts. Infrastructure-only reruns follow 0262's rule.

## Decision rule (frozen before any E run)

```text
TRIGGER_MISS if fewer than 12 of 16 E runs are "applied" (branch A or B). TRIGGER_MISS ends this frozen candidate:
all 16 slots and their costs are kept, it is not a quality result, and a handoff repair is a new, newly frozen candidate.
INCONCLUSIVE if the owner changes more than 2 of the 16 B verdicts, or if usage is missing.

REJECT E if any holds (both arms scored from the new blind ratings):
 (a) E CC < 4 overall;
 (b) E CC = 0 on either task, or E CC < B CC on either task;
 (c) E CC = 0 for either implementing engine (Claude-implemented: drain-claude, direct-claude;
     Codex-implemented: drain-codex, direct-claude-codex);
 (d) an E owner-safety violation (use of the owner's desktop, browser profile or account drivers, or a real secret, as in 0262);
 (e) E arm-total tokens > 1.15 x B, or E arm-total wall > 1.5 x B;
 (f) when both arms' CC > 0: E tokens per CC > B's, or E wall per CC > 1.5 x B's.

SCREEN PASS (licenses the held-out confirmation, not adoption) when none of the above holds.

FC (total, per task), claim precision count(claimed_done and CC)/count(claimed_done), and claim coverage are reported, never gates:
E does not touch claiming, and B's FC is low only where B admitted not looking.

Class coding (whenever the trigger fired, both arms, regardless of the CC outcome): three blind classifiers code each owner
note with the frozen classes 1-4 (vocabulary, weight, missing affordance, structure). The unit is one incidence per output
per class (overlap allowed); majority per output and class. An output with a missing or non-specific note is "uncoded",
never zero, and is reported.
Next-rung branch: if E is rejected on CC and E's coded class 1-4 incidences per coded output are at most half of B's,
the next rung is a deterministic check of the same rules. Otherwise this content line stops.
```

## Predictions (frozen beside the rule)

1. At least 12 of 16 E runs are applied; at most 6 of 16 B runs are.
2. E CC is 2–5 of 16, with T1 ≥ T2.
3. E arm-total tokens are 0.95–1.15× B; wall is at most 1.25× B.
4. E claimed_done is at least 6 of 16.
5. The owner changes at most 2 of 16 B verdicts.
6. Coded class 1–2 incidences per coded output are fewer on E than on the re-rated B.

## Risks

- **Trigger.** The inline bullet may still be ignored; TRIGGER_MISS separates delivery from effect.
- **Owner taste beyond conventions** ("not world-class"): rule (a).
- **Confounds.** Historical B and exposed tasks: screen only, and held-out confirmation is required.
- **Rating recognition.** B outputs may be recognisable. Labels are hidden, but recognition is possible; that is reported.
