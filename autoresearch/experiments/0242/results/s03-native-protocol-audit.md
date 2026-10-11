# 0242 s03 native protocol audit

The original result remains **STOP / PARTIAL**, reason `ValueError: whole-run usage PARTIAL`, with the retained gap `Claude result cell/work/.devlyn/pair/fresh-result-metadata.json without usage`. The owner exited 0 and teardown is CLEAN. The observations below do not regrade the run or supply a post-STOP product verdict.

Evidence root: `/Users/aipalm/.local/share/nx01/0242-live/staged-v1/out-smoke/s03-p-codex`. Root separately owns the accounting-discovery diagnosis and broad input/evidence-manifest integrity audit. Only this report and its accompanying JSON were written.

## Actual Claude calls and request fidelity

The owner is Codex `gpt-6-astra` / `max`, session `01a126a9-f2c1-7ff1-afa9-6a3d0e986414`. Both independent peers are Claude session **`1007025c-9afd-4539-8461-53b1571e00e9`**, using **`claude-opus-5-5` / `max`**.

Both helper argv records set `--tools Read,Grep,Glob`, `--permission-mode dontAsk`, and empty strict MCP configuration; resume uses the same session. Native assistant records independently identify `claude-opus-5-5` with both `effort` and `perTurnEffort` equal to `max`. Both native result envelopes are successful, share that session, and contain usage.

The complete fresh and resume prompt strings equal the helper argv and prompt hashes. They also appear exactly as native transcript user messages at lines **3** and **50** of `home/.claude/projects/-cell-work/1007025c-9afd-4539-8461-53b1571e00e9.jsonl`. Thus request delivery is supported beyond requested argv.

The 2,386-character original caller request appears once as literal multiline text at fresh-prompt character 866, followed by a second representation inside the verbatim JSON caller contract at 3,253. This is a duplicated representation of the same request, not two independent requests. Relevant source starts at 5,981, the raw candidate diff at 7,967, public-check output at 10,203, and the review ask at 10,431. No owner conclusion precedes the source/check evidence. The leading material establishes the read-only peer role and source paths.

Both native result files and `finalanswer.txt` files remain under `cell/work/.devlyn/pair/review1/` and `review2/`. The requested/native identity checks and peer policy are MATCH, with no recorded policy gaps or violations.

## Tools, lifecycle, and source

The native Claude transcript records seven fresh-call tool uses: five Read, one Grep, and one Glob; resume records one Read of `calculate_total.py`. There is no Bash, edit, check execution, delegation, or other tool use. No sidechain is recorded, and the retained native inventory contains no peer child or recursive independent session. This states observed use and configured restriction, not a separate raw provider tool-catalog or security-boundary proof.

Fresh completed exit 0 in **214.68231922300038 seconds**; resume completed exit 0 in **12.846623465004086 seconds**. Four source identities—fresh-before, fresh-after, resume-before, resume-after—are identical: **29 files** and HEAD `0777e18c54cb8999478f77d3b93fae70c7ff6fc0`. All 29 retained final file hashes still match. The caller and Git configuration still match the saved pre-implementation SHA-256 values.

The owner reported only CLAUDECODE presence: absent before fresh and before resume. No observed operation removes that marker or prints its value.

## Completed answers and executed checks

| `run/stdout` line | Observation |
| --- | --- |
| 28, `item_13` | Owner public check ran; seven unittest methods passed, exit 0. |
| 39, `item_15` | Fresh helper completed, exit 0; marker absence recorded. |
| 41, `item_21` | Owner read the complete fresh answer and native result. |
| 44, `item_23` | Same-session resume completed, exit 0; marker absence recorded. |
| 46, `item_24` | Owner executed both peer-derived examples: 28 and 504, each exit 0. |
| 48, `item_25` | Owner read the complete resumed answer and checked stable identities. |
| 53, `item_28` | Delivery candidate source/modes matched checked source; cached diff check passed. |
| 55, `item_29` | Attributable local commit created. |
| 57, `item_30` | Delivery helper succeeded; the surrounding owner assertion failed on its cleanup label. |
| 60, `item_32` | Receipt-based recovery, reconciliation, and cleanup completed. |
| 61, `item_33` | Owner final response after both complete answers and checks. |

The fresh peer proposed **`(49, 50, 10) -> 28`**: 24.5 discounted cents rounds to 25; 2.5 tax cents rounds to 3. Resume recalled this same input and reread the unchanged source. The owner executed that assertion and the peer's decimal-percentage example **`(500, 0, 0.7) -> 504`**. Both commands and raw outputs are retained in `cell/work/.devlyn/pair/peer-checks.log`.

The fresh answer discusses alternative rounding interpretations and invalid inputs as notes, not findings. This audit retains those observations without inventing an S2 hidden oracle or additional input contract. Peer agreement and these examples do not establish product efficacy.

## Two owner assertion failures and recovery

Both failures remain visible in raw stdout:

1. **Whitespace-check status assumption, line 35.** While the fresh peer was running, the owner wrapped `git diff --no-index --check -- /dev/null <new-file>` and asserted exit 0. It returned 1, causing AssertionError. Before re-observing, the owner recorded the prediction that comparing differing files would return 1 without whitespace diagnostics. Line 37 then records both files returning 1 with empty stdout/stderr, preserved in `diff-check-observation.log`. No source changed. A later normal cached diff check in the delivery worktree returned 0.
2. **Cleanup-label assumption, line 57.** The completion subprocess itself exited 0 and returned `LOCAL_ONLY` with `scratch_cleanup.status: CLEAN`. The owner wrapper incorrectly asserted `CLEANED`, so the surrounding command exited 1 after persisting the successful helper result. The owner inspected the returned receipt and empty owned scratch, recorded `local-delivery-observation.txt`, and reconciled the accepted commit. It did not repeat completion, change the source, or erase the failed assertion.

These are observed owner-side recovery events, not grounds to silently replace the original study STOP.

## Attributable local delivery and limits

Commit **`5fe2d0ed993c99e962cf61530f498d700977ac27`** has baseline `0777e18c54cb8999478f77d3b93fae70c7ff6fc0` as its sole parent and changes only `calculate_total.py` and `test_calculate_total.py`. Read-only Git inspection confirms checked source bytes, clean `main`, only `refs/heads/main`, and no temporary worktree registration. The receipt is retained under `cell/work/.git/devlyn-completion/24b6efab7793b7e147a65017/`; the common endpoint returned LOCAL_ONLY. Reconciliation fast-forwarded the original checkout and removed the temporary worktree and branch.

The runner stopped before its product/delivery evaluation, so the raw verdict's delivery field remains null. The local-delivery facts above are directly observed records and repository state, not a substituted runner grade. No hidden S2 oracle or post-STOP product assessment was added.

Raw known usage lower bounds remain **1,325,063 input / 45,755 output tokens**, with owner wall time **644.9293162910035 seconds**. Whole-run usage remains PARTIAL. The separate native Claude accounting guard reports MATCH, six terminal messages, and no API errors, stream retries, or accounting gaps; that narrower match does not remove the overall discovery gap. The owner-generated metadata file was written while reading the real fresh result at stdout line 41; its producer is retained for the separate diagnosis.

Under **No guesswork**, the final integrity prediction is that all 59 captured report-source hashes remain unchanged. The actual before/after values are in [s03-native-protocol-audit.json](s03-native-protocol-audit.json). No model, auth operation, new native call, or test was run for this audit. No original source, frozen input, raw evidence, or verdict was edited.

