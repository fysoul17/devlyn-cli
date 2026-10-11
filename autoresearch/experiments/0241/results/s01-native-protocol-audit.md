# 0241 s01 native protocol and local-delivery audit

This read-only audit records operational observations from `s01-h-codex`. The original result remains **STOP / PARTIAL**, with `measurement_eligible: false`: `ValueError: peer model identity/evidence UNVERIFIED`. Nothing here regrades the run or supplies a post-STOP product verdict.

Evidence root: `/Users/aipalm/.local/share/nx01/0241-live/staged-v3/out-smoke/s01-h-codex`. Sources below are relative to that root; the original verdict is `../verdict-s01-h-codex.json`. The accompanying JSON records source SHA-256 values before and after this audit.

## Request and source fidelity

- The 2,386-character `harness/caller.json` request appears exactly once in `cell/work/.devlyn/pair/request.md`, at character 794. It precedes the raw candidate diff (3,489), source (5,921), raw public checks (8,050), and owner interpretation (8,253). The leading text establishes the independent, read-only peer role.
- The helper's fresh argv prompt equals that file, and its SHA-256 equals the recorded prompt digest. The fresh native initial inference payload also contains that exact prompt. The resume initial inference contains both the original fresh prompt and the exact resume prompt.
- Fresh-before, fresh-after, resume-before, and resume-after source identities are equal: 29 files and HEAD `93fa6a5b80328fe9b2692d1dad39452aa38469f6`. Both completion receipts state `source_unchanged: true`; the retained final source bytes still match every one of the 29 hashes.
- The caller file and Git configuration still match the hashes recorded before implementation. The owner reported `CLAUDECODE marker present: False` at `run/stdout:15` and again before resume at line 51, without exposing a credential or environment value.

## Actual native identity and lifecycle

| Role | Session | Native model / effort |
| --- | --- | --- |
| Owner | `01a12676-3aef-7851-9c9c-d81351b81b33` | `gpt-6-astra` / `max` |
| Fresh and resumed peer | `01a12678-aede-7d52-bae3-84b3b6e297c6` | `gpt-6-astra` / `max` |

These identities are supported by native rollout metadata, turn contexts, trace manifests, and initial inference payloads, beyond the requested argv. The owner has one native trace; the peer has distinct fresh and resume traces with the same root session. No child session appears in the retained native inventory.

The fresh helper completed with exit 0 in **36.94525418400008 seconds**; resume completed with exit 0 in **11.354144796001492 seconds**. Both native traces end `rollout_ended: completed`. The owner exited 0 after **428.83751491701696 seconds**.

The fresh peer executed three read-only source-inspection commands: two `sed` reads and one `rg` search. It did not execute a check, mutate source, commit, or invoke a child/session delegation tool. Resume emitted an answer without a tool call. This observed non-delegation does **not** prove that delegation capability was removed; the separate capability audit finds that the collaboration catalog remained exposed.

## Observed completion order and checks

| Evidence in `run/stdout` | Observation |
| --- | --- |
| Line 31, `item_15` | Owner's public check actually ran; six unittest methods passed, exit 0. |
| Line 44, `item_21` | Fresh helper returned its completed receipt, exit 0. |
| Line 48, `item_24` | Owner read the full fresh answer and native capture. |
| Line 51, `item_26` | Owner ran the proposed `(29, 50, 10) -> 17` assertion, printing 17 and exiting 0. |
| Line 53, `item_27` | Resume helper returned its completed receipt, exit 0, same session. |
| Line 57, `item_29` | Owner read the full resumed answer. |
| Line 68, `item_35` | Attributable local commit completed. |
| Lines 70, 73, 75 | Common local-delivery endpoint, reconciliation, and final verification completed. |
| Line 76, `item_40` | Owner final response, after both answers and checks. |

The fresh answer proposed 29 cents with a 50% discount and 10% tax: 14.5 rounds to 15 discounted cents; tax of 1.5 rounds to 2; total 17. Resume recalled this input and result without reading a saved answer. The owner-run assertion and raw output are retained in `cell/work/.devlyn/pair/peer-check.py` and `peer-checks.txt`; public output is `public-checks.txt`.

The two returned answer files are `cell/work/.devlyn/pair/review1/finalanswer.txt` and `review2/finalanswer.txt`. Both native captures and completion receipts are retained. No test or model was rerun during this audit. No hidden S2 oracle was invoked or credited, and the runner stopped before product evaluation.

## Local delivery and cleanup

The common endpoint returned `LOCAL_ONLY` for commit **`09a082b076937c447097ac340dca6913d593f0cb`**, whose sole parent is the baseline `93fa6a5b80328fe9b2692d1dad39452aa38469f6`. Direct read-only Git inspection confirms:

- Exactly `calculate_total.py` and `test_calculate_total.py` changed; committed bytes equal the checked source.
- The original checkout is clean on `main` at that commit.
- Only `refs/heads/main` remains, with no temporary worktree registration.
- The delivery receipt and custody records remain under `cell/work/.git/devlyn-completion/289e556a13ca9eed326324d6/`.

The recorder states `teardown: CLEAN`. Read-only Docker inspection independently returned “No such container” for `devlyn-0231-ff818842f8914dbeb70f5a1399045de1` and “no such volume” for `devlyn-0234-tmp-9cba6586bf6f470dbe3c1d371ad7f7f7`. There is no publication claim.

## Limits and integrity

The original known usage lower bounds are **1,040,004 input / 17,807 output tokens**. These are not complete whole-run costs: the frozen result retains the gap `peer: observed helper launch has no retained attempt receipt`, policy `UNVERIFIED`, and usage `PARTIAL`. This audit does not remove that gap. See the separate [receipt diagnosis](s01-receipt-diagnosis.md) and [capability diagnosis](s01-capability-diagnosis.md) for the two blockers.

Under **No guesswork**, **Production ready**, and **Worldclass**, the factual successes above cannot turn a STOP into a shippable or efficacy result. They establish observed transport, source stability, checks, and local delivery only; they do not show an automatic trigger, product advantage, efficiency improvement, or removed child capability.

Before the final integrity pass, the prediction is that all 83 captured report-source SHA-256 values remain unchanged. The actual comparison and complete before/after values are recorded in [s01-native-protocol-audit.json](s01-native-protocol-audit.json). No source, frozen input, raw record, or original verdict was edited.

