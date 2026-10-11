# 0240 s01-h-codex: preserved native protocol audit

The registered native catalog gate **failed**. Both fresh and resumed Codex
peers still received the collaboration namespace despite the recorded
`-c features.multi_agent=false` argument. No peer delegation was observed, but
that does not establish the registered capability restriction. The raw cell
verdict remains **STOP**, `ValueError: whole-run usage PARTIAL`, and
`measurement_eligible=false`. Do not dispatch the next registered cell on the
strength of the successful observations below.

This is a read-only audit of the completed capture, not a model run, evaluator
replay, accounting repair or retrospective product verdict. The corresponding
JSON records source hashes, native evidence locations, command observations and
read-only Docker cleanup checks. Root separately owns the frozen-input and
evidence-manifest integrity audit. Original captures, seals and verdict were not
changed.

Private evidence root:
`/Users/aipalm/.local/share/nx01/0240-live/staged-v1/out-smoke/s01-h-codex`.
Paths below are relative to that root unless stated otherwise.

## Native catalog requirement

Both helper attempt records include `features.multi_agent=false`, read-only
sandbox, approval policy `never`, and `gpt-6-astra` / `max`. Actual initial
inference requests nevertheless declare these six collaboration tools:
`followup_task`, `interrupt_agent`, `list_agents`, `send_message`, `spawn_agent`,
and `wait_agent`.

| Seat | Initial inference request under `cell/trace/` |
| --- | --- |
| Fresh peer | `trace-2722469f-c56f-47da-bc9e-7d4bb189d970-01a12657-256e-7581-8c0b-9d27a83616d9/payloads/4.json` |
| Resumed peer | `trace-ea13db5f-eb9f-4669-930c-01d3665a7869-01a12657-256e-7581-8c0b-9d27a83616d9/payloads/4.json` |
| Owner | `trace-738c1b20-d32a-4aa6-86fe-c99b8de10437-01a12655-325a-7da2-a965-c8842b71b084/payloads/4.json` |

The owner's collaboration catalog is retained, as required. Later incremental
requests do not repeat the `additional_tools` declaration; that omission is not
evidence that the initially supplied tools became unavailable. Native owner
configuration still contains `[features.multi_agent_v2] enabled = true` and
owner child defaults `gpt-6-sol` / `high`. This audit identifies the ineffective
restriction without selecting or implementing a repair.

All three traces contain only their respective root thread. The peer's native
rollout contains three `exec` calls, at lines 13, 24 and 45: source, caller,
instructions and consumer reads through `pwd`, `rg`, `nl` and `cat`. No native
child, recursive independent session, source edit, product-check execution,
delivery or network command appears in those calls. Its observed behavior
respected the prompt restriction, while its available capabilities failed the
stronger pre-registered gate.

## Request, identity and awaited answers

The exact 2,386-character `harness/caller.json` request occurs once in
`cell/work/.devlyn/pair/request.md`. This packet is byte-for-byte identical to
the fresh CLI prompt and the native peer user-message text at rollout line 9.
The original request precedes the candidate diff and raw public-check output;
the raw output matches the preserved public-check log. Owner constraints and
runtime bindings are explicit; no owner interpretation of a successful check is
inserted before those raw inputs.

The owner is session `01a12655-325a-7da2-a965-c8842b71b084`. Both peer calls use
session `01a12657-256e-7581-8c0b-9d27a83616d9`, distinct from the owner. All 32
recorded native inference requests identify `gpt-6-astra` with `max` effort:
27 owner, three fresh-peer and two resumed-peer requests. Both native peer turn
contexts also report the read-only sandbox and `never` approval policy.

| Call | Helper elapsed time | Native result |
| --- | ---: | --- |
| Fresh | 49.68794173099741 seconds | Exit 0; one `turn.completed` |
| Resume | 10.00316925500374 seconds | Exit 0; same session; one `turn.completed` |

Both calls have complete returned answers matching the native capture and native
rollout final messages. The owner awaited exit and read the returned answer
files into its own native transcript: fresh answer at owner rollout line 118,
resumed answer at line 143. The resumed prompt matches native user-message line
41 and explicitly recalls the prior example from unchanged source. Neither
capture contains `turn.failed` or `error`.

All four helper source identity objects—before and after each call—are equal,
including the same HEAD and all 29 recorded files. The two allowed source-file
hashes also match the precheck, delivered commit blobs and final checkout.
`CLAUDECODE` was reported absent before launch; no command removed it.

## Observed checks and local delivery

The owner's public invocation `python -m unittest -q test_calculate_total`
exited 0 and reported seven passing tests. Its raw result is present in the
native owner transcript at line 71 and in
`cell/work/.devlyn/pair/public-check.raw.log`. This records the original run;
the audit did not rerun the source tests.

The fresh peer reported no supported requirement violation and supplied
`calculate_total(9, 50, 10) == 6`: the discounted 4.5 cents round to 5, tax of
0.5 cents rounds to 1, and the sum is 6. The owner wrote the proposed assertion,
recorded its prediction, executed it and preserved exit 0 with
`calculate_total(9, 50, 10) == 6: PASS`. The resumed peer recalled and confirmed
that same example after rereading source. These are observed task checks;
S2 has no hidden oracle, and the runner stopped before its product evaluation.

Read-only Git inspection confirms local commit
`a013a1bcaefdf394c5fc1d4d2a4362a14de0546c`, with sole parent
`922f25a89e3714ab66745b138d2219a8464aa8f7`, adds only `calculate_total.py` and
`test_calculate_total.py`. The common completion helper returned `LOCAL_ONLY`
with `pr: null`. The original task checkout is clean on `main` at that commit;
the temporary delivery branch and worktree are removed. Caller SHA256 remains
`8ac7a46faf798a9ac1a9c6ad62f42de1291da79ce4e80fd55518001c59541c20`.

The native owner checked `/proc` for outstanding helper/peer commands and
recorded an empty list before final response. The enclosing run reports
`EXITED_0`, elapsed 422.45709574999637 seconds and teardown `CLEAN`.
Read-only Docker inspection during this audit independently returned “No such
container” for `devlyn-0231-23c5793fc5f24c8498a0b56e086553e8` and “no such
volume” for `devlyn-0234-tmp-f85f1efc7c394115a9ce0243d0c42226`.

## Limits and disposition

The original STOP lists unreadable Claude-result gaps for the local
`peer-check.json` witness metadata and its custody copy. Accounting diagnosis
is owned separately; this report neither repairs nor regrades that result.
Preserve the raw known lower bound of 1,175,250 input and 17,382 output tokens,
the null whole-run token totals and the unknown residual. Do not derive a
finite whole-run efficiency comparison from this cell.

Independently of that accounting issue, the actual collaboration catalog fails
the registered 0240 requirement. The source observations and successful
fresh/resume transport therefore do not admit this candidate, demonstrate
ordinary automatic activation, or establish efficacy, token savings, latency
improvement or superiority to the bare model. Any treatment repair needs its
own prospective identity and registration; this original cell remains STOP.
