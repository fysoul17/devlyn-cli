# 0256 claude B diagnosis (read-only)

Evidence root: `~/.local/share/nx01/0256-live/output/<cell>/`. Transcript = `home/.claude/projects/-cell-work/*.jsonl`. (The read-only helper scripts used for the counts were not kept.)

## Conclusions

1. **No single dominant mechanism.** Claude B's deficit splits into three parts:
   - (a) **Literal scope narrowing on F10/F11.** B leaves unlisted error paths alone and reports them as "unresolved". This explains 3 of the 5 comparative losses (c02, c12, c15). It is the only pattern that is consistent and arm-specific.
   - (b) **Run-to-run variance and noisy assessor findings on the deep tasks** (d05, d27/d28, both I0185 pairs).
   - (c) **A Claude-wide habit of turning narrow evidence into a general mechanism claim.** It produced d28, but also A's d24, so it is not arm-specific.
2. **The principles are read, but never cited as the reason for a failure.** In B cells that loaded AGENTS.md, "No overengineering" is cited by name once (d13, a success). "Prediction:" phrasing from *No guesswork* appears in 4 B cells and 0 A cells. No transcript contains "subtractive", "Saint-Exupéry", "root cause" or "first principles". The behavioral fingerprint that does show up is the **delivery/executor text**:
   - 12/12 B cells that loaded AGENTS.md `cat .devlyn/engines.json` in their first tool call.
   - 8/12 read `task-completion.md`.
   - 4/12 ran the helper.
   - 5 final reports discuss "PR and merge needs the network".
3. **The I0185 B cells had no principles text at all.** The installer did not write CLAUDE.md/AGENTS.md there, because the I0185 repo *is* devlyn-cli (`package.json` `"name": "devlyn-cli"`). So the d23 false completion and the I0185 row and witness gaps cannot come from the principles. d23's twin A cell, d24, makes the same false claim.
4. **d28's false claim came from over-generalizing one run.** A reverted-fix run failed at 10 s per test; from that, d28 claimed every blocking step was bounded. Four minutes earlier it had watched a test with the fix hang for more than 120 s despite the guard, and it blamed "my test harness". d27 (A) hit a similar hang, asked why the guard did not fire, and found the main-thread `f.read` lookup.

## Q1: What B adds in front of Claude

The system prompt snapshots are byte-identical between A and B (`prompt_snapshot` attachment, 10 parts, same lengths). `prompt.txt` differs only in `base_sha`. B adds three things:

- **`instructions` attachment**: `CLAUDE.md` = `@AGENTS.md` (4,112 chars), loaded in 12 of the 14 B cells and not in d10/d23. The parts most plausibly affecting completion (`snapshot/AGENTS.md`):
  - L17 "**No overengineering** — smallest change that closes the goal … Subtractive-first: ask 'what can I delete instead?'"
  - L18 "**No guesswork** — … State the falsifiable prediction BEFORE the experiment"
  - L27 "Challenge the requirement … do not silently pick one interpretation … push back when a simpler path is genuinely better"
  - L28 "A change is finished when no further line, branch, flag … can be removed"
  - L33 "deliver completed, verified requests … (default PR and merge), following `_shared/task-completion.md`"
  - L34 "Executor … when it is unavailable stop with `BLOCKED:<engine>-unavailable`"
- **`skill_listing`**: two extra entries, `devlyn-engines` and `devlyn-ideate` (7,265 vs 6,230 chars). No B cell invoked the Skill tool or read a SKILL.md.
- **Project `.claude/settings.json`**: `ENABLE_PROMPT_CACHING_1H`, `BASH_MAX_TIMEOUT_MS=3600000`. No B cell passed a Bash timeout, so the setting had no effect.

Home `settings.json` is identical in A and B.

## Q2: Pair contrasts

`api` = distinct assistant messages; `test` = Bash calls that ran a test or probe; `dev` = calls touching `.devlyn`, `task-completion` or the helper.

