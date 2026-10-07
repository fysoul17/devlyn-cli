# Pair reasoning

You and one peer session work out the change together in at most three peer
turns. You alone edit the workspace; the peer reads it and argues with you.

Peer: a fresh session of your own engine, at its CLI's configured default
model and effort. If the peer cannot start or a turn fails, report that and
continue solo.

## Turns

1. **Independent positions.** Before you share your approach, send the peer the
   request verbatim. Ask for the invariant it would protect, its approach, and
   one to three executable counterexamples: each a test or command, the request
   clause it enforces quoted, and the expected result. Write down your own
   position the same way before you read its answer.
2. **Reciprocal development.** Send your position, your critique of its
   approach and checks, and your first implementation with check results. Ask
   it to answer your reasoning and the artifact, revising or defending its
   position. Adopt what the evidence supports.
3. **Closure.** When your checks pass on the final source, send the final diff,
   the check results and any unresolved claim. Fix and verify a blocker it
   supports with evidence; report one you reject, with your evidence. There is
   no fourth turn.

## Rules

- Settle disagreement by running the check or citing source, never by agreement.
- A claim or check stands only on the request's text and existing behavior.
  Reject one that adds a requirement, quoting the clause; repair an invalid
  check rather than weakening a valid one.
- Recovery must not hide a failure the request requires reporting.
- Run each turn in the foreground: give it at most 540 seconds (Codex:
  `CODEX_MONITORED_TIMEOUT_SEC=540`; Claude: `timeout 540` where available),
  wait up to 600 seconds, and check that it ended successfully. Never end your
  session while a turn runs.
- Final evidence comes from the submitted source; an edit after a check makes
  that check stale.

## Commands

Run them from the repository root. Keep each turn's text and the peer's
answer under `.devlyn/pair/` (ignored), one file per turn: `turn1.md`,
`turn2.md`, `turn3.md`.

Codex peer, through `codex-monitored.sh` beside this file (`<dir>`) — the first
turn, then each later turn in the same session:

```
CODEX_MONITORED_TIMEOUT_SEC=540 bash <dir>/codex-monitored.sh --json -s read-only -C . "$(cat .devlyn/pair/turn1.md)" > .devlyn/pair/peer1.jsonl
CODEX_MONITORED_TIMEOUT_SEC=540 bash <dir>/codex-monitored.sh resume --json -c sandbox_mode=read-only <thread_id> "$(cat .devlyn/pair/turn2.md)" > .devlyn/pair/peer2.jsonl
```

`<thread_id>` is in the first turn's `thread.started` event; each answer is the
last `agent_message` item of a run that ends in `turn.completed`.

Claude peer — choose a new UUID for the first turn:

```
claude -p --session-id <uuid> --tools Read,Grep,Glob --permission-mode dontAsk --output-format json < .devlyn/pair/turn1.md > .devlyn/pair/peer1.json
claude -p --resume <uuid> --tools Read,Grep,Glob --permission-mode dontAsk --output-format json < .devlyn/pair/turn2.md > .devlyn/pair/peer2.json
```

Each answer is `result` when `is_error` is false.
