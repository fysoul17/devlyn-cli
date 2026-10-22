I'll review the amendment against the frozen design, the executor contracts, and the 0257 diff. First I'll load the experiment files and how costs are computed.The account-stop lives in the 0257 driver and in code it imports. I'll read those paths and the window-estimate logic next.The cost and gate path in `decide.py` reads wall time, input tokens, output tokens, and whether usage is `COMPLETE`. Window points stay in the block reserve. The near-expiry profile read is required: renewal runs only in the last 300 seconds, and the old branch cleared the fingerprint for that whole window, so `account_changed` could not see the pre-renewal account. `test_near_expiry_account_change_is_logged_on_renewal` covers that path.

**MEDIUM** `driver.py:297`: A persisted `split_wait` holds the logged-in account whenever its reset time is within 600 seconds of the previous account's stored reset, so a switch onto an account with room still holds the second cell of a split block.

**MEDIUM** `test_apparatus.py:805`: The expected estimate is 7, the legacy cell, which is larger than the same-account cell's 5, so dropping every matching-account delta still passes.

**LOW** `amendment-1.md:36`: The amendment adds a two-account interpretation limit and leaves `DESIGN.md:297` ("on one account") and the inherited 0256 same-account renewal (`DESIGN.md:115`, `0256/DESIGN.md:154`) in place.

**LOW** `run_cell.py:374`: Regrading a pre-amendment assessor STOP keeps a record with no `claude_account_before`, `grade` then writes `claude_account_after`, and `estimates` raises. The live round-3 SMOKE verdicts are `PRODUCT_INCOMPLETE`. The round-1 `assessment held` STOP is under `smoke-r1/`, outside the output glob.

VERDICT: FIX
