---
id: "0098-lf-run-insensitive-compare"
title: "Terminal-LF-run-insensitive delivery comparison (two-branch predicate) + fresh delivery re-gate"
kind: reliability
status: REGISTRATION-DRAFT 2026-08-06 — design round CONVERGED (Codex+Grok AGREE-WITH-EDITS); two-branch predicate adopted; product change not yet landed
complexity: high
depends_on: ["0097-plan-prompt-canonicalization"]
---

# iter-0098 — LF-run-insensitive delivery comparison + re-gate

## Why this iter exists (pre-flight 0)

Three matrices measured the terminal-LF byte at the
Read→transcribe→`Agent.prompt` boundary as BIDIRECTIONALLY
model-unstable (0094 strip; 0096 strip despite the cue instruction;
0097 ADD onto the canonicalized no-LF artifact — DECISIONS
0094.1/0096.1/0097.1). Artifact-side and instruction-side remedies are
both measured-insufficient. The byte is semantically void (0095 packet,
user's original intuition) and — with the canonicalized source — is
structurally unable to carry information. The 0095 design round's F4
rejection is re-opened with its premise falsified: the delivery bar
must stop failing on this run while failing on every real corruption.
Mission 1; live delivery credit for the 0092 R1 native dispatch remains
the owed conjunct.

## Design (converged 2026-08-06, receipts ~/.local/share/nx01/iter0098-design/)

Oracle-only change (`benchmark/ceiling/scripts/plan-dispatch-oracle.py`):

1. Compute and record BOTH `delivered_prompt_sha256` (raw, unchanged)
   AND `delivered_prompt_terminal_lf_stripped_sha256` per candidate;
   bump the oracle payload schema for the added field.
2. Acceptance predicate at BOTH digest-enforcement sites (in-window
   shape check + delivery_attestation.match):
   `recorded == raw OR recorded == lf_stripped` — the raw-exact branch
   FIRST. [Adjudicated over Grok's single stripped-compare: the
   retained WITH-LF-era receipts (0091 C1, 0094 candidate-simple)
   conserve COMPLETE only through the raw branch — named criterion
   RETAINED-RECEIPT CONSERVATION. Grok convergent on everything else.]
3. `delivered-prompt-digest-mismatch` stays for real mismatches; no
   rename. Renderer/ledger/state/SKILL.md untouched.
4. Self-tests: retained with-LF exact (compat, raw branch); canonical
   exact; +1 and +N terminal-LF acceptance with UNEQUAL raw vs stripped
   digests both recorded; non-terminal mutation → still violation;
   `$(cat …)`-class mismatch → still violation.

Given the canonicalized source (never ends 0x0a), a delivered terminal
LF run is provably pure transport addition; stripping it cannot mask
content corruption (any real mutation differs in non-terminal bytes).
Falsifiers from the round: F1 no masking scenario constructible (both
seats); F2 void-byte semantics confirmed; F3 no native file/bytes input
on the pinned CLI's Agent tool; F4 raw-digest retention + raw-first
branch keeps every historical receipt stable (Codex's amendment,
adopted).

## Re-gate (carry 0097 frozen protocol; fresh per 0088.3)

Everything carries (watcher, branch worktrees, ABBA, pinned CLI,
`--no-risk-probes`, goals verbatim, scorer, guard SHARED); FRESH sibling
bases at the post-oracle SHA — control = candidate with the 0094
native-dispatch patch + the 0097 canonicalization/cue patch
reverse-applied (the oracle is the MEASURING instrument, identical for
both conditions — NOT part of the mutual delta); fresh tokens, sealed
mapping, fresh nonce. Bars: candidate structural 2/2 under the
two-branch predicate; dispatch_clean 4/4; watcher PASS 4/4; blind
no-loser (reached iff bars 1/2/3/5 pass; both judges MUST run when
reached); tripwires ≤1.25/≤1.50. Ship rule: all bars pass → live
delivery credit for R1 + the canonicalization + this compare; any bar
fails → new registration. Operator: never launch arms near the 12am
KST session-quota boundary (0097 lesson).

## Freeze protocol

Land the oracle change via /devlyn:resolve (executor codex,
--pair-verify) → seat-executed proofs (oracle self-test; 4 retained
full-arm replays ON COPIES: 0091 C1 COMPLETE + 0094 cs COMPLETE via the
raw branch, 0094 cd + 0091 C2 violations conserved; NEW: 0097
candidate-simple full-dir replay must now score COMPLETE via the
stripped branch — the added-LF receipt becomes the satisfiability
proof) → R1 FREEZE both seats with liveness markers → fresh
bases/tokens/nonce + per-base probes → matrix. Receipts:
`~/.local/share/nx01/iter0098-reg/` (git).
