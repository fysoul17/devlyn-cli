# 0244 s01 native protocol audit

The observed operational transport, native accounting, source/check, and local-delivery evidence supports the untouched **CHECKS_PASS / COMPLETE** result. Identity and peer policy are MATCH with no gaps or violations, and teardown is CLEAN. This is forced S2 smoke, with `measurement_eligible: false` and assessment `NOT_REQUESTED`; it supplies no efficacy result or hidden semantic oracle.

Evidence root: `/Users/aipalm/.local/share/nx01/0244-live/out-smoke/s01-p-codex`. Pair records are under `cell/work/.devlyn/pair/calculate-total-20261010/`. This independent audit wrote only this report and its accompanying JSON. The prior 0242 s03 verdict remains **STOP / PARTIAL**, with its original lower bounds, and is included in the protected hash set.

## Actual native identity, requests, and tools

The owner is Codex `gpt-6-astra` / `max`, session `01a126d0-2a0e-73d0-92d5-eb29f0daa618`. The independent Claude peer uses session **`0bac0e05-98d8-487a-a11a-26a8df35ef2b`** for both calls.

Both helper argv records request `claude-opus-5-5`, effort `max`, `--tools Read,Grep,Glob`, `--permission-mode dontAsk`, and empty strict MCP configuration. The actual native transcript independently records model `claude-opus-5-5`, `effort: max`, and `perTurnEffort: max` throughout. Both native envelopes are `result/success`, have `is_error: false`, the same session ID, nonempty usage, and no permission denials. Each native result text matches its retained final-answer file.

The full fresh and resumed prompt strings match their helper argv and prompt digests, and appear exactly in the native transcript's user rows **3** and **41**. This binds the request actually delivered, beyond requested argv.

The original 2,386-character caller request appears once as literal multiline text at fresh-prompt character 351. The prompt then includes original owner instructions at 2,738 and the verbatim caller JSON at 3,448, which repeats the caller request in escaped form. The candidate diff starts at 6,150, relevant source at 8,167, raw public checks at 9,912, and review task at 10,140. No owner conclusion precedes the raw evidence. The leading paragraph restricts the peer's role.

Observed native tools are limited to three Read calls, one Glob, and one Grep during fresh review, followed by one Read of `calculate_total.py` during resume. No Bash, edit, check execution, delegation, sidechain, or descendant session appears in the retained native inventory. This states configured restrictions and actual tool use, not an unrecorded provider tool-catalog or security-boundary proof.

Fresh completed exit 0 in **374.50967158700223 seconds**; resume completed exit 0 in **9.820799588000227 seconds**. CLAUDECODE was reported absent before both launches in presence-only marker records; no observed operation removed it or exposed its value.

## Stable source and awaited answers

Fresh-before, fresh-after, resume-before, and resume-after identities are identical: **29 files**, baseline HEAD `a2f04a58490e9b956479caf132c037b21f7bd92b`. Every retained final file hash still matches that identity. The caller snapshot equals the retained caller contract, and Git configuration matches its saved baseline hash.

| `run/stdout` evidence | Observation |
| --- | --- |
| Line 26, `item_12` | Owner public check ran: seven unittest methods passed, exit 0. |
| Line 44, `item_14` | Fresh helper returned a completed receipt, exit 0. |
| Line 46, `item_25` | Owner read the entire fresh answer and result identity. |
| Line 51, `item_28` | Same-session resume completed, exit 0. |
| Line 53, `item_29` | Owner executed all four checks from the fresh answer; every command exited 0. |
| Line 56, `item_31` | Owner read the entire resumed answer and verified stable source identities. |
| Line 61, `item_34` | Delivery candidate source matched checked bytes; candidate diff check passed. |
| Line 63, `item_35` | Attributable local commit completed. |
| Line 65, `item_36` | Common delivery helper returned LOCAL_ONLY. |
| Line 68, `item_38` | Reconciliation and final verification completed. |
| Line 69, `item_39` | Final answer, after both complete peer answers and checks. |

