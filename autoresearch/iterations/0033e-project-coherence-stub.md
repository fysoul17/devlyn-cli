---
iter: "0033e"
title: "ideate PROJECT coherence audit — pair-mode candidate (QUEUED-STUB)"
status: QUEUED-STUB
verdict: not preregistered yet — measurement design TBD
type: candidate measurement (gated by iter-0033d outcome + defect-class oracle definition)
date: 2026-05-03
mission: 1
codex_r05_round3_iter0033c: 2026-05-03 (230s — verdict "Partially agree. PROJECT is not ready for A/B yet." Recommend defect-class oracle FIRST before any A/B run; downstream-coupled resolve scoring is too blunt as first oracle; queue as stub not real prereg until defect classes are explicit.)
---

# iter-0033e — ideate PROJECT coherence audit (QUEUED-STUB)

## Why this stub exists

User direction (2026-05-03): "이거야말로 가장 중요한 스탭이고 이거야말로 여러 LLM이 유저와 면밀하게 검토해서 가장 정확한 방향의 북극성을 만드는 역할을 할텐데 (특히 프로덕트 전체 그림을 보고 일관되게 그림을 그리는 용도)."

`/devlyn:ideate --project` is the surface that produces a multi-feature `plan.md` + N child specs. Cross-spec coherence (dependency DAG, shared constraint propagation, hidden coupling detection, scope ordering) is exactly the failure surface where one-model can drift and a second-model audit could catch defects.

But: per Codex round-3 R0.5, **measurement design is not yet honest enough to A/B**. We don't have a defect-class oracle that scores "coherence" deterministically.

## Status

- **Not pre-registered.** No hypothesis, no falsifiable predictions, no acceptance gates. This file is a placeholder to keep the candidate visible in the queue.
- **Sequencing**: blocked on iter-0033d outcome AND on a defect-class oracle being explicit.
- **Sequence**: iter-0033d (PLAN-pair) → iter-0033e (PROJECT-pair) IF iter-0033d validates pair-mode mechanism AND defect oracle is ready.

## Hypothesis (placeholder)

Second-model audit of `{plan.md + N child specs}` catches cross-spec defects that solo-mode misses, materially improving downstream `/devlyn:resolve` outcomes on each child spec.

## Required preconditions before this iter promotes from STUB to PRE-REGISTERED

### 1. Defect-class oracle definition

Codex R0.5 round-3 recommendation: defect-class oracle preferred over LLM-judge oracle. Candidate defect classes (per `config/skills/devlyn:ideate/references/project-mode.md`):

- **dependency DAG broken**: child spec declares `depends_on: <feature>` that doesn't exist in the index, OR creates a cycle.
- **project constraint not inherited**: project-level constraint (e.g. "all features must use TypeScript") missing from a child spec's `## Constraints`.
- **contradictory shared constraints**: two child specs declare incompatible constraints on a shared file/module.
- **hidden coupling**: two child specs touch the same file but one doesn't declare the other in `depends_on`.
- **overlapping scope**: two child specs' `## In Scope` overlap without coordination.
- **invalid implementation order**: `plan.md` suggested order violates `depends_on` graph.
- **missing/invalid `spec.expected.json`**: child spec lacks expected.json OR expected.json fails schema validation.

Each defect class needs:
- A scriptable detector (Python).
- A test fixture pair: clean PROJECT output that passes + corrupted PROJECT output that should be detected.
- Pre-registered tolerance (e.g. "0 false-negatives on test fixtures, ≤5% false-positives on a held-out PROJECT corpus").

### 2. iter-0033d outcome

If iter-0033d validates pair-PLAN mechanism (firewall + structural separation works), the same architecture transfers to PROJECT-pair. If iter-0033d invalidates pair-mode mechanism entirely, this stub is killed and pair-mode is shelved across all phases.

### 3. Real-PROJECT corpus

Need ≥3 real PROJECT runs (manually crafted or from internal use) where coherence defects exist. `--project` mode is not yet exercised by benchmark fixtures; without a corpus, oracle calibration is impossible.

## Deferred to iter-0033e PROMOTE

- Actual measurement architecture (downstream-coupled resolve scoring? defect-class oracle? hybrid?).
- Acceptance gates.
- PROJECT-pair structural firewall (mirror PLAN-pair's; child specs are the "contract" downstream resolve consumes).
- ideate spec-audit decision: does PROJECT-pair imply per-spec audit too, or is PROJECT-only sufficient?

## Why this stub instead of a full pre-registration

Codex R0.5 round-3 verbatim: "Queue 0033e as a stub, not a real prereg, until the defect classes are explicit."

Pre-flight 0 (PRINCIPLES.md): an iter that exists without a falsifiable hypothesis violates principle #2. This stub holds the candidate visible without committing to a measurement we don't know how to design yet.