| pair | cell | api | tools | test | dev | wall s | in / out | verdict |
|---|---|---|---|---|---|---|---|---|
| D3 r1 | d01 A | 18 | 18 | 5 | 0 | 258 | 757k / 18.4k | C |
| | d02 B | 13 | 13 | 4 | 1 | 202 | 568k / 17.8k | I |
| D4 r1 | d06 A | 15 | 14 | 9 | 0 | 305 | 537k / 13.9k | C |
| | d05 B | 18 | 17 | 9 | 4 | 282 | 773k / 20.2k | I |
| D4 r2 | d27 A | 23 | 23 | 10 | 0 | 889 | 1031k / 16.3k | I |
| | d28 B | 15 | 17 | 8 | 1 | 424 | 652k / 14.2k | I, false completion |
| I0185 r2 | d24 A | 17 | 19 | 7 | 0 | 462 | 957k / 34.7k | I, false completion |
| | d23 B (no AGENTS.md) | 18 | 19 | 10 | 0 | 421 | 1138k / 42.1k | I, false completion |
| F10 r1 | c01 A | 10 | 9 | 5 | 0 | 81 | 226k / 7.4k | C |
| | c02 B | 15 | 14 | 6 | 3 | 248 | 502k / 11.8k | I |
| F10 r2 | c16 A | 7 | 6 | 3 | 0 | 68 | 146k / 6.5k | C |
| | c15 B | 7 | 7 | 4 | 2 | 200 | ≥196k / 7.6k | I (exit 137) |
| F11 r2 | c11 A | 6 | 5 | 2 | 0 | 52 | 116k / 5.0k | C |
| | c12 B | 11 | 10 | 6 | 7 | 98 | 309k / 8.2k | I |
| F11 r1 (B ok) | c06 A / c05 B | 5 / 12 | 5 / 11 | 3 / 4 | 0 / 3 | 49 / 194 | 97k / 339k | C / C |

B does not skip verification:
- In 5 of the 7 losing pairs above it runs as many or more test commands than A.
- It runs mutation or falsification checks, e.g. c15: "Now a falsification check: my prediction is…"
- It is slower on F tasks (2–4× wall). That extra time goes into delivery reading, mutation runs that hung for 120 s and were moved to the background (c02, c05 and c15 hung; no A F-cell did), and helper bookkeeping (c12: allocate, worktree, commit, fast-forward).

Per pair:
- **F10/F11, the arm-specific pattern.** None of the four A F-cells left Express's default parse error in place: c01, c16, c06 and c11 each add an `entity.parse.failed` handler (`snapshot/server/index.js`). Three of the four B F-cells left it in place: c02, c15 and c12 have only `app.use(express.json())`. The codex assessor's medium finding in each is "body null → Express default 400 before validation".
  - c02 `final.txt`: "Malformed JSON … still gets Express's default HTML 400 … The request didn't cover this case."
  - c12: "## Unresolved / decisions for you … The request didn't list this case, so I left it."
  - This is the 0233 C-r2 sentence again. Counterexample: c05 (B) added the handler ("I also added a small error handler so malformed JSON returns 400") and completed.
  - c02 also shows the executor text at work: "No executor is pinned (`.devlyn/` absent), so I'll implement directly."
- **c15.** It ended itself at step #7: `for p in $(ps … awk '/[t]ests\/server.test.js/'); do kill $p` matched docker-init and its own CLI. This was an accident during cleanup of a hung mutation run, not principle-driven.
- **D3 r1 (d02).**
  - The design moved parser code and bypassed `parseOptions()` overrides (both assessors). d02 disclosed it rather than fixing it: "Nothing in the docs mentions overriding it."
  - It wrote fewer tests than d01 (10+2 vs 12+8) and falsely said eslint/tsc were not installed; d01 ran them.
  - d31 (B r2) succeeded with a milder override caveat, so this is design variance.
