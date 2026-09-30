#!/bin/sh
# Clause (spec Req 2): evolve(name=new, alias=None) in one call derives the alias from the new name; name/alias/alias_is_default agree.
set -eu
cd "$1"
PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1 python3 - "$PWD" <<'PY'
import os, sys
import attr

assert os.path.realpath(attr.__file__).startswith(os.path.realpath(sys.argv[1]) + "/src/"), attr.__file__


@attr.s(auto_attribs=True)
class C:
    _private: int = attr.ib(alias="external")
    _plain: int = 0


for original in (attr.fields(C)._private, attr.fields(C)._plain):
    got = original.evolve(name="_next", alias=None)
    triple = (got.name, got.alias, got.alias_is_default)
    if triple != ("_next", "next", True):
        sys.exit(f"violated: {original.name}.evolve(name='_next', alias=None) -> {triple!r}")
print("holds")
PY
