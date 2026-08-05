---
id: "0094-r5-regate"
title: "R5 re-gate: live four-arm matrix for the native foreground PLAN dispatch"
kind: reliability
status: CLOSED 2026-08-05 — matrix RAN (first past controls); candidate structural bar FAILED at candidate-discovery (delivered-prompt-digest-mismatch, one-byte trailing-LF strip); NO SHIP CREDIT; R1 not refuted
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

## TERMINAL VERDICT (2026-08-05) — NO SHIP CREDIT; R1 not refuted

The matrix ran to completion — the first time this iteration line got past
controls. All four arms: watcher PASS, empty categories, SIGINT-only stop
(grace 5000 ms; zero escalation), quiescent groups, `.devlyn` allowlist
clean, source baselines byte-match. The 0092 death boundary
(`implement.task-context` pre-transition) was crossed cleanly by all four
arms, and the risk-probe kill path stayed closed (`high_risk: false`,
probes disabled in every arm). Sessions are 100% `claude-sonnet-5`.

**Deciding bar — candidate structural, FAILED at candidate-discovery
(0260532c).** The parent delivered the PLAN prompt with the render's
single terminal `0x0a` stripped: delivered 10,015 bytes / sha `c9d8a32e…`
vs disk+state 10,016 bytes / sha `daf10207…`; every common byte matches.
Serialization artifact is ruled out: candidate-simple (0e9f44a7) in the
same matrix delivered byte-exact INCLUDING the trailing LF (all three
digests `ff7bda46…`), and the failing session preserves trailing LF on
other tool_use string inputs (e.g. `Write.content`). The digest conjunct
is tested (oracle self-test) and satisfiable (candidate-simple) — a real
delivery failure of the contract-warned `$(cat …)` class. Live candidate
delivery compliance 1/2 against a pre-committed 2/2 bar → NO SHIP CREDIT.
R1 is NOT refuted: one candidate arm proved the exact call shape works
byte-perfectly (mode absent, `run_in_background:false`, ACCEPTED, digest
match). Adjudication: Grok CONFIRM, Codex AMEND (P1/P3/P4 confirm; P2
precision corrections — all three byte-verified and folded). Next
registration owns the failure class: **PLAN delivery byte-fidelity**
(the 0089/0090 delivery-compliance lineage, now measured in the native
structured-field shape).

**Instrument defects found at first contact (follow-ups, scored against
no one):**

- **Oracle evidence scoping**: current-format live sessions carry
  non-message JSONL records; the collector flags each as
  `message-not-object` and evidence-completeness caps classification at
  INCOMPLETE — so no live arm can ever score COMPLETE. Proof by
  execution: full-dir replay of retained 0091 Canary 1 — the artifact the
  frozen gate requires to "remain COMPLETE" — scores INCOMPLETE with 82
  such issues (the 284-assertion self-test's C1 is a curated minimal
  fixture). Candidate-simple: 110 issues + 1
  `agent-subagent-type-malformed`. Fix scope: evidence scoping for live
  session formats + gate retained canaries on full-dir replay +
  resolve `subagent_type` absent-key (oracle self-test line 1474) vs the
  freeze's "leave selection to the parent / no key-set pin" prose.
- **Dispatch scorer artifacts clause**: fired `implement-carrier-mutated`
  on all four arms because the product spawn writer
  (`state-phase-write.py:1350`) always emits
  `artifacts: {"findings_file": null, "log_file": null}`; the senior
  tested watcher explicitly allowlists exactly that skeleton and judged
  all arms "start-only carrier" live. Untested edge (scorer self-test
  covered `worker_dispatched: true` only), unsatisfiable against the
  writer — align the clause to the watcher allowlist. All other scorer
  rules: zero findings on all arms (no wrapper executions, no non-PLAN
  Agent uses, no IMPLEMENT headings, no capture artifacts).

**Blind quality axis (reported; cannot restore credit):** unblinding
(commitments verified) gave A=control / B=candidate on both goals. Fable 5:
tie/tie, attributions file:line-correct. Grok 4.5: simple tie; discovery
emitted winner=A(control) — literal no-loser reading FAIL — but all five
of its findings carry mechanically-proven inverted A/B attributions (5/5,
`judges-crosscheck.md`), so its content-level preference was the actual
candidate. Both readings recorded; neither judge emitted CRITICAL/HIGH.
No judgment rerun (frozen rule). Duration tripwires PASS: candidate sum
0.866× control (≤1.25); per-arm 0.873 / 0.864 (≤1.50) — candidate faster
on both goals.

**Also of record:** control arms' own captured calls varied — 
control-simple omitted `mode` while control-discovery supplied
`mode:"bypassPermissions"`, and control-simple also digest-mismatched its
delivery — live evidence that delivery variance is a both-conditions
product problem, strengthening the delivery-fidelity registration's
motivation. Receipts: `~/.local/share/nx01/iter0094-reg/` (git; seats/,
replay/, unblinding.json, judges-crosscheck.md),
`~/.local/share/nx01/iter0094-r5/` (arms, worktrees, goals, driver).
