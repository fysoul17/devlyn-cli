# P2 implementation instructions

Family: ordering/precedence. Apply this request alone to the pinned tree.

## Reference design

Change exactly `src/dateutil/parser/_parser.py` and `tests/test_parser.py`. The reference and twin must have identical changed-file sets and identical tests.

The existing parser already extracts a name and numeric offset, and passes both to a `tzinfos` callback. For example, `2012-01-19 17:21:00 -0300 (BRST)` yields `res.tzname == 'BRST'` and `res.tzoffset == -10800`. Extend the mapping path in `_build_tzaware` and `_build_tzinfo`:

- The mapping is applicable if either `(res.tzname, res.tzoffset)` or `res.tzname` is present. Keep callback dispatch first and preserve the existing resolution chain when neither mapping key exists.
- In `_build_tzinfo`, for a mapping choose the exact pair when it is present; otherwise use the existing name lookup. Key presence is distinct from value truthiness. Preserve `None`, integer zero, and all existing value conversions.
- Reuse `_assign_tzname` exactly as the existing mapped-timezone branch does, so fold/name handling does not regress. Do not add offset agreement checks.
- Preserve the outer `ignoretz` guard in `parse`; it must bypass the entire mapping/callback path.
- Describe the tuple option in the class method's `tzinfos` docstring and the module-level `parse` documentation in this same file. No documentation file needs changing.

## Public tests added to the repository

Use fixed full date/time inputs. Parameterize the module-level API and an instance's `parse` method where useful.

- A compound test uses `{('BRST', -10800): tzoffset('PAIR', -7200), 'BRST': tzoffset('NAME', -14400)}`. Parse the named numeric-offset input above, then a name-only input, then the first input with `ignoretz=True`. Assert timezone identity for the first two and a naive result for the third. This directly exercises priority and fallback without hitting the target mechanism.
- Exact-pair conversions for a `tzinfo` object, a timezone string such as `'UTC+0'`, integer `3600`, and integer `0`.
- Pairs with an absent component: `('BRST', None)` for a name-only input and `(None, -10800)` for a numeric-only input. Use non-`None` mapping values.
- A mismatching pair falls back to an existing name entry. With no matching mapping key, a numeric offset still resolves through the built-in path.
- An invalid selected pair value, such as `object()`, raises `TypeError` even if a valid name fallback is available.
- A spy callback is called exactly once with the parsed pair; an `ignoretz=True` call never invokes it. Existing name-key and callback `None` regressions remain in place.

Do not add a public case combining an exact tuple value of `None` with a non-`None` name fallback. Do not include that combination in any parameterized or generated test. It is the single target interaction, not required for the other public conversion and priority cases. Existing tests only exercise name-key/callback `None` values, so they are unaffected.

## Twin construction

Keep `_build_tzaware`'s applicability test, callbacks, documentation, and public tests identical to the reference. Only change exact-pair value selection inside `_build_tzinfo` for mappings: fetch the pair with `.get(pair)` and treat a returned `None` as a miss, then fetch the name entry. In pseudocode, the deviating selection is:

```python
tzdata = tzinfos.get((tzname, tzoffset))
if tzdata is None:
    tzdata = tzinfos.get(tzname)
```

The reference instead distinguishes an absent pair from a present pair whose value is `None`, by membership or a sentinel. Do not use a generic truthiness check: zero-valued pairs must still work on the twin. This one conflation of absence and `None` makes a conflicting name fallback override the explicit request for a naive result.

Use ordinary production naming and no comments identifying the defect. The public tests avoid exactly this conflicting-`None` combination; all other added tests and the existing suite must pass, including the project coverage target.