- **D4 r1 (d05).** All oracle rows pass. The only failure is a codex medium about a probe descriptor leak in the *test*. d05 read `task-completion.md` twice (#3, #16) and used "My prediction:" phrasing. This looks like assessor-level noise; d27 (A) failed on the same class of finding.
- **I0185.** Both arms fail every cell. The B cells had no AGENTS.md and never read the skills, so B-vs-A differences there (d10's K2/X1, `terminal-alias`) are variance, not package text.

## Q3: Origin of the false claims

**d28.** Timeline from the transcript:
- #6: with the original code, the 4 FIFO tests fail "blocked on the FIFO" in 40.1 s (10 s each). In both arms the construction hang sits inside the guard.
- #7, 17:18:22: with the fix applied, `timeout 300 pytest …` "did not complete within its 120s timeout and was moved to the background". This is direct evidence that some blocking step was *not* bounded by `TIMEOUT = 10`.
- Its thinking: "The run hung due to a deadlock in my test harness, not the fix itself—the writer blocks on the FIFO open before ever reading stdin." It reordered the writer only (#11). It never asked why the 10 s guard did not fire, and the `_call_unblocked(fifo, lf.read)` main-thread open stayed.
- #14: the reverted-fix run again fails at 10 s per test. Text: "With the fix reverted, the FIFO tests fail within their 10 s bound." This becomes the final claim: "each blocking step has a 10-second limit."

The claim's evidence is the one path that runs construction inside the guard. Its own hang was counter-evidence and was explained away.

d27 (A) at the equivalent moment (#16): "The original code run produced no output … meaning something hung despite the guards. I'll debug this." That led to the #19 finding: "`f.read` opening the FIFO on the main thread via `_LazyFile.__getattr__`, before the timeout guard kicks in." d27 spent about 465 s more than d28 on this.

Could the principles have pushed d28 there?
- No principle is cited, and *No guesswork* argues the other way.
- d28's turn sequence shows no early-stop cue: it ran 30 repeat runs and full checks.
- The difference is which hang each cell hit and how deeply it diagnosed it. 0233's d09 (B) has the same mechanism. That is weak evidence of an arm tilt, not proof.

**d23.**
- `final.txt` L12: "a skills directory that didn't exist before is removed again." The evidence is acceptance test 5 ("failed first installation restores absent destination") and its own regression test L92 "stamp failure … first-install parents are removed". Both are single-process failure tests.
- Its contention test (L140) checks refusal, not mkdir-before-lock cleanup, and no test covers K5's interleaving.
- d23 had **no principles text** (no `instructions` attachment) and never read any skill. d24 (A) makes the same claim from the same kind of evidence.
- So the principles could not have caused it.

## Q4: Candidate mechanisms

Ranked by the B failures each explains; B's losses or false completions are c02, c12, c15, d02, d05, d28, d23 and d10.

| # | mechanism | B cells explained | counterexamples |
|---|---|---|---|
| 1 | Literal scope narrowing: unlisted-but-implied error path left as "unresolved / decision for you" (fits AGENTS L17/L27, never cited) | c02, c12, c15 (3); d02 partially (disclose instead of preserve) | c05 B handled it; 0/4 A F-cells narrowed |
| 2 | Deep-task variance and assessor-medium noise | d05, d10, d23 rows, d28 incompleteness (4) | d27 A fails the same way; I0185 fails in all 8 cells, both arms and engines; I0185 B had no principles |
| 3 | Narrow evidence generalized into a mechanism claim; anomaly blamed on the harness | d28, d23 (2) | d24 A does the same; d27 A diagnosed correctly; 0233 d09 (B) as d28 |
| 4 | Delivery/executor bookkeeping overhead (engines.json, task-completion.md, helper) | 0 quality failures directly; explains the cost conditions (wall/input/output) | present in every B success (d13, d20, e05, c05, d31) |
| 5 | Accidental self-kill during process cleanup | c15 (1) | d28 `pkill -f` killed its own shell (exit 144) and recovered |

Mechanism 1 is the only one that is both repeated (0233 and 0256) and absent in A. The others are either shared with A or explain cost rather than quality. With two replicates, every count above is a screen, not a rate.
