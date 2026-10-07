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
- Wait for each turn in the foreground with a 600-second timeout, and check
  that it ended successfully. Never end your session while a turn runs.
- Final evidence comes from the submitted source; an edit after a check makes
  that check stale.

## Commands (from the repository root; the turn text in `turn.md`)

Codex peer, through `codex-monitored.sh` beside this file — first turn, then
each later turn in the same session:

```
DEVLYN_CODEX_PROMPT_FILE=turn.md CODEX_MONITORED_TIMEOUT_SEC=600 bash <dir>/codex-monitored.sh --json -s read-only -C . - > peer.jsonl
DEVLYN_CODEX_PROMPT_FILE=turn.md CODEX_MONITORED_TIMEOUT_SEC=600 bash <dir>/codex-monitored.sh resume --json <thread_id> - > peer.jsonl
```

`<thread_id>` is in the first `thread.started` event; the answer is the last
`agent_message` item of a `turn.completed` run.

Claude peer — choose a new UUID for the first turn:

```
claude -p --session-id <uuid> --tools Read,Grep,Glob --permission-mode dontAsk --output-format json < turn.md > peer.json
claude -p --resume <uuid> --tools Read,Grep,Glob --permission-mode dontAsk --output-format json < turn.md > peer.json
```

The answer is `result` when `is_error` is false.
