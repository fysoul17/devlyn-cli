---
id: "0106-grok-terminal-message-carrier"
title: "Grok 4.6 terminal-message carrier for VERIFY pair output"
kind: product-fix
status: SHIPPED 2026-08-21 — terminal dual-attestation and partial-stream TIMEOUT conservation landed; live Grok 4.6 collection and pyx-cloud Opus 5 + Grok 4.6 VERIFY both PASS
complexity: high
depends_on: ["0080-pair-emission-boundary", "0082-weld-recovery", "batch-b-harness-findings"]
---

# iter-0106 — Grok terminal-message carrier

## Why this iter exists

Pre-flight 0: this removes a real user failure. A live pyx-cloud VERIFY pair
run completed two bounded Grok 4.6 probes and emitted terminal `PASS`, but Grok
CLI 1.0.5 `--output-format json` flattened earlier tool-turn narration and the
terminal answer into one `text` string. The shared collector correctly rejected
that welded string, so the explicit pair route blocked.

Mission 1: this repairs the already-shipped single-task VERIFY/JUDGE pair path;
it adds no parallel-fleet or cross-run substrate.

## Evidence and falsifiable prediction

- Live failing transport: Grok CLI 1.0.5 emits `stopReason: "end_turn"` and a
  narrated aggregate `text` under `--output-format json`; the current parser
  accepts only the registered Codex `EndTurn` envelope and must not recover a
  narrated PASS.
- Current CLI help exposes `streaming-messages-json` as whole-message NDJSON.
- Grok CLI 1.0.5's bundled headless-mode guide defines that stream as one
  `system/init` record, whole assistant/user messages, and a terminal `result`;
  it states that `result.result` is the final assistant-message text.
- Two 2026-08-21 probes, including a real `read_file` tool turn, emitted earlier
  `tool_use` assistant messages separately and exactly one final assistant
  message with `message.stop_reason == "end_turn"`, followed by a successful
  result whose `result` equals that final text.
- R0 counter-review found a carrier-specific timeout edge: unlike aggregate
  JSON, whole-message NDJSON can leave a non-empty partial stream when the
  600-second process budget kills the judge. Without a merge-contract edit,
  that registered budget abort would change from `TIMEOUT` to `BLOCKED`.

Prediction: replacing Grok's aggregate JSON transport with the whole-message
stream and accepting only its uniquely attested terminal assistant text will
make the live Grok 4.6 pair output collectible without accepting any welded,
cancelled, ambiguous, or result-mismatched PASS. Falsifier: any adversarial
stream below is accepted, any existing registered collector capture changes,
or a fresh isolated Grok 4.6 pair run still cannot produce canonical findings.

## Why-chain and violated invariant

1. Why did a successful pair block? The collector received narration plus the
   terminal contract as one string.
2. Why could it not distinguish them? The adapter chose an aggregate transport
   even though the CLI now exposes whole-message turn boundaries.

Violated invariant: adjudication may bind only to an unambiguous terminal
assistant message, never to substring recovery from aggregated conversation
text. The fix therefore belongs at the transport/parser boundary, not in the
pyx-cloud product or a permissive PASS recovery rule.

## Requirements

- [x] R1 — Grok pair invocation uses `streaming-messages-json`; aggregate
  `--output-format json` is removed from the shipped Grok adapter.
  `streaming-json` and `--include-partial-messages` are not used.
- [x] R2 — The shared parser extracts only one final assistant message whose
  `stop_reason` is `end_turn`, followed by one successful terminal result that
  agrees byte-for-byte with the in-order concatenation of that message's text
  blocks. The stream begins with one `system/init`; session identity agrees
  across init, terminal assistant, and result; the result is unique and last,
  has `subtype == "success"`, `is_error == false`, and `stop_reason == "end_turn"`.
- [x] R3 — Prior tool-use/narration messages may exist but are never passed to
  the finding parser. Narrative welded into the final message, multiple terminal
  messages, malformed NDJSON, missing/error/cancelled results, post-result data,
  message/result mismatches, session mismatches, partial-message frames, compact
  boundaries, and unknown record types all reject. Once the first record declares
  this stream shape, extraction either returns or rejects: it never falls through
  to plain JSONL or narrated-envelope recovery.
- [x] R4 — Existing plain JSONL, Codex envelope, narrated NEEDS_WORK recovery,
  fence, dual-document, and terminal-verdict behavior remains byte-compatible.
- [x] R5 — VERIFY documentation names the shared terminal-message rule without
  duplicating parser logic; config, `.claude`, and `.agents` mirrors are exact,
  and the harness lint's critical-path parity list covers the shared judge parser.
- [x] R6 — The already-landed primary findings fail-closed and seat-attributed
  stdout behavior remains green. No duplicate primary-timeout mechanism is
  added; downstream installation must include those current source bytes.
- [x] R7 — A valid pair timeout marker plus a non-empty, result-less partial
  stream remains `pair_judge: TIMEOUT`, not an emission-contract `BLOCKED` and
  never a pair PASS. Parseable completed findings keep their existing behavior.
- [x] R8 — A fresh isolated Grok 4.6 live run is collected through the shipped
  path, and the pyx-cloud VERIFY is rerun with Codex orchestration, Opus 5 as
  primary judge, and Grok 4.6 as pair judge.

## Authorized surface

