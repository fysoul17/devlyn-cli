# 0259 amendment 1 review, round 1 (read-only)

Read-only review in `/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0259-amend1`. Do not edit, create or
delete any file and do not run commands that write. Running
`python3 -m pytest -q -p no:cacheprovider autoresearch/experiments/0259` is fine. Never open anything under
`~/.local/share/nx01`.

A measured run is live. One cell lost its OAuth session while the Mac slept. Its 401 showed up only on the CLI's retry
event, so 0233's classifier did not see it, and the cell was scored as a product failure with zero model turns.

Read:
- `autoresearch/experiments/0259/amendment-1.md` (the specification);
- `autoresearch/experiments/0259/quota.py`;
- `autoresearch/experiments/0259/reclassify.py`;
- the new tests in `autoresearch/experiments/0259/test_apparatus.py`;
- the README change;
- for context, `autoresearch/experiments/0233/quota.py`, the stop and verdict code in
  `autoresearch/experiments/0259/run_cell.py`, and the archive path in `autoresearch/experiments/0259/driver.py`.

Root ran a dry classification over the live run's finished cells. Only the affected cell matches, with kind
`claude authentication retry`. No cell has been graded.

Questions:
1. Is the amendment legitimate? Is it decided blind to outcomes and arm-neutral? Is it consistent with the inherited
   fault rules? Is there a reason it should not be applied, or should be narrower or wider?
2. Does `quota.py` match exactly the amendment's shape and nothing else? Consider false positives (for example a
   recovered 401 followed by a later unrelated `api_error`), double counting with 0233's rule, and unchanged 0233
   behavior.
3. Does `reclassify.py` rewrite only what the amendment allows, atomically and loudly? Does the driver's existing path
   then archive and rerun the cell correctly? Does `decide.py` treat the archived attempt correctly?
4. Are the tests sound?

Answer in under 40 lines:

```
VERDICT: SHIP | REVISE
FINDINGS:
- [HIGH|MEDIUM|LOW] <file> — <problem> — <concrete fix>
```

HIGH means the run or its decision could be wrong.
