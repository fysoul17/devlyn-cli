---
id: issue-429
title: Reject max_age on untimed URLSafeSerializer.loads
complexity: medium
changed_files:
  - src/itsdangerous/serializer.py
  - src/itsdangerous/timed.py
  - src/itsdangerous/url_safe.py
  - tests/test_itsdangerous/test_serializer.py
  - tests/test_itsdangerous/test_timed.py
  - tests/test_itsdangerous/test_url_safe.py
  - CHANGES.rst
---

# Reject max_age on untimed URLSafeSerializer.loads

Source: https://github.com/pallets/itsdangerous/issues/429
Base commit: `672971d66a2ef9f85151e53283113f33d642dabd`.

The reporter signs a value with `URLSafeSerializer("SECRET")`, then calls
`serializer.loads(signed, max_age=-1)`. The call silently returns the value,
although this serializer does not support expiration. Pyright also accepts the
incorrect call. The corresponding timed serializer rejects the expired token.

## Requirements

1. Calling untimed `URLSafeSerializer.loads` with `max_age` must raise `TypeError`.
   No exact exception message is required. Its public type contract must also
   reject this unsupported keyword in Pyright.
2. Preserve ordinary untimed round trips, string and byte tokens, and explicit
   salt handling. Preserve timed `max_age` acceptance and expiration rejection,
   `return_timestamp`, and both serializers' existing `loads_unsafe` behavior.
3. Make the smallest source and regression-test change that corrects the argument
   contract. Do not introduce new `Any` annotations, type-checking suppressions,
   silent exception handling, dependencies, or altered tool settings. Existing
   tests must continue to pass. Pre-existing annotations need no unrelated cleanup.

## Scope

The listed `changed_files` are the allowed output surface; editing every file is
not required. Add a concise `CHANGES.rst` entry only if needed for the public
behavior change. Do not change unrelated modules or APIs. The supplied files under
`docs/specs/issue-429/` are fixed acceptance inputs and must remain unchanged.

## Verification

Run the commands in `spec.expected.json` from the repository root in the prepared,
activated Python environment. Existing tests and the runtime acceptance script
must import this checkout's `src/itsdangerous`. The typing acceptance script uses
that source directory explicitly and checks the exact invalid call, alongside
valid untimed and timed calls. Reinstall the current source before the package
type-completeness check so it evaluates the resulting package.

The runtime script checks the unsupported keyword and preserves valid salt,
token, expiration, timestamp, and unsafe-loading behavior. The typing script must
report one argument error at the invalid untimed `max_age` keyword and no other
errors. All commands must exit successfully after the repair.