The fresh peer chose **`(15, 70, 10) -> 6`**: 4.5 discounted cents rounds to 5; tax of 0.5 rounds to 1. Resume recalled that same input and reread unchanged source.

The owner parsed all four shell blocks from the fresh answer into argv, executed them, and retained each script and raw result. Each `peer-check-N.py` exactly equals the corresponding peer-proposed Python argument plus its final newline:

1. Four concrete assertions, including `(15,70,10) -> 6` and decimal `(500,99.7,0) -> 2`, passed.
2. A separate `Fraction(99.7)` binary-float interpretation demonstration returned the predicted alternative 1.
3. The integer grid contains `101³ = 1,030,301` cases, with zero mismatches.
4. The half-percentage grid contains `21 × 201² = 848,421` cases, with zero mismatches.

The two grids total **1,878,722** comparison cases. Their actual owner execution and zero-mismatch output are retained in `peer-checks.log`; this audit checked the loop bounds and script identity without rerunning the grids. These are peer-proposed owner checks, not a hidden S2 semantic oracle.

## Terminal-result inventory and costs

Before read-only collection, the audit predicted that the unchanged 0244 discovery code would return exactly the genuine fresh/resume envelopes for one Claude session, with no extra summary or unreadable carrier. The actual inventory returned exactly:

- `fresh/peer1791652636410605387.json`, SHA-256 `991ee752cd9ea5f4c3309d316c8c15a00a62bfa9d3885590d36eec2fe7bf5202`
- `resume/peer1791653044838073215.json`, SHA-256 `1fd5fe5971a4ae13433e83e73c1abcfbd4890436e4da924ef64baa69024ab79e`

Both are genuine successful native terminal results containing answer, `usage`, and `modelUsage`; their session and answer text bind to the native transcript and helper attempts. No additional metadata-only result or unreadable carrier was admitted. The collector invocation read existing evidence only and wrote no new verdict or accounting file.

The retained Claude accounting guard reports MATCH across five terminal messages, with no API errors, stream retries, or accounting gaps. It records 49,646 cache-creation input, 94,625 cache-read input, 10 ordinary input, and 41,881 output tokens for the peer session; thinking is already included in output.

Whole-run emitted accounting remains **1,326,755 input / 61,134 output tokens**, COMPLETE, with owner wall time **688.6771035840211 seconds**. These are native emitted totals, not independently verified provider billing. No old result was reclassified.

## Local delivery, cleanup, and limits

Commit **`75b691634e30b3a1e03d2b91804f1412427d08e2`** has baseline `a2f04a58490e9b956479caf132c037b21f7bd92b` as its sole parent and changes only `calculate_total.py` and `test_calculate_total.py`. Read-only Git inspection confirms checked source bytes, clean `main`, only `refs/heads/main`, and no temporary worktree registration. The common endpoint returned LOCAL_ONLY, with retained receipt/custody records under `cell/work/.git/devlyn-completion/9e729938f32e81614da91255/`.

Reconciliation fast-forwarded the original checkout and removed its temporary worktree and task branch. Read-only Docker inspection independently found no remaining container `devlyn-0231-f4b60958b4f444d493de137c33fbc5c6` or volume `devlyn-0234-tmp-f6e428308fb74070b95631493d04970e`. There is no publication claim.

Under **No guesswork**, the final integrity prediction is that all 65 protected source hashes remain unchanged, including the old 0242 s03 STOP verdict and the collector source. The actual before/after comparison is recorded in [s01-native-protocol-audit.json](s01-native-protocol-audit.json). Root separately audits broader frozen-input/evidence manifests.

No inference, independent review, auth operation, or heavy test was launched for this audit. Operational success does not establish automatic pairing, defect-discovery gain, better reasoning, lower latency, or token savings.

