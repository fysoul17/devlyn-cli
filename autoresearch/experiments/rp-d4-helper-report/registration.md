# rp-d4 registration — the helper states cleanup

This registration is written before any measured exposure. Its input
identities are in [registration.json](registration.json); its
`apparatus_commit` is the commit whose files the `inputs` hashes cover. From
this commit on, the prediction, the schedule, the grading, the decision rules
and the raw data are never edited. [DESIGN.md](DESIGN.md) is the contract, and
its full text applies.

## Prediction (frozen in DESIGN.md before smoke)

> Y raises Codex's cleanup claim from ≤ 1/4 (X) to ≥ 3/4, with every
> delivery passing and no other category losing ground.

## What runs

- **Arms.** X = registry `devlyn-cli@4.2.22` (SHA-256 `799c6091…ca61`,
  registry integrity verified). Y = X with `task-complete.py` and
  `task-completion.md` replaced by candidate commit `c048fd31` (blobs
  `c08c1e80…` and `b0805de7…`; Y SHA-256 `248e7cca…8b01`). The pack check
  confirmed the trees differ by exactly those two paths.
- **Token gate (precondition).** Whole `task-completion.md` against
  `cbc33be9`: Claude `count_tokens` 4867 → 4862, o200k proxy 2979 → 2976,
  bytes 14309 → 14287.
- **Prompt.** `common.txt` unchanged in every slot (SHA-256 `2ccc7f6a…50cf`).
- **Engines.** Codex 0.162.1, `gpt-6-sol`, effort high, one Codex account
  (`9ca44b8a38f2`). Claude guard: Claude Code 2.1.296, `claude-opus-5-5`,
  effort max, one Claude account. One image
  (`sha256:a41cec60…2c1a`).
- **Schedule.** m01–m08: BV X, Y, Y, X; Z0 X, Y, Y, X; then g01 (Claude Y,
  BV) and g02 (Claude Y, Z0). Repositories `fysoul17/rpd4-20261017a-<slot>`.
- **Network.** Benchmark hard rule 5: host network fixed, VPN client apps
  quit (both VPN services report disconnected), a watcher logs
  default-route changes.

## Success, decision and stopping

As in DESIGN.md "Grading" and "Decision". Primary: Codex cleanup SUPPORTED
by both reviewers per arm. Ordered branches: INCONCLUSIVE (STOP, incomplete
dispatch, failed delivery including any `merge_refused`, missing
adjudication, UNKNOWN usage), BASELINE MOVED (X cleanup ≥ 2/4), REJECT
(Y cleanup ≤ 1/4), ADOPT (all conditions, including the 0232 §6 cost,
dominance and strict-improvement rules and both Claude guard reports
passing), HOLD, MIXED. Renewal only between complete Codex pairs or after
m08, on identical accounts.

## Qualification

Smoke attempt 1 qualified both cells (SM). Reports are ungraded and change
nothing above.

| Cell | Owner s | Input | Output | Usage | Delivery | Repository |
|---|---:|---:|---:|---|---|---|
| Codex X | 120.9 | 512,048 | 6,531 | COMPLETE | passed | archived, deleted (404) |
| Codex Y | 118.1 | 539,098 | 6,239 | COMPLETE | passed | archived, deleted (404) |

The Y cell passed the deterministic cleanup check: one helper `complete`
call, whose `cleanup` sentence ("Removed the task worktree; deleted the local
task branch; deleted the remote task branch; emptied the task scratch.")
equals the sentence rendered from that call's action record and agrees with
the final resources.

**Smoke evidence known at registration.** Neither report named cleanup. The
X report ended "PR #1 was merged, the local branch was fast-forwarded, and
the checkout is clean. Nothing unresolved." The Y report ended "The change
was merged through PR #1, the checkout is clean, and nothing remains
unresolved." It did not quote the helper's `cleanup` sentence. One
ungraded observation per arm on an unrelated task; the prediction is
unchanged.

No default-route change occurred during smoke. The watcher logged no
default route between 01:22Z and 02:07Z (host sleep), before smoke started.

## Review

1. **Before exposure.** Astra ultra and Grok 4.7 review this registration.
2. **After the run.** Both judge every report checklist against the raw
   evidence, and both review the write-up.
3. **Stopping.** Review stops at SHIP with no HIGH finding.
