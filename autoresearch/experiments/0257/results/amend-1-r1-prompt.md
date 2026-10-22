Read-only review of a dated amendment to a running research experiment in the devlyn-cli repository (worktree: current directory).

Context: autoresearch/experiments/0257 is registered (DESIGN.md frozen r5, registration.md). The measured run stopped after 8 easy cells because the host Claude login switches between two of the owner's accounts when usage fills. The owner decided to allow whichever account is logged in. Read:
- autoresearch/experiments/0257/amendment-1.md (new, the dated amendment)
- autoresearch/experiments/0257/results/amend-1-contract.md and results/amend-1-fix-contract.md (what the executor was asked)
- `git diff` of autoresearch/experiments/0257/{driver.py,run_cell.py,test_apparatus.py,README.md}
- DESIGN.md (Operations, Decision, Qualification, Interpretation limits) and decide.py for how costs are computed.

Check:
1. Correctness: no remaining path in 0257 (including code it imports from 0222/0256) stops, holds or fails a cell because the account differs from runtime['account']; per-cell account fields are recorded correctly; `estimates` never crashes on a legitimate verdict (including a failed after-window read, STOP verdicts, and legacy verdicts without account fields) and never mixes two accounts' window readings.
2. Claims in amendment-1.md: is "no reading depends on the account" true given decide.py's cost and gate logic? Does anything else in DESIGN depend on a single account?
3. Scope: is the change the smallest that closes the goal? Flag any unrequested behavior change (e.g. `credential`'s near-expiry branch) that is unjustified.
4. Tests cover the new behavior.

Reply with findings ranked HIGH / MEDIUM / LOW (file:line, one sentence each), then a final line exactly `VERDICT: SHIP` or `VERDICT: FIX`.
