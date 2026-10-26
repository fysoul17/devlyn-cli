# Fix contract: 0259 amendment 1, review round 1

Same hard limits as `results/amend1-contract.md`. Work in `/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0259-amend1` only.

Both reviewers found the same two HIGH problems ([amend1-r1-astra.md](amend1-r1-astra.md),
[amend1-r1-grok.md](amend1-r1-grok.md)):

1. The remembered 401/403 retry status stays in force for the rest of the stream, so a later, unrelated `api_error`
   result is classified as an authentication fault.
2. An explicit terminal `api_error_status`, for example 500, is overridden by an earlier 401 retry.

`amendment-1.md` change 1 has been narrowed; read it again. Do:

- In `autoresearch/experiments/0259/quota.py`, match only what the amended rule now says:
  - The result must have `api_error_status` missing or null.
  - Any `result` event clears the remembered retry status, whether it is classified or not.
  - An `assistant` event whose `message.model` is not `"<synthetic>"` also clears it.
  - 0233's precedence is unchanged.
- Add regression tests:
  - a 401 retry, then a successful result, then a later `api_error` result with null status → no hit;
  - a 401 retry, then a non-synthetic assistant event, then an `api_error` result with null status → no hit;
  - a 401 retry, then an `api_error` result with `api_error_status: 500` → no hit;
  - the d007 shape, with its synthetic assistant event (`message.model: "<synthetic>"`) between the last retry and the
    result, → still detected. Update the existing d007 test to include that event if it lacks it.
- Nothing else changes.

Done means:
- `python3 -m pytest -q -p no:cacheprovider autoresearch/experiments/0259` passes; report the exact output.
- `py_compile` is clean.
- Report the diff.
