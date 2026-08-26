---
complexity: small
---

# Archive prune null-state safety

`/devlyn:resolve` can complete and move the current run, then exit with a traceback while
best-effort pruning inspects an older archive whose `phases.final_report` value is JSON
`null`. This spec closes that observed terminal artifact failure before the per-task lane
is sealed.

## Evidence

- Runs `rs-20260826T142817Z-467b7b339412` and
  `rs-20260826T132929Z-c65aab72cbc8` moved their current artifacts successfully, then
  `config/skills/_shared/archive_run.py:154` raised `AttributeError` while reading the
  older archive `rs-20260826T131906Z-b4ff91e384a1`.
- The state schema permits `phases.final_report` to be `null` for an in-flight run, and
  the archive contract says such runs are never pruned.

## Subtractive-first decision

1. Keep the existing prune contract and candidate loop; add no recovery wrapper or
   fallback around archive execution.
2. Treat a non-object `final_report` exactly like an absent verdict: not safely complete,
   therefore not a prune candidate.
3. Add only the regression fixture required to prove the observed JSON shape no longer
   crashes or deletes the archive.

## Requirements

1. `prune()` must not raise when a readable state contains
   `{"phases":{"final_report":null}}`.
2. That archive must remain on disk even when completed candidates exceed `keep`.
3. Existing oldest-first pruning of completed runs must remain unchanged.
4. Malformed or unsafe state must continue to fail closed by being skipped.
5. Canonical `config/skills` and tracked `.agents` mirrors must remain byte-identical.
6. Add no dependency, user-facing flag, archive format, or silent exception handler.

## Red-first obligation

Before changing production logic, extend the existing `archive_run.py --self-test` with
the null-`final_report` fixture and retain its raw failing traceback in the resolve run
evidence. Then make the smallest production change and rerun green.

## Authorized implementation surface

- `config/skills/_shared/archive_run.py`
- `.agents/skills/_shared/archive_run.py`

## Verification

```bash
python3 config/skills/_shared/archive_run.py --self-test
diff -q config/skills/_shared/archive_run.py .agents/skills/_shared/archive_run.py
bash scripts/lint-skills.sh
git diff --check
```
