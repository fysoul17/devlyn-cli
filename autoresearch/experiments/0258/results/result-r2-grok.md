**REVISE.** One LOW. The by-account table and the account-change sentences match the verdicts, probes, and witnesses. Every other round-1 finding is resolved.

## LOW

`autoresearch/experiments/0258/RESULT.md` (operations) says the log shows d027 `rc 3` until 09:51:16Z, then 52 `skip_finished` lines at 10:06:49Z, and that the driver was relaunched after a host restart.

`driver.log` has those two log facts (last pre-gap d027 `rc 3` at 09:51:16Z, then exactly 52 `skip_finished` lines at 10:06:49Z) and none of a host restart. The restart is only in `results/operator-notes.md`.

Fix: end the log sentence at the skip count, and attribute the relaunch-after-restart to the operator notes.

## Resolved

- Non-rejection is stated as the tests, with smaller effects left open.
- “64 cells” and “128 commands” match the public `argv` entries (32 F10 + 96 D3). Both SMOKE cells are outside that 128.
- The non-object sentence is limited to the blanket `invalid_body` claim, and c006’s `[]` sentence is the narrower one.
- F10 C output is `≥ 82,333` (`164667 / 2`).
- Disclosure text says “Express’s default 400.” c015 is empty. c022 reports handling it.
- `f10-b.json` `close_calls` is `[]`. c031 remains the only `false_completion`.
- The restart time, 29 GiB, image check, and overwritten d027 disk reason are only in `operator-notes.md`, labeled as outside the log. The retained d027 not-dispatched file is the 429 reason.

## By account

Dispatch account (`claude_account_before`), cells / endpoint events / completions:

| account | F10 B | F10 C | D3 B | D3 C |
|---|---|---|---|---|
| `44e06b9de5c4`/`16b7ef0cf7cf` | 8 / 0 / 0 | 8 / 0 / 0 | 7 / 3 / 3 | 7 / 5 / 2 |
| `cc43a4e02ede`/`2905f4abf05b` | 8 / 0 / 2 | 7 / 0 / 1 | 8 / 6 / 0 | 8 / 5 / 2 |
| `25813bedb87d`/`e44a78e9700b` | — | 1 / 1 / 1 | 1 / 1 / 0 | 1 / 1 / 0 |

That matches the table. c022 is the only `json_error_400`, on `25813…`, and that account has no F10 B cell. Before and after differ only for c006, c021, and d024. The only missing after-readings are the seven HTTP 429 `claude_limits_after_error` cells named in RESULT. Both SMOKE cells are on `44e06…`.
