---
id: "0094-r5-regate"
title: "R5 re-gate: live four-arm matrix for the native foreground PLAN dispatch"
kind: reliability
status: REGISTERED-FROZEN 2026-08-05; arms not yet run
complexity: high
depends_on: ["0092-plan-native-foreground-dispatch"]
---

# iter-0094 — R5 re-gate registration

Successor live gate for iter-0092's R1 candidate (native foreground PLAN
dispatch, landed `83b275e`, formal verification GREEN at verify-only
`rs-20260805T030021Z`). 0092's matrix closed UNSCORED
protocol-failed-at-controls (DECISIONS 0092.1); per the 0088.3 rule this is
a NEW registration with fresh controls and a fresh judging nonce. Only live
delivery credit is at stake; the landed implementation stands on its formal
verification either way.

## Frozen protocol (summary; receipts are authoritative)

Registration receipts: `~/.local/share/nx01/iter0094-reg/` (git repo,
`frozen-assets.sha256` anchors every frozen asset incl. driver, goals,
watcher, dispatch scorer, oracle, IMPLEMENT heading source). Matrix home:
`~/.local/share/nx01/iter0094-r5/`.

- Four serial ABBA arms — control-simple → candidate-simple →
  candidate-discovery → control-discovery — worker-visible names carry only
  opaque tokens (`cc218382`, `0e9f44a7`, `0260532c`, `53aafda1`); the
  token→condition mapping is sealed with commitment `fabde4e5…`.
- Arm bases are neutral machine-local sibling commits (identical parent
  `3de1b66`, identical metadata): candidate `b609891` (tree ==
  `3558b57^{tree}`), control `cacf806` (tree == `caddd93^{tree}` =
  `3558b57` with only the 83b275e PLAN-dispatch product hunks
  reverse-applied). Mutual delta = the two `devlyn:resolve/SKILL.md`
  files, 6 lines each — exactly the hypothesis bytes.
- Sonnet 5 parents via the run-owned pinned CLI 2.1.222 (`c66a6cc6…`),
  goal invocation frozen as `Run /devlyn:resolve --no-risk-probes "<goal>"`
  (kills the plan→probe_derive arm-death path the discovery goal's
  output-shape classification would trigger).
- Amended registration-owned watcher: preparation files
  `implement.task-context`/`implement.prompt` allowed; forbidden =
  `implement.stdout`/`implement.stderr`; grace 5000 ms (live SIGINT
  wind-down preflight measured 632 ms); Terra re-proof 5/5 incl. the new
  `preparation_allowed` regression case.
- Mechanical bars: watcher PASS; candidate structural bar via the schema-3
  oracle at `3558b57`; NEW `dispatch_clean == true` for all four arms via
  the registration-owned dispatch scorer (execution-shape
  `bash-codex-dispatch` rule — the literal-match draft false-fired on the
  contract's own preflight in the real 0092 fixture and was corrected +
  re-proven before freeze).
- Blind quality: Fable 5 + Grok 4.5, nonce commitment `bafa1d0c…`, mapping
  bit = low bit of last hex digit of `sha256(nonce + ":" + goal_id)`;
  strict no-loser gate; findings schema `target A|B|both` /
  `severity CRITICAL|HIGH|MEDIUM|LOW` / `axis correctness|scope|autonomy`;
  candidate-only excludes `both`. Duration tripwires ≤1.25 summed /
  ≤1.50 per arm. Infra replacement only before any in-window PLAN Agent
  use; fresh attempt paths.

## Registration attestations (2026-08-05)

- Terra (`gpt-5.6-terra`): amended-watcher re-proof PASS 5/5; dispatch
  scorer built + PROVEN (14 self-test cases + real 0092 fixture).
- R0: Grok 4.5 FREEZE; Fable 5 REVISE (risk-probe death path — adopted);
  Codex gpt-5.6-sol REVISE (worker-visible condition labels, mechanical
  dispatch bar, judge schema, receipt anchoring — all adopted).
- R1 on the amended whole: FREEZE ×3 (Grok, Fable, Codex). Codex's first
  R1 call returned a byte-identical stale re-emission of its R0 answer and
  was ruled invalid on the seat-liveness rule; the liveness-marker rerun
  (`cb68ba943faa`) independently verified current bytes and returned
  FREEZE. Receipts: `iter0094-reg/seats/`.

These attestations froze the experiment; they are not ship credit.

## Ship rule

All bars pass → R1 earns live delivery credit and 0094 records SHIP for
the already-landed bytes. Any bar fails → no ship credit; failure class
routes to a NEW registration (never amendment-in-place).
