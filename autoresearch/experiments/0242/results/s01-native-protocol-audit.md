# 0242 s01 native protocol audit

The observed registered transport gates pass. The untouched raw verdict is **CHECKS_PASS / COMPLETE**, identity and peer policy are **MATCH**, local delivery passes, and teardown is **CLEAN**. This is the forced S2 operational test, with `measurement_eligible: false` and assessment `NOT_REQUESTED`; it is not an efficacy result or product pair admission.

Evidence root: `/Users/aipalm/.local/share/nx01/0242-live/staged-v1/out-smoke/s01-h-codex`. The registration and selected `freeze-smoke-v2.json` were read; the latter matches SHA-256 `91233c5a27e1c5c43096a0a8e05b9c712eff30d87ff9d5c2f449b29ccee4b1d4`. Root owns the broader input/evidence-manifest audit.

## Actual initial native capabilities

Each row below is bound through that attempt's recorded start, native trace manifest/root session, and the **first** `inference_started` event (sequence 6), whose request pointer is `payloads/4.json`. Each payload contains one explicit, full `additional_tools` declaration. This does not infer removal from an incremental request, argv, or lack of spawning.

| Actual initial request | Session | Collaboration catalog | multi_agent_role / multi_agent_mode |
| --- | --- | --- | --- |
| Fresh peer, inference `efaa93e3-5e52-4a70-9a72-a4e0ce9cea6f` | `01a12691-12a0-71c0-b19b-8ec9cfafba32` | Absent | Both absent |
| Resumed peer, inference `3ab91d19-4aa4-4a9a-a288-8e55d7330ede` | Same peer session | Absent | Both absent |
| Owner, inference `54f82a99-0eff-4add-894d-399cf19d5b13` | `01a1268f-0732-7273-a590-f0d4df6f01b0` | Present, all six tools | Both present |

Both peer catalogs contain only the `functions` and `clock` namespaces: `functions.exec`, `functions.wait`, `functions.request_user_input`, `functions.request_user_input_async`, and `clock.sleep`. Neither full peer catalog nor its developer message text contains `spawn_agent`. The owner catalog additionally contains `collaboration.followup_task`, `interrupt_agent`, `list_agents`, `send_message`, `spawn_agent`, and `wait_agent`.

Both peer argv records contain `agents.enabled=false` and `features.multi_agent_v2.enabled=false`; the actual payloads above independently establish the effect. All three actual initial payloads specify `gpt-6-astra` and reasoning effort `max`. Full native paths, payload hashes, and bindings are in the accompanying JSON.

This establishes native tool/instruction removal in these two requests, not a security boundary or proof of handler denial against arbitrary handcrafted calls.

## Request, source, and awaited answers

The original 2,386-character caller request occurs exactly once in the fresh prompt, starting at character 410. It precedes the exact relevant source (3,056), candidate diff (4,933), raw owner checks (7,132), and review task (7,371). No owner conclusion precedes those raw materials. The leading paragraph establishes the read-only, non-delegating role.

Both prompt files exactly match their helper argv strings and recorded prompt digests. Each is present exactly in its corresponding initial native request. The fresh and resumed native captures and trace roots bind the same peer session. Fresh-before, fresh-after, resume-before, and resume-after identities are equal: **29 files**, baseline HEAD `9d477cedf8892ce9df5134327360fe796accc813`. All 29 final retained source hashes still match. The caller and Git configuration retain their pre-implementation hashes.

Fresh completed exit 0 in **50.75958839699888 seconds**; resume completed exit 0 in **9.475126712997735 seconds**. Both native traces end as completed. No peer child or recursive model session appears in the retained session inventory.

| `run/stdout` evidence | Observed event |
| --- | --- |
| Line 44, `item_21` | Owner public check ran: five unittest methods passed, exit 0. |
| Line 53, `item_24` | Fresh helper completed, exit 0. |
| Line 55, `item_27` | Owner read the complete fresh answer and capture. |
| Line 58, `item_29` | Owner independently executed the proposed witness; output 105, exit 0. |
| Line 60, `item_30` | Owner reported CLAUDECODE marker absent before resume. |
| Line 62, `item_31` | Same-session resume completed, exit 0. |
| Line 64, `item_32` | Owner read the complete resumed answer. |
| Lines 71, 73, 75 | Attributable commit, common local-delivery completion, and reconciliation/final verification. |
| Line 76, `item_39` | Final answer, after both complete peer answers and checks. |

The fresh peer proposed **`(105, 10, 10) -> 105`**: 94.5 discounted cents rounds to 95; 9.5 tax cents rounds to 10. Resume recalled the input and personally reread the unchanged source. The owner ran its proposed assertion, including the integer-type check, and retained `peer-proposed-check.py` and `peer-proposed-check.log`.

The fresh peer also ran that example itself using `python -B` and verified unchanged source bytes. This must not be described as “no peer check execution.” It made five command calls total: four source/diff/consumer inspections and this source-preserving check. Resume made one source-read call. The installed guide and prompt require a read-only Codex peer, sole source writer, no implementation/delivery/delegation, and owner execution of proposed checks; they contain no explicit ban on source-preserving peer execution. The owner's independent execution satisfied its own obligation. No source mutation, commit, or delegation by the peer is observed.

## Local delivery and measurement limits

Commit **`747834637656181f104a1bce76f43377714dd5a5`** has baseline `9d477cedf8892ce9df5134327360fe796accc813` as its sole parent and changes only `calculate_total.py` and `test_calculate_total.py`. Read-only Git inspection confirms checked source bytes, clean `main`, only `refs/heads/main`, and no temporary worktree registration. The common endpoint returned `LOCAL_ONLY`; reconciliation fast-forwarded the original checkout and removed the temporary worktree and task branch. Receipt/custody records remain under `cell/work/.git/devlyn-completion/042d51079d1cd4d412a0501a/`.

The raw run reports **828,204 input / 17,165 output tokens**, usage **COMPLETE**, and owner wall time **402.3037222090061 seconds**. These are retained native accounting, not independently verified provider billing. Policy has no gaps, violations, or protocol violations. The recorder reports clean teardown. No model, auth operation, new native run, or test was executed for this audit.

No hidden S2 oracle or efficacy claim is added. The example already appears in the candidate tests; peer agreement and transport success do not establish new defect discovery, automatic activation, reasoning advantage, speed, or token savings. Prior STOP outcomes remain intact.

Under **No guesswork**, the final integrity prediction is that all 55 captured report-source hashes remain unchanged. The actual before/after comparison is recorded in [s01-native-protocol-audit.json](s01-native-protocol-audit.json). No frozen input, raw record, or verdict was edited.

