#!/bin/sh
# Clause (spec Constraint): Attribute.evolve's docstring documents the alias=None reset, and its "resulting name" statement holds when name changes in the same call.
set -eu
cd "$1"
PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1 python3 - "$PWD" <<'PY'
import os, sys
import attr

assert os.path.realpath(attr.__file__).startswith(os.path.realpath(sys.argv[1]) + "/src/"), attr.__file__

doc = " ".join((attr.Attribute.evolve.__doc__ or "").split())
if "alias=None" not in doc:
    sys.exit("violated: evolve docstring does not document alias=None reset")

if "resulting name" in doc:

    @attr.s(auto_attribs=True)
    class C:
        _private: int = attr.ib(alias="external")

    got = attr.fields(C)._private.evolve(name="_next", alias=None)
    if got.alias != "next":
        sys.exit(f"violated: docstring says alias comes from the resulting name, but evolve(name='_next', alias=None) gave alias {got.alias!r}")
print("holds")
PY
