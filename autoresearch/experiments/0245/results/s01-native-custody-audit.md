# 0245 s01 native protocol and custody audit

**PASS for the registered operational test.** The emitted outcome remains CHECKS_PASS/COMPLETE: **1,360,918 input / 48,745 output tokens**, owner duration **590.173871958 seconds**, identity/policy/accounting MATCH, no gaps, and CLEAN teardown. The cell remains measurement-ineligible. This is not evidence of efficacy, spontaneous pair activation, or efficiency.

Raw evidence: `/Users/aipalm/.local/share/nx01/0245-live/staged-v1/out-smoke/s01-p-codex`.

## Original request and actual native sessions

The owner is native Codex `gpt-6-astra` / `max`, session `01a12714-c64d-7520-9dd0-ac758d8c5eb4`. Fresh and resumed peer calls use the same native Claude session, `dc2ac749-87e8-4825-b6d7-7f1b75d89d72`. Native assistant records consistently report `claude-opus-5-5`, effort and per-turn effort `max`, with no sidechain. The fresh call uses three Read, two Glob and two Grep calls; resume uses one Read and one Grep. There is one peer transcript and no observed descendants, shell/test execution, or source mutation. Both argv records restrict tools to Read/Grep/Glob with an empty strict MCP configuration.

The actual fresh native prompt (transcript line 3) equals the attempt argv prompt. It contains the entire 2,998-character caller request verbatim once at offset 521, before source at 3,523, diff at 5,559, raw public results at 7,861 and the owner's focused review question at 8,102. The prefix identifies the read-only role and restrictions. The raw five-test result appears before interpretation. The 8,827-character prompt hash matches `9a85a73a0b1e7c71d602ff65997497b87f093d13508314484a97d78b222b8ed1`. The actual 811-character resume prompt at transcript line 52 also equals its recorded argv; it asks the same session to recall its example without supplying the answer.

The owner reports only `CLAUDECODE_present: False` at both launches. The actual wrapper commands neither remove that variable nor replace the inherited environment.

## The missing lifetime guarantee is exercised

The actual owner commands at `run/stdout:50` and `:61` use Python TemporaryDirectory contexts. Each writes its prompt inside caller scratch, invokes the helper without `--out`, receives canonical paths, hashes the five retained files, copies the answer into scratch, and consumes that copy. After leaving each context, the owner asserts scratch absence and byte equality of all canonical records. The resumed command also rechecks the fresh records.

| Call | Deleted caller scratch under .devlyn/pair | Retained canonical directory | Peer seconds |
|---|---|---|---:|
| Fresh | caller-fresh-5_4c1wy8 | peer-nysoz0xg | 253.906954 |
| Resume | caller-resume-1gnz86j2 | peer-aayeukjv | 13.019744 |

Independent filesystem inspection confirms both scratch directories are absent. Exactly two typed attempt/completion sets remain. Each contains only attempt.json, completion.json, its untouched native result, stderr and finalanswer.txt. All **10 canonical files** still match the hashes taken inside their contexts before cleanup, including after delivery. Auxiliary owner logs/reports in .devlyn/pair do not create another canonical set. The unchanged collector independently discovers exactly two genuine native result envelopes for this one session, with no gaps.

The fresh native result is `peer1791657163152015969.json`, SHA-256 `0a0b51ccf784f76b88c54e5b2cd7143feb6de72bd5bb69b6006a5686b680280e`; resume is `peer1791657448132715461.json`, SHA-256 `a0bf7dde2271eb7b7a9d73d3013ded20b4fdec358a231194c000404a4f363737`. There is no command copying, moving or deleting these helper records. Only the required disposable answer copies are made.

All four source snapshots—fresh before/after and resume before/after—are identical, with 29 files and the same pre-delivery HEAD. The reviewed source reaches the final commit unchanged.

## Complete answers and owner execution

Both finalanswer files exactly reproduce their native result text plus a trailing newline. Fresh has 2,859 characters and resume 1,244. Both complete answers appear in the owner's completed stdout events, lines 58 and 62. The corresponding native owner tool results at rollout lines 158 and 173 contain the full answers without truncation, at 18:37:01.939 and 18:37:44.359 UTC, before owner checks, delivery and the final response.

The fresh peer proposes `(210, 5, 8.25) → 217` and the additional decimal-rate check `(500, 0, 7.3) → 537`. Resume recalls the first example and re-reads unchanged source. The owner executes both exact Python assertion bodies, including integer-type assertions, at stdout lines 67–69: both exit 0 with empty stdout/stderr. The raw results remain in peer-proposed-checks.log. Five public tests passed at stdout line 42; this auditor replayed none.

The peer reports no supported violation. Its discussion of discounted remainder versus rounded discount amount is retained as an interpretation observation, not a hidden semantic oracle or a newly imposed requirement.

## Delivery and complete native accounting

The common delivery helper allocates an owned worktree, receives byte-identical checked source, and returns LOCAL_ONLY. Commit `e0088294b0acdcde794834740a56d2b78025f00f` has parent `c9a556ddfeeda906b1620d60de5506462cb6943d` and changes exactly calculate_total.py and test_calculate_total.py. The owner verifies original untracked files against the committed candidate before replacing those attributable copies through a fast-forward.

Read-only Git inspection confirms main is at that commit with a clean checkout and one worktree. The owned delivery worktree and task branch are gone. Git configuration matches the owner's saved SHA-256. The local completion receipt and acceptance evidence remain. The original container and temporary volume are absent. Owner reconciliation at stdout line 85 also verifies that both caller scratch directories remain absent and all helper hashes still match.

The unchanged accounting guard reconciles seven native terminal-message usage records. Claude's cumulative session total is 14 ordinary input + 38,543 cache creation + 152,277 cache read, and 29,584 output. Codex contributes 1,170,084 input / 19,161 output, producing the emitted complete whole-run totals. The resumed aggregate is cumulative; summing it with the fresh aggregate would double count. Thinking is already included in output. These are native emitted counters, not provider billing.

The companion JSON records protected hashes before and after. No native/model calls, authentication access, tests, source edits, frozen-file edits or archive rewrites were performed. Prior STOPs—including 0243 d02—and their full recorded costs remain intact. This success closes the exercised caller-cleanup retention condition only.

