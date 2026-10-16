REVISE. A live Claude guard can seal its OAuth bearer token into graded evidence, and a non-direct helper invocation can drop `merge_refused` so that slot still counts as a passed delivery.

Memory tools were unavailable. The README offline pytest loop was not executed in this session, so this review does not claim a green suite.

## HIGH

The pre-seal scanner needles the selected snapshot's Codex `access_token`, `refresh_token`, and `id_token`, then the GitHub PAT. Guard dispatch points that snapshot at the Claude auth directory, so the bundled `codex.json` is covered. `claude.env` is not. `CLAUDE_CODE_OAUTH_TOKEN` is injected with `--env-file` and is readable inside `g01` and `g02`. If that value lands in any slot file, `cell.seal` still writes the evidence manifest and the slot can be graded. A Codex hit writes `codex-scan.json` (`status`, `revocation_required` only), skips the manifest, and the runner forces `STOP`.

Fix in the rp-d4 scan wrapper, for `auth_engine == 'claude'` only: read the access token with the private reader and run the same streaming, filename, symlink, and git-object scanner before the inherited seal. On a hit or a scan failure, write a marker with `status` and `revocation_required` only, raise a fixed string that contains no token bytes, and treat that marker like `codex-scan.json`. Add a guard test parallel to `test_guard_selected_codex_snapshot_is_scanned_before_sealing` that plants the synthetic Claude token in a slot file and asserts the seal aborts, the manifest is absent, and the token is absent from the exception and stdout.

## MEDIUM

Measured and guard cells have no observer, so `merge_refused` is decided only by `shell_complete`. A direct `python3 task-complete.py complete`, including `bash -lc` and the Claude Bash tool, is recognized, and the tests lock that. These forms are treated as "not an invocation," so a refusal in their output is ignored and a later successful `complete` can set `delivery_pass`:

- `python3 -c '...'` when `task-complete.py complete` appears only inside the code string
- shell nesting deeper than 4 (`depth > 4` returns false)
- a `shlex` split error (also returns false)

Code-mode already fails closed on an unresolved `exec_command` / `shell_command`. The shell path does the opposite. That can turn a required INCONCLUSIVE into a graded delivery and then into ADOPT, HOLD, or MIXED.

Fix: if the raw command contains `task-complete.py` and `complete` and parsing gives up (depth, `shlex`, or a `python -c` body), raise `ValueError` so the slot becomes STOP. Keep echo and `--help` as non-invocations. Add those three cases next to `test_shell_c_payloads_are_parsed_without_treating_echo_as_execution` and `test_code_mode_unparsed_helper_forms_preserve_refusal_detection`.

## LOW

`sitecustomize.observe` is uncaught. A missing `actions` dict, a `json.dump` failure, or `open('x')` raises inside the profile hook, which can change the Y-smoke helper process. Qualification still fails closed when stdout and action records disagree, so this cannot qualify a bad sentence. Catch inside `observe`, leave the helper's locals and return value alone, and let the missing record fail qualification.

`decision` treats a missing `merge_refused` key as false (`.get(..., False)`). The live runner writes the key on every dispatched, non-revoked slot, and a qualification error becomes STOP, which is already INCONCLUSIVE. Require the key on every dispatched slot before any branch; a missing key is INCONCLUSIVE. Cover it in `test_inconclusive_precedes_baseline_moved`.

## Checked, and holding

Arms. X is a byte copy of the registry tarball after SHA-256, `sha512-` integrity, and `package.json` `devlyn-cli` `4.2.22`. Y is a deterministic PAX/gzip repack (mtime 0) of exactly `config/skills/_shared/task-complete.py` and `config/skills/_shared/task-completion.md`. Manifests may differ only on those paths; type and mode stay equal; both files must change; each Y git blob id must match the candidate commit. `package/../`, absolute paths, and `package/./alias` are rejected. `binding` checks every installed copy of both files at prepare and again at launch.

Observer reach. `prepare` installs `sitecustomize` and prepends `/harness` only when `phase == 'smoke'` and `arm == 'Y'`, and `install_observer` also requires Codex and SM. Measured and guard plans stay on `src:/control/python` and never get the file. The hook returns unless the event is a return from `complete` in the bound helper. On that path it reads `actions` and `json.dump`s a new record; `sort_keys` does not reorder the helper dict. The subprocess test checks that the captured record equals printed stdout and that stderr is empty.

Schedule. `m01`–`m08` are BV X,Y; BV Y,X; Z0 X,Y; Z0 Y,X, then `g01` BV Y and `g02` Z0 Y. Repository names are `fysoul17/rpd4-<run-id>-` plus those fourteen suffixes, and the URL regex is the same set. Smoke attempts are only 1 and 2. A failed smoke or failed Y qualification stops the schedule; measured staging requires both selected smokes qualified with archive, deletion, and HTTP 404. `--through-pair` 1..4 pauses on the Codex prefix; omitting it runs both guards. Renewal is allowed only at even completed counts 0, 2, 4, 6, and 8, with the same Codex account, the same Claude account, and the same Codex identity inside the Claude snapshot. Mid-pair, between `g01` and `g02`, a stopped schedule, and a snapshot inside the stage are refused.

Credentials written by the apparatus. Runtime JSON, preflight reasons, scan markers, and Docker argv carry paths and hashes. Codex preflight does not call the Claude profile service. The 6300 s floor is Claude-only (`6299` refused, `6300` and `6301` allowed), including a replaced Claude snapshot at renew; an unchanged Claude snapshot is checked again by guard preflight.

Decision. `summarize.decision` follows DESIGN order: INCONCLUSIVE unless all ten slots are dispatched, every delivery passed, both reviews are PASS or FAIL, usage is COMPLETE, and no `merge_refused`; STOP and UNKNOWN usage hit that gate before BASELINE MOVED. Then X cleanup ≥ 2/4, Y cleanup ≤ 1/4, ADOPT, HOLD, MIXED. Cost matches 0232 §6: `S_Y = 0` fails, even against `S_X = 0`; `S_X = 0 < S_Y` passes by dominance with no raw-sum comparison; otherwise each of wall, input, and output per success is Y ≤ X over every dispatched Codex attempt. Strict improvement is `S_Y > S_X` or one strictly lower per-success cost; three-way ties HOLD. Missing wall on a required comparison is INCONCLUSIVE. FALSE from either reviewer on any Y slot, including the guards, blocks ADOPT. Guard pass is both guards and all four categories SUPPORTED by both reviewers. Guard report failure is MIXED and is not given a cause. Codex tallies exclude smoke and the guards.

The offline tests, as written, lock those holding paths: pack identity, schedule and repo names, smoke consume/spare, through-pair and renew, the 6300 boundary, the guard Codex-token scan, observer placement, and the ordered decision branches including dominance, FALSE, `merge_refused`, and guard pass. They do not cover the HIGH or the MEDIUM.

VERDICT: REVISE
