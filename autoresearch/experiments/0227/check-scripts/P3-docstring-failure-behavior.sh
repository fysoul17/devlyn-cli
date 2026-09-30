#!/bin/sh
# Clause (spec Constraint): resolve_types' docstring describes force and its failure behavior, and the described failure behavior (types and cache left unchanged) matches the code.
set -eu
cd "$1"
PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1 python3 - "$PWD" <<'PY'
import os, re, sys
import attr
import attrs

assert os.path.realpath(attr.__file__).startswith(os.path.realpath(sys.argv[1]) + "/src/"), attr.__file__

doc = " ".join((attr.resolve_types.__doc__ or "").split())
m = re.search(r"force \(bool\):(.*?)(Raises:|$)", doc)
if not m:
    sys.exit("violated: resolve_types docstring does not describe force")
section = m.group(1)
if not re.search(r"fail|rais", section):
    sys.exit("violated: force description does not state failure behavior")

if "unchanged" in section:

    @attrs.define
    class C:
        value: "Token"  # noqa: F821

    assert attrs.resolve_types(C, localns={"Token": int}) is C
    try:
        attrs.resolve_types(C, localns={}, force=True)
    except NameError:
        pass
    else:
        sys.exit("violated: failing forced resolution did not raise")
    if attrs.fields(C).value.type is not int:
        sys.exit("violated: docstring says field types are left unchanged on failure, but they changed")
    if C.__dict__.get("__attrs_types_resolved__") is not C:
        sys.exit(f"violated: docstring says the resolution cache is left unchanged on failure, but the marker became {C.__dict__.get('__attrs_types_resolved__')!r}")
print("holds")
PY
