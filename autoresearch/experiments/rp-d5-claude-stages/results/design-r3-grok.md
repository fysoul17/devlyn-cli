## HIGH — Explore/Verify still moves on an unpinned write scan

The named round-2 cases are in the prose: heredoc bodies are stripped only for redirection scanning, `write_text(` stays in the payload, `2>&1` and `>/dev/null` are not writes, `cp`/`mv`/`tee`/`patch` use word boundaries, and `cat` of the helper is a read. Two implementers can still disagree on the first write, and every later look follows that choice.

- `open(...)` in write/append mode has no pattern. The fixture list covers `write_text` only. `open(p, "w")` can be a write or a mutation-unknown inline script.
- "A temporary directory" is not the prefix list in `0234/diagnostics.py` (`/tmp/`, `/private/tmp/`, `$TMPDIR/`, `tmp/`, `.devlyn/`). `>/tmp/out` can still be the first write. That regex already ignores `2>&1`, because `&` never matches the target class.
- "Full text is kept for every other predicate" and "a command word of the pipeline" disagree inside a heredoc. A payload that contains the word `cp` becomes a write if the command-word scan sees the payload.
- A mutation-unknown row is reported and then ignored by the boundary. A later look is still Explore. The stage table then states that no write preceded it. `python3 fix.py`, `rm`, and `Path.write_bytes` never enter the write list, and they are mutation-unknown only when the command is an inline script that matched nothing else.

**Fix:** Keep command-word predicates (`cp`, `mv`, `tee`, `patch`, `sed -i`, `git apply`, pytest, the deliver list, the shell reads) on the heredoc-stripped pipeline only. Keep in-process writes on the full text, pinned to `\bwrite_text\s*\(`, `\bwrite_bytes\s*\(`, and an `open(` whose mode literal begins with `w`, `a`, or `x`. A variable mode stays mutation-unknown. Reuse the diagnostics redirection regex and its exclude prefixes. If any mutation-unknown row has an earlier index than the first write, still show the look counts and mark that slot's Explore/Verify split unsupported. Accounting `UNKNOWN` still fails the smoke; this flag does not. Add fixtures for `open(p,"w")`, `open(p,"rb")`, `>/tmp/x`, `cp` inside a payload, `python3 fix.py`, and a look after `python3 -c 'print(1)'`. Freeze that oracle before the run (**No guesswork**).

## MEDIUM — Shell-read path tokens are still prose

Read/Grep/Glob with no path, or with the worktree root, is a task-tree look. That closes the tool case from round 2. `rg`, `grep`, `cat`, `ls`, `head`, `tail`, and `sed -n` are classified by "path arguments" with no split rule. `rg is_expired src/expiry/__init__.py` can come out Orient, Explore, or Other. Those calls are the exploration this run exists to count, and Other hides them in the same bucket as unmatched commands.

**Fix:** `shlex.split` the heredoc-stripped command. Flags are not paths. For `rg`/`grep`, the first non-flag token is the pattern unless `-e` or `-f` is present; the remaining non-flag tokens are paths. For `cat`, `ls`, `head`, `tail`, and `sed -n`, every non-flag token is a path. Zero paths, or all paths in the task tree or at the root, is look. All paths under `CLAUDE.md`, `AGENTS.md`, or `skills/` is orient. A mix is Other. A token that is not a worktree path makes the call Other. Fixtures: `rg is_expired src/expiry/__init__.py`, `grep -n deadline src/limitcli/__init__.py`, `ls -la`, and `cat CLAUDE.md src/expiry/__init__.py`.

## LOW — The repeat key adds a working directory the tool input does not have

Claude's Bash input is the command text, not a cwd field. The cell cwd is `/cell/work`. A second component parsed out of `cd` splits or merges repeats that the full command string already distinguishes.

**Fix:** The operation key is the tool name plus the canonical JSON input object. A cwd field counts only when that object has one.

## What holds

A new run is required. The g01/g02 verdicts carry usage and ids and no tool name or path. Effort is the right second factor: those slots are 23–28 turns and about 80% thinking, which is what `max` versus `high` changes. Four serial slots with the Z0 order swap separate task from effort. Codex stays out. `0254/audit.py` is Claude terminal bodies; a Codex slot would not identify a Claude stage. The Codex gap stays motivation. The prediction is falsifiable, and n=1 is stated as one outcome per cell.

Replacing the nominee with a descriptive repeats table is the sound resolution of Astra's removal finding and of the round-2 removal rule. Full input, including Read offset/limit, Grep pattern, and the heredoc payload, stops the old key from collapsing different reads. The table claims neither "unnecessary" nor "devlyn-caused." Nothing is ranked, pooled, or selected. Adoption stays a later design under the owner ladder (total wall, input, and output per completed task, failures included). Putting a state-equivalence tester back would rebuild the rule this draft correctly deleted (**No overengineering**).

Accounting is implementable as written. One row per `0254` receipt in `index.jsonl` order; `thinking_tokens` is an integer no greater than `output_tokens`; every request's `output_config.effort` is checked; foreground children sit in `totals`; headline input is uncached plus cache read plus cache write. Tool identity is the terminal response `content[]`, joined by `message_id`. Bash exit codes come from the project-JSONL result text, as in `diagnostics.py`. `task-complete.py` prints one JSON object, and only `COMPLETE` or `CLEANUP_PENDING` with `delivery_status` `COMPLETE` opens the post-delivery region. Slot wall is `owner_seconds`, the monotonic interval around `docker start -a` in `0251/cell.py`. Leaving index timestamps out of the stage table is required: `audit.py` never validates them.

| Round-2 finding | Round-3 status |
|---|---|
| Astra HIGH: heredoc strip drops writes; `cat` of the helper becomes Deliver | Named cases fixed; the boundary pin above is still open |
| Astra MEDIUM: removal eligibility | Resolved: no nominee; full-input identity; no devlyn-caused claim |
| Grok HIGH: removal rule does not determine a nominee | Resolved by the same deletion |
| Grok MEDIUM: pathless Read/Grep/Glob; `2>&1`; `>/dev/null`; word boundaries | Tool case and the named redirections are fixed; shell path tokens and temp prefixes remain |

VERDICT: REVISE
