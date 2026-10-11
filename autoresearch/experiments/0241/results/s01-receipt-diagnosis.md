# 0241 s01 receipt-gap diagnosis

The sole gap is a **command-text false positive**, not an observed missing helper receipt. The frozen policy counted four regex matches; the retained stream shows two actual helper calls and two descriptions of those same calls inside delivery acceptance data. This diagnosis does not regrade the saved STOP/PARTIAL or resolve its recorded whole-run UNKNOWN.

Evidence root: `/Users/aipalm/.local/share/nx01/0241-live/staged-v3/out-smoke/s01-h-codex`.

| Raw stdout line | Event | Observed operation | Regex matches |
| --- | --- | --- | ---: |
| 44 | `item_21`, completed, exit 0 | Fresh installed `peer.py` call; result names `.devlyn/pair/review1` | 1 |
| 53 | `item_27`, completed, exit 0 | Resume installed `peer.py` call; result names `.devlyn/pair/review2` | 1 |
| 70 | `item_36`, completed, exit 0 | `python -` heredoc constructs `acceptance['checks']`, writes JSON, calls `task-complete.py complete` | 2 |

At line 70, `checks[3].command` and `checks[4].command` are exactly the shell-unwrapped commands from lines 44 and 53. They are Python string values, never submitted as executable argv by that script. The script's subprocess calls obtain Git facts and invoke `task-complete.py`. The installed completion helper, `cell/work/.agents/skills/_shared/task-complete.py:299–303`, validates that each check has a command string and records its evidence path; lines 311–317 bind custody and acceptance. It does not execute those strings.

The two logical typed receipts have starts `1791646805682159883` and `1791646878395845889`; each exists in the original pair directory, custody and records (six physical copies, correctly deduplicated by `0238/policy.py:42–62`). Both name session `01a12678-aede-7d52-bae3-84b3b6e297c6`, with the second explicitly resuming it. Both completions are `EXITED`, exit 0, source unchanged. The saved peer policy reports `validation_completion=COMPLETED`, no protocol violation, and only the missing-receipt gap. The retained numeric usage is 1,040,004 input / 17,807 output; its saved status remains PARTIAL.

Root cause: `0238/policy.py:232–242` searches the entire native command text for a Python/peer.py substring, including inert heredoc contents and string literals. Lines 243–244 compare the resulting 4 with the two deduplicated receipts and add the gap. This is separate from 0241's capture classification repair: the selected receipt files and native captures are present.

A minimal prospective repair should establish **actual supported helper invocation positions**, after bounded shell-wrapper/argv parsing, instead of treating a matching substring as execution. Use standard lexical primitives for the supported direct helper route; ignore quoted documentation and heredoc data. Keep the missing-receipt comparison, incomplete-attempt handling and independent native session/accounting gates. Do not filter this gap after collection, exempt delivery commands by filename, increase the receipt count using custody copies, or change this old verdict. General script execution cannot be proven by a substring parser; unsupported indirect execution remains a bounded-observability limitation, with native sessions still requiring attribution.

Falsifiable prospective control: retain the two real fresh/resume command events, two receipts and their native evidence, then append the exact acceptance-writing event. Expected: two observed helper launches and no new receipt gap. Add a third actual supported helper invocation that fails before its receipt: the gap must return. Add echoed/documented helper strings: they must not add calls. Keep malformed receipt, unknown native session, missing usage and interrupted-request STOP controls. These fixtures have not been run in this audit.

`s01-receipt-diagnosis.json` retains exact event offsets, line/command hashes, receipt identities, equality checks and source hashes. No source, receipt, verdict, accounting file or frozen input was modified; no test/model/auth/native call was made.
