#!/bin/sh
# Clause (spec Requirement 5): a failing forced resolve_types leaves field types and the resolution cache unchanged; a previously cached class stays a cache hit on the next unforced call.
set -eu
cd "$1"
PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1 python3 - "$PWD" <<'PY'
import os, sys
import attrs

assert os.path.realpath(attrs.__file__).startswith(os.path.realpath(sys.argv[1]) + "/src/"), attrs.__file__


@attrs.define
class C:
    value: "Token"  # noqa: F821


assert attrs.resolve_types(C, localns={"Token": int}) is C
field = attrs.fields(C).value
assert field.type is int and C.__dict__["__attrs_types_resolved__"] is C

try:
    attrs.resolve_types(C, localns={}, force=True)
except NameError:
    pass
except TypeError as e:
    sys.exit(f"violated: resolve_types does not accept force=True: {e}")
else:
    sys.exit("violated: failing forced resolution did not propagate NameError")

if field.type is not int:
    sys.exit(f"violated: failed forced resolution changed field type to {field.type!r}")
if C.__dict__.get("__attrs_types_resolved__") is not C:
    sys.exit(f"violated: failed forced resolution changed the cache marker to {C.__dict__.get('__attrs_types_resolved__')!r}")
try:
    got = attrs.resolve_types(C, localns={})
except NameError:
    sys.exit("violated: unforced call after failed refresh re-evaluated annotations and raised NameError")
assert got is C
assert attrs.resolve_types(C, localns={"Token": str}) is C
if field.type is not int:
    sys.exit(f"violated: unforced call after failed refresh re-evaluated and set {field.type!r}")
print("holds")
PY
