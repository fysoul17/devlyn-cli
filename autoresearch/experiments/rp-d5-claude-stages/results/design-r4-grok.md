## HIGH — The pipeline split breaks quotes, then asks `shlex` to parse the pieces

The pipeline view is the heredoc-stripped command split on `|`, `;`, `&&`, `||`, and newlines, then `shlex` (`DESIGN.md` lines 120–123). That split is a character split. Two implementers diverge on commands this run will see.

- `python3 -c 'print(1); cp a b'` becomes a second command whose word is `cp`, so the row is a write and becomes the first write. A quote-aware split is one `python -c` command: mutation-unknown, and Explore/Verify is unsupported if it precedes the first write.
- `rg "is_expired|stale" src/expiry/__init__.py` splits inside the quotes. `shlex.split` then raises `ValueError`. The design has no class for that failure. One implementation marks Other; another aborts the slot.

The heredoc strip already keeps a payload `cp` off the command-word scan. The operator split undoes that protection for quotes. This is the first-write boundary the stage table hangs on (**No guesswork**).

**Fix:** Split on those operators only outside single quotes, double quotes, and the heredoc strip. A `shlex` failure makes that Bash call Other. A quoted `cp`, `rm`, `mv`, `tee`, or `sed` is not a command word. Freeze the oracle before c01, and make those tests a precondition of c01. The smoke's "no UNKNOWN" check does not cover this: `python3 -c 'print(1); cp a b'` is unknown, and `rg "is_expired|stale" src/expiry/__init__.py` is a task look.

### MEDIUM — Ordinary shell looks still fall into Other

The shell-read paragraph both excludes the `rg`/`grep` pattern from the path list and says a token that is not a worktree path makes the call Other. `rg is_expired src/expiry/__init__.py` is therefore a task look under one reading and Other under the other. The fixture names the command and does not state the label.

Flag operands are also path tokens under the written rule, because only tokens that start with `-` are flags:

- `head -n 40 src/expiry/__init__.py` treats `40` as a path and becomes Other.
- `sed -n '1,80p' CLAUDE.md` treats the script as a path and becomes Other, so an instruction read misses Orient.
- `rg -g '*.py' is_expired src/expiry/__init__.py` takes `*.py` as the pattern.
- `git diff HEAD` and `git log -n 5` depend on an undefined "revision". `find . -name '*.py'` treats `*.py` as a path.

Those are the exploration commands the stage table is supposed to count. Other then mixes them with unmatched commands.

**Fix:** Only path-position tokens are judged, and the `rg`/`grep` pattern is not one of them. Flags in a pinned consume-list (`-n` for `head`/`tail`, the `sed -n` script, `rg -g`/`-t`/`-A`/`-B`/`-C`/`-e`/`-f` and their long forms, `grep -e`/`-f`) take the next token. For `git diff`, `git log`, and `git show`, a token is a revision when it is a flag or does not normalize into the worktree; revisions do not make the call Other. `find` predicates and their arguments are not paths. Expected labels for the existing fixtures, plus these four, are frozen with the oracle above.

### MEDIUM — `cp` / `mv` / `rm` set the first write where a temp redirection does not

The redirection arm reuses the `0234/diagnostics.py` regex and excludes `/dev/null`, `/tmp/`, `/private/tmp/`, `$TMPDIR/`, `tmp/`, and `.devlyn/`. The command-word arm treats every `cp`, `mv`, and `rm` as a write, with no path test. `>/tmp/x` leaves the boundary alone. `rm /tmp/x` becomes the first write and moves every later look from Explore to Verify, with the unsupported flag clear. The same hole is open for the prefix list and for `sed`:

- "env/sudo-style prefixes" is not a list. `sudo cp a b` is a write if `sudo` is stripped, and Other if the command word stays `sudo`.
- "command word `sed -i`" can mean argv exactly `-i`. `sed -i.bak` is then missed, so a real edit never moves the boundary. The diagnostics pattern `\bsed\s+-i\b` already matches `-i.bak`; the design does not cite it.

**Fix:** The stripped prefixes are `sudo`, `command`, `nohup`, `time`, and leading `VAR=value`. `git apply` is argv `git` then `apply`. `sed` is a write when an argument is `-i`, `--in-place`, or starts with `-i`. `cp`, `mv`, and `rm` are writes only when a path argument normalizes into the task tree and outside those exclude prefixes. All-excluded is not a write. Any other path is mutation-unknown. Fixtures: `rm /tmp/x`, `>/tmp/x`, `sudo cp a b`, `sed -i.bak f`, `dispatch`.

### MEDIUM — The `complete` stdout decoder is still a choice

The boundary opens on the first `complete` stdout object with `status` `COMPLETE`, or `CLEANUP_PENDING` with `delivery_status` `COMPLETE`. "Parsed" is undefined. `task-complete.py` prints one JSON object, and retained helper output is that object plus a trailer (`0242/fixtures/retained-helper-events.json`: a JSON line, then `Local commit: …`). `json.loads` of the whole tool-result string fails and, by the written rule, sends the boundary and every later row to Other. `JSONDecoder.raw_decode`, which `rp-d4` `json_objects` already uses for this helper, opens After delivery. The tail of every successful slot follows that choice.

**Fix:** Scan the tool-result text the way `0234/diagnostics.py` builds it (string content as-is, any other content JSON-encoded). `raw_decode` from each `{`, leaving a trailer in place. Open the boundary on the first object from a `complete` invocation that meets the status rule. The invoking row stays Deliver. Freeze the trailer string as a fixture whose following row is After delivery.

VERDICT: REVISE
