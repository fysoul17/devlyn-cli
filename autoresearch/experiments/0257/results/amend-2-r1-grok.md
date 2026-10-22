**SHIP**

`ready()`, `fits()`, and split-wait match the amendment. Nothing removed is still on the dispatch or verdict path. The change does not favor an arm or turn a quota fault into a scored result. The operator steps are safe if followed in order.

`fits` (`driver.py:57`) starts a cell only when both Claude windows are strictly under the registered caps. At 95/95 that is used < 95. A miss holds, and `run` re-reads after 60 seconds (`driver.py:362`). Split-wait is still only for the second cell of a block (`driver.py:359`, `269`). It stores that account and the windows that are at or over the cap, keeps holding until those reset times change (`driver.py:263`), and drops the wait when the login changes (`driver.py:257`). That is the same account-switch release as amendment 1.

`panel`, `estimates`, `delta`, and `FLOORS` were only inputs to the old reserve. The "incomplete Claude account pair" check lived inside `estimates` and only stopped a bad delta from entering that reserve. `decide.py` never reads account fingerprints or window percents. Regrade still records `claude_account_before` (`run_cell.py:383`).

A and B use the same threshold. The schedule still alternates AB/BA, so neither arm is systematically second. A cell that hits a limit mid-run still gets `shared account fault during execution:` (`run_cell.py:300`), returns 2, and is not treated as finished (`driver.py:355`). The next time `ready()` passes, that verdict and cell directory are renamed to `.stop-N` and the cell is run again (`driver.py:314`). `decide.py` treats a current STOP as a gap (`decide.py:165`) and charges archived quota attempts only as cost (`decide.py:136`). A preflight `account limit reached` never writes a verdict (`run_cell.py:250`).

`--amend-caps` still refuses a cap change after SMOKE until this command is run (`driver.py:107`, `158`). Setting 95/95 and then amending registers those caps. Relaunching before that stops the driver. Stopping while no cell is running avoids a live process writing `driver-status.json` back over the amendment.

No HIGH or MEDIUM findings.

**LOW** `amendment-2.md:5` — The owner’s words in the next sentence are “5% 미만” (under 5% left, used > 95). The paraphrase says “5% or less,” and the driver holds at used >= 95 (`driver.py:57`). If the switcher implements the quote and nothing else is consuming Claude, an account sitting at exactly 95% is held until that window’s `resets_at` changes, because the driver will not start a cell and the switcher will not rotate.

