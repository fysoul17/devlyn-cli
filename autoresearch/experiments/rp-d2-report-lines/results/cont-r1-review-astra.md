- **HIGH — allowed accounting gaps can conceal identity/evidence failures.** [runner.py:78](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d2-report-lines/autoresearch/experiments/rp-d2-report-lines/runner.py:78) trusts 0254’s first failure as exhaustive. An `api_error` aborts auditing before request account/session/effort and later lifecycle checks. In-memory reproduction: account mismatch alone is rejected; adding a retry produces only the allowed retry gap. Likewise, a child aggregate mismatch hides a subsequent unbound lifecycle. Identity, peer policy and matching file hashes do not establish these skipped invariants.

- **HIGH — continuation omits the independent native-scope audit.** [runner.py:108](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d2-report-lines/autoresearch/experiments/rp-d2-report-lines/runner.py:108) never restores [0255’s MATCH-only checks](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/rp-d2-report-lines/autoresearch/experiments/0255/runner.py:41). A retry combined with malformed foreign native evidence can therefore continue, although COMPLETE accounting would expose the foreign-carrier/inventory defect and STOP. Peer policy does not check all those inventory fields.

For **No workaround**, require independently completed non-accounting integrity and scope checks. Then reuse inherited grading through a narrow eligibility hook; this removes the duplicated grading block without falsifying usage completeness.

No other findings: grading order/status mapping matches; the MRO places continuation before archive → done_check → delete/404 → final PAT scan for both engines; smoke remains STOP. The new exception handler avoids credential payloads, and scan coverage includes both verdict and accounting-stop files. UNKNOWN summary/adoption behavior matches the contract.

Verified through read-only tracing and in-memory probes. Operator-reported suites were not rerun.

VERDICT: REVISE