<!-- devlyn:authorized-surface -->
```json
[
  "config/skills/_shared/judge-output-parser.py",
  "config/skills/_shared/collect-codex-findings.py",
  "config/skills/_shared/verify-merge-findings.py",
  "config/skills/_shared/adapters/grok.md",
  "config/skills/devlyn:resolve/SKILL.md",
  "config/skills/devlyn:resolve/references/phases/verify.md",
  ".claude/skills/_shared/judge-output-parser.py",
  ".claude/skills/_shared/collect-codex-findings.py",
  ".claude/skills/_shared/verify-merge-findings.py",
  ".claude/skills/_shared/adapters/grok.md",
  ".claude/skills/devlyn:resolve/SKILL.md",
  ".claude/skills/devlyn:resolve/references/phases/verify.md",
  ".agents/skills/_shared/judge-output-parser.py",
  ".agents/skills/_shared/collect-codex-findings.py",
  ".agents/skills/_shared/verify-merge-findings.py",
  ".agents/skills/_shared/adapters/grok.md",
  ".agents/skills/devlyn:resolve/SKILL.md",
  ".agents/skills/devlyn:resolve/references/phases/verify.md",
  "benchmark/ceiling/probes/r-weld-0082/test-collector-contract.py",
  "scripts/lint-skills.sh",
  "autoresearch/iterations/0106-grok-terminal-message-carrier.md",
  "autoresearch/HANDOFF.md",
  "autoresearch/DECISIONS.md"
]
```

## Verification

<!-- devlyn:verification -->
```json
{
  "verification_commands": [
    {"cmd": "python3 config/skills/_shared/collect-codex-findings.py --self-test", "timeout_sec": 60},
    {"cmd": "python3 config/skills/_shared/verify-merge-findings.py --self-test", "timeout_sec": 60},
    {"cmd": "python3 benchmark/ceiling/probes/r-weld-0082/test-collector-contract.py", "timeout_sec": 120},
    {"cmd": "bash scripts/lint-skills.sh", "timeout_sec": 600}
  ]
}
```

## Principles check

- Pre-flight 0 — PASS: closes the observed pyx-cloud explicit-pair blocker.
- Mission-bound — PASS: repairs Mission 1 single-task VERIFY/JUDGE.
- No overengineering — replace one transport; add only the parser branch and
  negatives required by the observed transport.
- No guesswork — prediction and raw CLI shapes were recorded before editing.
- No workaround — terminal turn identity replaces aggregate substring recovery.
- Worldclass / production-ready — malformed, ambiguous, failed, and cancelled
  carriers fail closed.
- Best practice — consume the CLI's documented whole-message wire format.
- Layer-cost-justified — no extra model turn or probe; transport only.

## R0 design freeze

Opus 5 and Grok 4.6 independently returned `DESIGN_REVISE`. Both required the
same core invariant: the existing Codex envelope path stays byte-identical, and
the Grok stream can bind only through a unique `end_turn` assistant message plus
an agreeing successful terminal result. Their non-conflicting additions were
adopted: explicit text-block assembly, terminal-on-detect dispatch, no partial
message framing, and parity coverage for the shared parser.

Two apparent disagreements were resolved by concrete existing behavior:

- The 0082 regression matrix remains frozen; this iteration adds a separate
  stream section to that executable without changing existing path matrices,
  corpus expectations, or dated overrides.
- `verify-merge-findings.py` changes only at the observed carrier-specific
  budget edge. A valid timeout marker plus an unparseable partial stream remains
  `TIMEOUT`; completed parseable findings retain the existing merge behavior.
  The already-landed primary fail-closed and seat-attribution branches are not
  modified.

No further design branch is open. Implementation must satisfy R1-R8 literally.

## R1 implementation and closure

The implementation landed in three scoped commits: parser/collector and stream
regressions (`59df4d3`), Grok adapter plus timeout conservation and docs
(`15cba6c`), and exact `.agents` mirror synchronization (`3820023`). The
installed Codex runtime was then refreshed from these source bytes; SHA-256
matched for the parser, collector, merge, and Grok adapter.

Deterministic closure:

- collector and merge self-tests exit 0;
- the additive 0082 regression executable passes 132 checks, including two
  valid whole-message streams and 16 stream negatives;
- all config / `.claude` / `.agents` critical mirrors are byte-identical;
- `bash scripts/lint-skills.sh` exits 0 with all checks passed.

Live closure used Grok CLI 1.0.5 with model `grok-4.6`: an isolated run emitted
exactly `system/init`, one terminal assistant `end_turn` message containing
`PASS`, and one successful final result with the same session and text. The
shipped collector produced zero findings / PASS. The current runtime then
verified pyx-cloud HEAD `18f4259`: mechanical checks PASS, Opus 5 primary PASS,
Grok 4.6 pair PASS, deterministic merge PASS with zero findings. The qualified
financial integration suite passed 117/117 and provenance passed 3/3. A first
merge intentionally blocked when a non-seat diagnostic was named
`opus5-judge.stdout`; removing that derived naming collision left the single
standard pair carrier `grok-judge.stdout` and proved seat-attributed scanning
remains fail-closed rather than silently ignoring ambiguous stdout.

No production deployment was performed: pyx-cloud still requires the owner to
provide current payment-method attestations for the immutable-image rotation
ceremony. The deploy-ready product commit is pushed only after this closure;
the financial gate is not weakened or bypassed.
