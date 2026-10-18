# apparatus-r4 — grok

I'll confirm only the round-4 push-scan claims against the round-3 notes and commit `c636fb87`, without editing files or running anything.The round-4 push scan in `c636fb87` holds. No new HIGH or MEDIUM finding.

The push scan in `capture.py:220-259` consumes a separate `-o` value and the value of any prefix that matches exactly one of `--push-option`, `--repo`, `--receive-pack`, or `--exec` before dry-run detection. Ambiguous prefixes (`--p`, `--re`, `--rec`, `--d`) set `unknown` and do not consume the next argument. An attached `-o` value stays out of the short cluster, so `-on` and `-uon` stay real pushes while `-un` and `--dr` stay dry runs.

Help is scoped in `capture.py:211-214` and `capture.py:235-254`. `-h` or `--help` among the global tokens before `push` leaves the push unobserved. Inside `push`, only an exact `--help` or an `h` before the first `o` is help. A value taken by `-o` or by one of those four long options is not scanned as help, so `--pu -h` and `-o --help` stay real pushes, while `--pu value --help` and `-o value -h` do not.

A dry run is recorded only for a unique `--dry-run` prefix without `=`, or for `n` in a fully classified short cluster. Any other long option, unknown short letter, missing option value, or `=` on a flag sets `unknown`. `capture.py:258-259` then records an unresolved push, so that command is not treated as a dry run.

`capture.py:386-406` still sets `pushed` only when that push is observed, resolved, and the sole command in a sealed success. `flags()` at `capture.py:168-180` still matches option names exactly.

Static review only. No files edited and no tests or live commands run.

VERDICT: SHIP
