# 0242 s02 native protocol audit

The observed registered transport gates pass for the **Claude owner → Codex peer** cell. The untouched verdict is **CHECKS_PASS / COMPLETE**; identity and peer policy are **MATCH** with no gaps or violations, local delivery passes, and teardown is **CLEAN**. This remains forced S2 smoke: `measurement_eligible: false`, assessment `NOT_REQUESTED`. No efficacy result or product pair adoption follows.

Evidence root: `/Users/aipalm/.local/share/nx01/0242-live/staged-v1/out-smoke/s02-p-claude`. All paths below are relative to that root unless noted. Root handles the broader frozen-input and evidence-manifest integrity audit.

## Actual peer request capabilities and identity

Both helper attempts request `gpt-6-astra` / `max`, native read-only sandbox, `agents.enabled=false`, and `features.multi_agent_v2.enabled=false`. Their actual native initial requests independently establish the outcome:

| Attempt | Initial inference ID | Native session | Actual capability result |
| --- | --- | --- | --- |
| Fresh | `886e281e-4af7-4e31-918e-bb0e5097d9c6` | `01a126a2-89ab-7802-a2cf-462f8ba005ad` | No collaboration catalog or multi_agent_role/mode instructions |
| Resume | `593b7862-4c66-494f-8368-2ea125453857` | Same session | Same absence |

Each binding follows the attempt start to the corresponding native trace manifest/root session and the first `inference_started` event, sequence 6, pointing to `payloads/4.json`. Each initial payload contains one full `additional_tools` catalog with only `functions` and `clock`: `functions.exec`, `functions.wait`, `functions.request_user_input`, `functions.request_user_input_async`, and `clock.sleep`. Neither full catalog nor developer message text contains `spawn_agent`. Both developer message sets omit `multi_agent_role` and `multi_agent_mode`. Both native requests specify model `gpt-6-astra` and reasoning effort `max`.

The exact fresh and resumed prompts appear in their respective initial native payloads; the resumed payload retains the fresh conversation. The accompanying JSON records full trace/payload paths and SHA-256 bindings. These are actual initial catalogs, not incremental omissions or conclusions from argv/no observed spawning. No security-boundary or handler-denial claim is made.

The owner is Claude session `bd8e9711-7592-4f7f-a77d-20878d0f788f`. Its native init identifies `claude-opus-5-5`; the configured/launched effort is `max`, and the recorder's owner identity check is MATCH. Its initial tool inventory retains Claude's native owner capabilities, including Task, ListAgents, and SendMessage. A Codex owner catalog is inapplicable to this cell.

## Request fidelity and source stability

The original caller request is 2,386 characters and appears exactly once in `cell/work/.devlyn/pair/request.md`, starting at character 791. `original-request.txt` equals the caller request. The original precedes the candidate diff (3,183), raw checks (5,444), owner interpretation (10,027), and review ask (10,811). The leading material establishes the peer role and source locations. Both prompt files exactly match the helper argv strings and prompt hashes.

Fresh-before, fresh-after, resume-before, and resume-after identities are equal: **55 files**, HEAD `0a564a75f05d0cd4adf37fe78310aa0b3f74fe56`. Both completion receipts state unchanged source; all 55 retained final file hashes match those snapshots.

Fresh completed exit 0 in **52.502601024003525 seconds**; resume completed exit 0 in **12.077934130000358 seconds**. Both native traces end as completed. The fresh peer made nine read-only commands inspecting source, consumers, instructions, and Git state; it did not run its proposed check, mutate source, commit, or delegate. Resume made no command calls. The retained inventory has one Claude owner and one independent Codex peer, with no peer descendants or recursive session.

## Observed order and owner execution

| `run/stdout` line | Observation |
| --- | --- |
| 508 | Initial public check: two unittest methods passed, exit 0. |
| 631 | Immediately before fresh launch: CLAUDECODE marker reported present. |
| 636 | Fresh helper completed, exit 0. |
| 642 | Owner read the complete fresh answer and capture. |
| 708 | Before resume: CLAUDECODE marker reported present again. |
| 712 | Same-session resume completed, exit 0. |
| 715 | Owner read the complete resumed answer. |
| 740 | Owner actually ran the peer-proposed assertion: output 197, exit 0. |
| 834 | Public two-test check and witness both passed in the delivery worktree. |
| 866 | Common local-delivery helper returned LOCAL_ONLY. |
| 900 | Original checkout fast-forwarded; temporary worktree and task branch removed. |
| 923 | Public two-test check passed on reconciled main. |
| 936–937 | Owner final answer, then native success result. |

The fresh peer derived **`(145, 10, 50) -> 197`**: 130.5 discounted cents rounds half up to 131; tax of 65.5 rounds to 66. Resume recalled the same input and expected result. The owner's executed command and raw output remain in `cell/work/.devlyn/pair/peer-check.log`.

The marker observations use presence checks; no observed operation removes CLAUDECODE or prints its value. Both completed answer files and untouched native captures remain under `review1/` and `review2/`. Both full answer strings occur in owner tool results before the final answer.

## Local delivery, reported caveats, and limits

The common endpoint returned `LOCAL_ONLY` for commit **`d23ce723e09b2b196ac54a2f891a46b4544d08b5`**, whose sole parent is baseline `0a564a75f05d0cd4adf37fe78310aa0b3f74fe56`. Read-only Git inspection confirms exactly `calculate_total.py` and `test_calculate_total.py` changed, checked source bytes match, and the original checkout is clean on `main`. Only `refs/heads/main` remains, with no temporary worktree registration. Receipt/custody records remain under `cell/work/.git/devlyn-completion/75ea0d8505fc5f4279b5ddf1/`.

Preserved observations from the owner, not new audit requirements:

- The implementation rounds the discounted price. The owner reported that interpreting half-up rounding as applying to the discount amount instead changes `(1005, 10, 0)` from 905 to 904. Both interpretations pass the two public tests. The fresh peer found no established obligation to round the discount amount separately. This audit neither invents a hidden S2 oracle nor resolves the ambiguity by adding a requirement.
- Source and retained solo-check output show explicit range/type validation and error handling beyond the stated valid-input domain. The final response reports percentage text such as `'10'` is accepted, while NaN/None errors do not identify the argument. These remain disclosed implementation observations; they are not silently upgraded to contract failures or erased.
- Retained owner solo checks report zero integer-grid/decimal-percent mismatches and mutation-test observations. This audit did not rerun that grid, reinterpret its reference as an independent hidden oracle, or turn peer agreement into defect-discovery evidence.

The raw complete native usage is **4,526,918 input / 85,892 output tokens**, with owner wall time **858.5960301250161 seconds**. This preserves emitted accounting, not a claim about independently verified provider billing. Recorder teardown is CLEAN; no test, model, auth operation, or new native run was launched during this audit.

Under **No guesswork**, the final integrity prediction is that all 40 captured report-source hashes remain unchanged. The actual before/after comparison is recorded in [s02-native-protocol-audit.json](s02-native-protocol-audit.json). No source, frozen input, raw record, or verdict was edited. Operational success does not establish automatic activation, product superiority, lower latency, or token savings.

