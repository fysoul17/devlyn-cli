---
id: "0097-plan-prompt-canonicalization"
title: "PLAN prompt artifact canonicalization: renderer emits no terminal LF; cue sentence deleted; delivery re-gate"
kind: reliability
status: REGISTRATION-DRAFT 2026-08-05 — design pre-committed (0095 design round escalation path, fired by 0096 evidence); R0+R1 3-seat FREEZE required; nothing frozen
complexity: high
depends_on: ["0096-transition-compliance-delivery-regate", "0095-plan-delivery-byte-fidelity"]
---

# iter-0097 — PLAN prompt canonicalization + delivery re-gate

## Why this iter exists (pre-flight 0)

The pre-named escalation from the 0095 design round fired on its exact
trigger (DECISIONS 0096.1): with the Read-cue instruction present in the
candidate tree, candidate-discovery STILL delivered the PLAN prompt
minus its single terminal LF (12,150/12,151; third occurrence of the
identical one-byte class across 0094/0096; candidate-simple byte-exact
both times). The instruction remedy is empirically insufficient at a
live 2/2 bar. The pre-committed successor: fix the ARTIFACT — the
renderer emits `plan.prompt` WITHOUT a terminal LF, making the
Read→transcribe route deterministic (no invisible-or-ignorable final
byte). The digest chain stays self-consistent because the renderer
hashes exactly what it writes (design-round F4: digest-side
normalization stays rejected; this is artifact canonicalization, not
detector softening). Mission 1, ceiling-gate lineage; live delivery
credit for the 0092 R1 native dispatch is still the only thing owed.

## Candidate product change (route through /devlyn:resolve; hypothesis-side, NOT shared)

1. **Renderer canonicalization**
   (`config/skills/_shared/phase-prompt-render.py` + mirrors): the
   renderer's output contract becomes "never emits a terminal LF" —
   exactly one trailing `\n` is stripped from the rendered bytes before
   write+hash when present (content-internal newlines untouched; no
   other normalization). `PLAN_PROMPT_SHA256` self-consistency is
   automatic (the renderer hashes what it writes). Self-test additions:
   rendered output never ends with `0x0a`; digest == written bytes;
   task-context-without-final-newline case (existing) unchanged.
2. **Cue sentence deletion** (net-negative): the 8f99b51 sentence
   ("In Read output, a final empty numbered line denotes the file's
   terminal LF — …") is DELETED from
   `config/skills/devlyn:resolve/SKILL.md` PHASE 1 + mirrors — with a
   canonicalized artifact the cue can never appear, and dead prose
   dilutes the load-bearing instruction (subtractive-first).

Design-round falsifier F1 (a consumer requires the trailing LF) was
ruled NOT-FIRED on active search at the time; R0 seats re-verify on
current bytes before freeze.

## Re-gate protocol (carry 0095/0096 frozen protocol; fresh per 0088.3)

Watcher (grace 5000 ms) + branch worktrees + fresh path per attempt +
four serial ABBA arms + Sonnet 5 parents on the pinned CLI + frozen
`--no-risk-probes` invocation + goals verbatim + opaque tokens/sealed
mapping + landed oracle + registration scorer + sha-anchored assets all
carry. FRESH: sibling bases at the post-canonicalization SHA (control =
candidate with the delivery-hypothesis hunks reverse-applied — the 0094
native-dispatch patch AND the renderer-canonicalization hunks; the
transition guard from 0096 stays SHARED in both trees), fresh tokens,
fresh controls, fresh nonce; 0096's bases/tokens/nonce retired.

Bars unchanged (0095 text is authoritative): candidate structural 2/2
byte-exact; dispatch_clean 4/4; watcher PASS 4/4; blind no-loser
(Fable 5 + Grok 4.5, file:line mandatory, hard conjunct,
non-restorative) — EXECUTED this time if reached (0096's skip was an
orchestrator call, logged); tripwires ≤1.25 / ≤1.50. Ship rule: all
bars pass → live delivery credit for R1 + canonicalization; any bar
fails → no ship credit, new registration. Escalation exhaustion note:
if the SAME one-byte class fires with a canonicalized artifact (no
terminal LF exists to strip), that outcome is definitionally impossible
at this class — any residual digest mismatch is a NEW class and routes
to a new registration with its own diagnosis.

## Falsifiers the orchestrator accepts (R0: fire with bytes)

- F1: a consumer of `plan.prompt` (or of the renderer's output for any
  caller) requires the terminal LF — canonicalization breaks a
  contract.
- F2: a frozen receipt/gate compares against a WITH-LF render digest in
  a way that the re-render does not refresh (stale-digest break).
- F3: the strip is reachable for content whose LAST intended byte is a
  meaningful `\n` inside the contract (over-strip) — show the caller.
- F4: deleting the cue sentence changes any measured non-delivery
  behavior (lint parity, token gauge shift beyond noise) — show the
  receipt.

## Freeze protocol

R0 adversarial (Codex gpt-5.6-sol + Grok 4.5; positions above stated
first) → adjudicate with named deltas → land via `/devlyn:resolve`
(executor pin codex + --pair-verify) → seat-executed proofs (renderer
self-test; the landing run's OWN PLAN phase is live dogfood of the
canonicalized artifact) → R1 FREEZE with liveness markers +
self-computed shas (mandatory on every re-invocation) → fresh
bases/tokens/nonce + per-base probes → matrix. Receipts:
`~/.local/share/nx01/iter0097-reg/` (git, sha-anchored).
