#!/bin/sh
# Clause (spec Requirement 5): a failing forced resolve_types leaves the cache state unchanged: a cached class stays a cache hit, and a class without its own marker gains none.
set -eu
cd "$1"
PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1 python3 - "$PWD" <<'PY'
import os, sys
import attrs

assert os.path.realpath(attrs.__file__).startswith(os.path.realpath(sys.argv[1]) + "/src/"), attrs.__file__

MISSING = object()


def failing_force(cls):
    try:
        attrs.resolve_types(cls, localns={}, force=True)
    except NameError:
        return
    except TypeError as e:
        sys.exit(f"violated: resolve_types does not accept force=True: {e}")
    sys.exit(f"violated: failing forced resolution of {cls.__name__} did not propagate NameError")


# Previously cached class stays a cache hit.
@attrs.define
class C:
    value: "Token"  # noqa: F821


assert attrs.resolve_types(C, localns={"Token": int}) is C
failing_force(C)
if attrs.fields(C).value.type is not int:
    sys.exit("violated: failed forced resolution changed the cached field type")
if C.__dict__.get("__attrs_types_resolved__", MISSING) is not C:
    sys.exit("violated: failed forced resolution cleared the cache marker of a cached class")
try:
    assert attrs.resolve_types(C, localns={}) is C
except NameError:
    sys.exit("violated: unforced call after failed refresh re-evaluated annotations")


# Never-resolved class gains no marker.
@attrs.define
class U:
    value: "Missing"  # noqa: F821


before = attrs.fields(U).value.type
failing_force(U)
if "__attrs_types_resolved__" in U.__dict__:
    sys.exit(f"violated: failed forced resolution added a marker {U.__dict__['__attrs_types_resolved__']!r} to a never-resolved class")
if attrs.fields(U).value.type != before:
    sys.exit("violated: failed forced resolution changed an unresolved field type")


# Subclass that only inherits its base's marker gains no own marker.
@attrs.define
class Base:
    value: "Token"  # noqa: F821


assert attrs.resolve_types(Base, localns={"Token": int}) is Base


@attrs.define
class Child(Base):
    extra: "Token"  # noqa: F821


assert "__attrs_types_resolved__" not in Child.__dict__
failing_force(Child)
if "__attrs_types_resolved__" in Child.__dict__:
    sys.exit(f"violated: failed forced resolution wrote {Child.__dict__['__attrs_types_resolved__']!r} into a subclass that only inherited the marker")
if Base.__dict__.get("__attrs_types_resolved__", MISSING) is not Base:
    sys.exit("violated: failed forced resolution of a subclass changed the base marker")
print("holds")
PY
