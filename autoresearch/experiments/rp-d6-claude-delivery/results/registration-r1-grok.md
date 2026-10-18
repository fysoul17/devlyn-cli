- `apparatus_commit` `0711150b4f3de9fbee5e132cc6911ed180dbd79c` matches `notes/apparatus-commit`. The branch tip is the child `4be26451` (`rp-d6: registration before measured exposure`). The hashed input set does not include `registration.md` or `registration.json`.
- Smoke-seal digests for the rp-d6 apparatus and the overlapping rp-d1 through rp-d4 files match `inputs`. `common.txt` is `2ccc7f6a…50cf`.
- `release/arms.json` and `stage/arms/arms.json` are the same document. The seal hashes that file as `f974433a…2e0d`, which is `live_inputs["arms.json"]` and `token_gate.arms_sha256`.
- X `799c6091…ca61` and Y `b939ee9b…2f1e`, both integrity strings, both manifest digests, candidate `15ded3a7…da91`, and the three blob ids match `arms.json`, both runtimes, and the smoke schedule. The seal hashes the stage tarballs to those same digests. CLAUDE.md and AGENTS.md share one blob id.
- Models cache `8597e51f…0a49` matches both runtimes, the seal, and attempt 1. Token-gate rows and `passed: true` match `registration/token-gate.json` and `counts.json`. Both runtimes and attempt 1 bind that gate file as `2cd8375a…a69c`.
- Image `sha256:f87a4753…b120` matches `notes/image.id` and both runtimes. Codex and Claude auth-manifest digests match the runtimes, the schedule, and the seal’s manifest entries.
- `runtime_sha256` `cdf78665…3897` and `smoke.schedule_sha256` `bf20776d…bafa` appear only in `registration.json`. Dispatch froze the smoke runtime at `9be6aaf1…1701`; attempt 1 and the seal record the post-smoke runtime as `4f9bc6e3…0ead`. Verdict digests in the registration match `inherited_verdict_sha256` on the schedule. This session did not recompute SHA-256 from raw bytes.

## Frozen rules and Y paths

The prediction quote matches DESIGN. The schedule is m01–m08 as BV X,Y then Y,X and Z0 X,Y then Y,X, then g01–g06 on Y with the DESIGN engines, efforts, suffixes, and g06 `repository: null`. Decision order is INCONCLUSIVE, UNSAFE, REGRESSION, NO FAILURE OBSERVED, REJECT, ADOPT, HOLD, MIXED. Cost is m01–m08 only. Renewal stays on identical accounts at the boundaries in `stage.py`. DESIGN’s full text is incorporated, including the spare-smoke stop.

The Y-path note matches the trees. Inside each arm, `CLAUDE.md` and `AGENTS.md` are the same bytes. Between arms, the Delivery bullet gains `the user asks you to `, and the North Star loses `This contract serves one goal: `. `runtime-principles.md` changes only in that North Star sentence. `bin/instruction-templates.json` is the same 988-line file in the worktree, X, and Y (same control-manifest digest `bf30ed4d…f6e5`). `package.json` `files` has no `.agents` entry, and the package manifest has no `.agents` path. The worktree mirror `.agents/skills/_shared/runtime-principles.md` has the new North Star. `scripts/test-windows-portability.py` carries the new Delivery sentence and stays outside the shipped set, which DESIGN already states. Rendered installs show the same two wording edits. The marker hashes differ and stay the same length. Gate counts are AGENTS.md Claude 1504 → 1499 and o200k 940 → 937, CLAUDE.md 16 → 16 and 5 → 5, with the 11-byte `@AGENTS.md` import labeled as such. Y is at or under X, and `passed` is true.

## Smoke

Both cells are SM, arm Y, effort `high`, and `smoke_qualification.status` is `PASS`. DESIGN’s checks all hold: owner `EXITED_0`, release binding `MATCH`, Claude effort `MATCH`, Codex effort `NOT_APPLICABLE`, usage `COMPLETE`, archive present, deletion `DELETED` with HTTP 404.

| Cell | Owner seconds | Input | Output | Delivery evidence |
|---|---:|---:|---:|---|
| Claude | 86.1526, reported 86.2 | 262,354 | 4,530 | merge `MERGED`, anchor `7aee6ed…` equals archived `main` |
| Codex | 130.5588, reported 130.6 | 555,721 | 6,344 | merge `MERGED`, anchor reconciled to archived `main` |

## Ranked findings

**HIGH:** none.

**MEDIUM:** none.

**LOW:** Both smoke cells leave `false_completion` and `severe_regression` at `ADJUDICATE`. Qualification does not read those fields. Mechanical publication is merged and reconciled, and the registration’s delivery sentences match that record. No registration edit is required before exposure.

**LOW:** `notes/network.txt` points the route watcher at `~/.local/share/nx01/rp-d5-live/notes/route-watch.log`. That log’s last line is `2026-10-17T23:32:24Z` interface `en0`. A change-only watcher stays quiet while the route is stable. Confirm the process is still running before the measured dispatch.

VERDICT: SHIP
