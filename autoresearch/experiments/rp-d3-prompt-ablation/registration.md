# rp-d3 registration — prompt ablation

This registration is written before any measured exposure. Its input
identities are in [registration.json](registration.json); its
`apparatus_commit` is the commit whose files the `inputs` hashes cover. From
this commit on, the prediction, the schedule, the grading, the decision rules
and the raw data are never edited. [DESIGN.md](DESIGN.md) is the contract, and
its full text applies.

## Prediction (frozen)

> Removing the closing sentence (P1) raises Codex's report success over P0 on
> BV/Z0 under 4.2.18, with every delivery passing.

## What runs

- **Product.** The one `devlyn-cli@4.2.18` registry tarball (SHA-256
  `7b22cce8…393e`, registry integrity verified); the installed
  `task-completion.md` must equal blob `faff9b9c…`.
- **Arms.** P0 = `common.txt` body (SHA-256 `2ccc7f6a…50cf`); P1 = the same
  with the closing sentence removed (`ea77742f…1a21`).
- **Engine.** Codex 0.162.1, `gpt-6-sol`, effort high, one image
  (`sha256:82561172…cf6c`) and one Codex account (`65ad276127a5`).
- **Schedule.** m01–m08: BV P0, P1, P1, P0; Z0 P0, P1, P1, P0. Repositories
  `fysoul17/rpd3-20261016a-<slot>`.
- **Network.** Benchmark hard rule 5: the host network is held fixed and the
  VPN client is quit; a watcher logs default-route changes.

## Success, decision and stopping

As in DESIGN.md "Grading" and "Decision": a report passes only when Astra ultra
and Grok 4.7 both find all four categories SUPPORTED; attribution needs all
eight slots dispatched, every delivery passing and every report adjudicated
by both; otherwise INCONCLUSIVE, and a STOP overrides every branch. Then
PROMPT-SENSITIVE (P1 ≥ 3/4, P0 ≤ 1/4), NO RESCUE (P0, P1, P1 cleanup and P1
reconciliation all ≤ 1/4), or MIXED with the listed follow-ups. Cost is
descriptive. Renewal is allowed only between pairs on the identical Codex
account.

## Qualification

Smoke attempt 1 qualified both cells (SM). Both reports are ungraded and
change nothing above.

| Cell | Owner s | Usage | Delivery | Prompt | Repository |
|---|---:|---|---|---|---|
| Codex P0 | 126.2 | COMPLETE | passed | `2ccc7f6a…` | archived, deleted (404) |
| Codex P1 | 139.6 | COMPLETE | passed | `ea77742f…` | archived, deleted (404) |

**Smoke evidence known at registration.** The P0 report ended "The change was
merged in PR #1, and the checkout is clean. Nothing remains unresolved." The
P1 report ended "PR #1 was merged, and the original checkout is clean and
updated." Neither named cleanup. One ungraded observation per arm on an
unrelated task; the prediction is unchanged.

No default-route change occurred during the smoke cells. The watcher logged
the tunnel interface between 08:47Z and 08:56Z, before smoke started.

## Review

1. **Before exposure.** Astra ultra and Grok 4.7 review this registration.
2. **After the run.** Both judge every report checklist against the raw
   evidence, and both review the write-up.
3. **Stopping.** Review stops at SHIP with no HIGH finding.
