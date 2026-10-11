# s02-h-codex-v2 protocol and integrity audit

2026-10-10. Read-only audit of the finalized cell at
`/Users/aipalm/.local/share/nx01/0238-live/staged-v1/out-smoke-v2/s02-h-codex-v2`.
No protocol or artifact-integrity blocker was found in the checked scope.
The original verdict remains **STOP: whole-run usage PARTIAL**; total cost is
**UNKNOWN**. Accounting is assigned separately and is not resolved by this report.
No source evaluation, test rerun, authentication or model/native CLI call was made.

Paths below are relative to that cell.

- **Original request.** `cell/work/.devlyn/pair/fresh-request.md:7` introduces
  the complete caller request, present exactly once and byte-for-byte equal to
  `harness/caller.json`'s request string. Only role/capability instructions
  precede it. Exact source follows at line 21, diff at 79, and raw checks at 142,
  before the review question at 193. No owner interpretation precedes the raw
  evidence. The peer is expressly read-only and permits exactly one native child.
- **Actual primary and resumed route.** The peer's native rollout
  `home/.codex/sessions/2026/10/10/rollout-2026-10-10T14-37-06-01a1263f-0580-7c32-9d49-11b8792e8494.jsonl`
  records `gpt-6-astra` / `max` / read-only in both turn contexts (lines 8, 66),
  and completed fresh/resumed turns (62, 82). Both captures use that exact
  session, and review2 explicitly resumes it. Requested-route receipts alone
  are not the identity evidence used here.
- **Native child completion.** Child rollout
  `home/.codex/sessions/2026/10/10/rollout-2026-10-10T14-37-41-01a1263f-8bf0-7c91-868b-001158c92bc0.jsonl`
  binds its parent to that primary at line 1 and records `gpt-6-sol` / `high` /
  read-only at line 8. Its completed answer at line 31 (14:37:54.132Z) confirms
  `(5,50,50) -> 5`. The primary's `list_agents` result at line 56 observes that
  completed result before its own fresh completion at 14:38:34.039Z. This is a
  native child, not an additional independent peer or an unresolved background call.
- **Stable source and owner consumption.** All four source identity objects
  (fresh before/after, resume before/after) match exactly. Both helper calls
  exited 0, at 88.159037999s and 15.841636049s. Owner tool results in
  `run/stdout:71` and `84` contain the fresh and resumed answers respectively.
  `run/stdout:74` records the owner's actual assertion
  `calculate_total(5, 50, 50) == 5`, stdout `5`, exit 0; its raw command/result
  remains in `cell/work/.devlyn/pair/fresh-proposed-check.*`.
- **Local commit.** `run/stdout:97` attributes the commit to only
  `calculate_total.py` and `test_calculate_total.py`; line 101 records local
  fast-forward reconciliation and temporary branch/worktree cleanup. Final
  `cell/work/.git/refs/heads/main` is
  `ca19872f1fbe9d5c738f14ad37ea6be11edcdf3f`, matching the retained local-delivery
  record. This is observed local delivery, not an independent source-quality pass:
  the runner stopped before producing evaluated snapshot/check/delivery artifacts.

All 75 sealed inputs, 5 prepared files, 1,196 evidence entries and 1,059 control
files match their recorded hashes. The verdict binds the same evidence manifest;
its declared failures list is empty. Both applicable freeze maps, 17 selected
artifacts and 6 recovery artifacts also match. Full counts and primary artifact
hashes are in `s02-v2-protocol-integrity-audit.json`. Empty credential mount
placeholders were checked by size/type without opening credential sources.

A failed owner lookup under `/root/.codex/sessions` at `run/stdout:80` was corrected
to the participant session path at line 82. It did not change the source or route.
This report neither changes the saved STOP nor treats successful protocol and
local delivery as complete whole-run accounting or pair-effectiveness evidence.
