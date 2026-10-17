The registration matches the live stage on arms, schedule, accounts, image, and smoke qualification. One MEDIUM remains: the Claude token count in the registration disagrees with the frozen design. No HIGH finding.

## MEDIUM

The registration records the token gate as Claude `count_tokens` 4867 → 4862 (`registration.md` and `registration.json` `candidate.token_gate.claude`). `DESIGN.md` records 4867 → 4860, and `README.md` points at that design figure. o200k 2979 → 2976 and bytes 14309 → 14287 agree in the design and the registration. Design review round 5 shipped the design with 4860. The registration gives no recount that replaces it. The prediction, schedule, and decision rules are unchanged either way: both candidate counts are below the control. Reconcile the Claude count in the registration text with `DESIGN.md` before that sentence is quoted as the frozen gate.

## LOW

`registration.json` `smoke.verdicts` equals `inherited_verdict_sha256` on `rp-schedule.json` and on each `rp-verdict.json`:

- `smoke-codex-X`: `8046081017ff194df8db0a2f3380a71b9f9fbd762daf775fd393c949689ec0d7`
- `smoke-codex-Y`: `c456b1233dd994196064c04ecf6a4786edc4232f6682b8dd5111647633aa11b3`

`~/.devlyn/rp-d4-runs/20261017a/attempt-1.json` binds the wrapper files `rp-verdict.json` at `2f994808…` and `fb930862…`. Those are different artifacts. The schedule already carries qualification, archive, and 404.

## Identities

`notes/apparatus-commit` is `13e6b9f9db9fd13be7a24fafe694537401d1e50a`. Reflog: that commit is the parent of HEAD `b6ec4d169ea6f47b3ee2ab7a1bf507b46db050a8` (`rp-d4: registration before measured exposure`, 2026-10-17 02:20:36Z). The inputs list omits the two registration files, which this commit adds.

These registration fields match `runtime-measured.json`, `arms/arms.json`, both smoke `plan.json` files, `notes/image.id`, and `build/image.id`:

- Run `20261017a`, phase `measured`, stage `output/` empty.
- X `799c6091…ca61` / manifest `ae0f0baf…340d` / integrity `sha512-PsTQkz…`; Y `248e7cca…8b01` / manifest `f90b7e84…6feb` / integrity `sha512-3woak0…`.
- Candidate `c048fd3122f408da01d9aeed4a86f410f6053a95`, blobs `c08c1e80…` and `b0805de7…`.
- Image `sha256:a41cec60…2c1a`. Codex account `9ca44b8a38f2`. Claude account `9f2f3a391923`, `ea65f3b4f086`. Auth manifest hashes match the runtime.
- Prompt `2ccc7f6a…50cf` on both smoke plans and on `common.txt` in `inputs`.
- `live_inputs` `arms.json` `7bf03480…` matches `attempt-1.json` `arms_sha256`. `models_cache.json` `aee6807a…` matches `models_cache_sha256`. X/Y tarball hashes match the release SHA-256 fields.
- `tasks.json` pins Codex `gpt-6-sol` effort `high` and Claude `claude-opus-5-5` effort `max`. Smoke plans ran `gpt-6-sol` at `high`. The image digest is the Dockerfile build that asserts Codex 0.162.1, Claude Code 2.1.296, and gh 2.83.2.

SHA-256 of each `inputs` path was not recomputed from `13e6b9f9` and from HEAD in this session. The cross-file identities above are what the live JSON records.

## Prediction, schedule, decision, stopping

The prediction quote matches `DESIGN.md`. The ten slots are BV X, Y, Y, X, then Z0 X, Y, Y, X, then Claude Y on BV (`g01`) and Z0 (`g02`). Repositories are `fysoul17/rpd4-20261017a-<slot>`.

Decision order matches the design: INCONCLUSIVE (incomplete dispatch, failed delivery, `merge_refused`, missing adjudication, STOP, UNKNOWN usage), then BASELINE MOVED (X cleanup ≥ 2/4), REJECT (Y cleanup ≤ 1/4), ADOPT (0232 §6 cost, dominance, strict improvement, both guards), HOLD, MIXED. Renewal is only between complete Codex pairs or after `m08`, on the same accounts (`stage.py` allows completed length 0, 2, 4, 6, or 8).

## Smoke

Attempt 1 is `QUALIFIED`. Both cells are SM, `usage` COMPLETE, `delivery_pass` true, `merge_refused` false.

| Cell | Owner s | Input | Output | Archive / 404 |
|---|---:|---:|---:|---|
| Codex X | 120.910 → 120.9 | 512,048 | 6,531 | `DELETED`, HTTP 404, archive present |
| Codex Y | 118.112 → 118.1 | 539,098 | 6,239 | `DELETED`, HTTP 404, archive present |

Y has one sealed `complete` call, `cell/helper-actions/291-1.json`, helper `e8fa246c…`, same hash as the observer binding. Native stdout carries the same object. Actions: `ran`, `linked`, worktree removed, local ref deleted, remote branch deleted; scratch `CLEAN`. Checklist resources are all absent and `scratch_files` is empty. The rendered sentence is `Removed the task worktree; deleted the local task branch; deleted the remote task branch; emptied the task scratch.` That is the helper `cleanup` field. `smoke_qualification.status` is `PASS` with `calls: 1`.

Neither `final.txt` contains `cleanup`. The quoted endings match both reports. Y does not quote that sentence. Smoke stays ungraded.

Route log: `en0` at 2026-10-16 23:22:43Z, `none` at 2026-10-17 01:22:22Z, `en0` at 02:07:25Z, no later line. Smoke X ran 02:13:47Z–02:15:48Z and Y 02:16:55Z–02:18:53Z, after the route returned. The log does not record VPN service state.

VERDICT: SHIP
