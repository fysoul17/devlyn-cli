# 0260 code review, round 1 (read-only)

You are reviewing a research apparatus in the devlyn-cli repository, read-only. Do not edit, create or delete any
file, and do not run commands that write (running the offline test suite is allowed:
`python3 -m pytest -q -p no:cacheprovider autoresearch/experiments/0260`). Repository root:
`/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0260-saint-exupery`. You may read
`~/.local/share/nx01/0259-live/control/packages/B/package/` (the real B package). Never open any `home/`, `auth/` or
credential file.

Read:
1. `autoresearch/experiments/0260/DESIGN.md` (r2) — the specification. Round 1 of the design review is in
   `autoresearch/experiments/0260/results/design-r1-*.md`; r2 applied it. Check r2 too.
2. `autoresearch/experiments/0260/results/build-contract.md` — what the implementer was asked to build.
3. Everything else in `autoresearch/experiments/0260/` against its 0259 origin
   (`diff -r autoresearch/experiments/0259 autoresearch/experiments/0260`, ignoring `results/` result files).

Check:
1. Does C's edit do exactly the DESIGN's two ordered edits in the three files, and fail closed on a B without either
   source or with either twice? Do the qualification checks in `instructions.py` assert the same edit?
2. Is every 0259 → 0260 delta one the DESIGN or contract asks for, and is anything 0259 had (an assertion, a check,
   a test) lost?
3. `judge.py`: is a container that never starts kept out of the recorded attempts in both `probe` and `run`, with
   earlier cells kept and the container removed on every path, and are start-phase failures still recorded as 0259
   did? Any path where a real probe or witness failure is now dropped, or a hang is recorded?
4. Amendment 1 path: does a cell with the retry-only authentication shape end STOP during the run and get archived
   and rerun in the same slot?
5. Anything that would make a result wrong or unreadable.

Answer in this format, under 60 lines:

```
VERDICT: SHIP | REVISE
FINDINGS:
- [HIGH|MEDIUM|LOW] <file>:<line> — <problem> — <concrete fix>
```

HIGH means a result could be wrong, an arm could differ by more than the edit, or a fault could be recorded as data.
