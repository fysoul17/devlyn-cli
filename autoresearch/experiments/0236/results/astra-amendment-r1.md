- **HIGH — [run_continuation.py:515](/Users/aipalm/.local/share/nx01/0236-reg/autoresearch/experiments/0236/run_continuation.py:515):** Preserved grading never validates `seal.json`’s input hashes. `baseline.json` is outside the checked evidence manifest, yet controls snapshot selection, task and scope grading. Changed baseline contents can therefore pass preservation checks. Verify sealed inputs before grading (**Production ready**).
- **MEDIUM — [run_continuation.py:543](/Users/aipalm/.local/share/nx01/0236-reg/autoresearch/experiments/0236/run_continuation.py:543):** Identity is taken from the old verdict rather than recomputed. Rerun `cell_run.identity()` against the verified plan and evidence to meet the explicit identity-recheck condition.

Symmetric exemption, reference preservation, disclosures, STOP archival and pipeline extraction otherwise match choice A.

Eight read-only tests passed. Full suite could not start because the sandbox prohibits temporary-file creation. Outcome blindness preserved.

**REVISE**
