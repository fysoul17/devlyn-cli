"""Independent behavioral checks for explicit type refreshes."""

import json

import attr
import attrs
import pytest

from typing import Annotated


def o1():
    @attrs.define
    class C:
        value: "Token"

    field = attrs.fields(C).value
    assert attr.resolve_types is attrs.resolve_types
    assert attrs.resolve_types(C, localns={"Token": int}) is C
    assert field.type is int
    assert attrs.resolve_types(C, localns={"Token": str}) is C
    assert field.type is int
    assert attrs.resolve_types(C, localns={"Token": str}, force=True) is C
    assert field.type is str
    assert attrs.resolve_types(C, localns={"Token": float}) is C
    assert field.type is str
    assert C.__dict__["__attrs_types_resolved__"] is C
    assert attrs.resolve_types(C, localns={"Token": float}, force=True) is C
    assert field.type is float


def o2():
    @attr.s
    class C:
        value: "Annotated[int, 'tag']" = attr.ib()
        other = attr.ib(type=str)

    value, other = attr.fields(C)
    namespace = {"Annotated": Annotated}
    for include_extras, force, expected in (
        (True, False, Annotated[int, "tag"]),
        (False, True, int),
        (True, True, Annotated[int, "tag"]),
    ):
        assert (
            attr.resolve_types(
                C,
                globalns=namespace,
                include_extras=include_extras,
                force=force,
            )
            is C
        )
        assert value.type is expected
        assert other.type is str
        assert C.__dict__["__attrs_types_resolved__"] is C


def o3():
    @attrs.define
    class C:
        known: "int"
        unknown: "Missing"

    fields = attrs.fields(C)
    original_types = tuple(field.type for field in fields)
    had_marker = "__attrs_types_resolved__" in C.__dict__
    with pytest.raises(NameError):
        attrs.resolve_types(C, localns={})
    assert all(
        field.type is original
        for field, original in zip(fields, original_types)
    )
    assert ("__attrs_types_resolved__" in C.__dict__) is had_marker
    assert attrs.resolve_types(C, localns={"Missing": str}) is C
    assert fields.known.type is int
    assert fields.unknown.type is str
    assert C.__dict__["__attrs_types_resolved__"] is C


def o4():
    @attrs.define
    class C:
        value: "Token"

    assert attrs.resolve_types(C, localns={"Token": int}) is C
    field = attrs.fields(C).value
    marker = C.__dict__["__attrs_types_resolved__"]
    assert field.type is int and marker is C

    with pytest.raises(NameError):
        attrs.resolve_types(C, localns={}, force=True)

    assert field.type is int
    assert C.__dict__["__attrs_types_resolved__"] is marker
    assert attrs.resolve_types(C, localns={}) is C
    assert field.type is int


def o5():
    @attrs.define
    class Base:
        value: "Token"

    assert attrs.resolve_types(Base, localns={"Token": int}) is Base

    @attrs.define
    class Child(Base):
        extra: "Token"

    assert attrs.resolve_types(Child, localns={"Token": str}) is Child
    assert attrs.fields(Child).value.type is str
    assert attrs.fields(Child).extra.type is str
    assert attrs.resolve_types(Child, localns={"Token": float}, force=True) is Child
    assert attrs.fields(Child).value.type is float
    assert attrs.fields(Child).extra.type is float
    assert Child.__dict__["__attrs_types_resolved__"] is Child
    assert attrs.fields(Base).value.type is int
    assert Base.__dict__["__attrs_types_resolved__"] is Base


def o6():
    def transform(cls, attribs):
        assert not attr.has(cls)
        assert (
            attr.resolve_types(cls, localns={"Token": int}, attribs=attribs)
            is cls
        )
        assert (
            attr.resolve_types(
                cls, localns={"Token": float}, attribs=attribs, force=True
            )
            is cls
        )
        return attribs

    @attr.s(field_transformer=transform)
    class C:
        value: "Token" = attr.ib()
        other = attr.ib(type=str)

    assert [field.name for field in attr.fields(C)] == ["value", "other"]
    assert attr.fields(C).value.type is float
    assert attr.fields(C).other.type is str
    instance = C(2.5, "x")
    assert (instance.value, instance.other) == (2.5, "x")


def main():
    rows = {}
    for identifier, check in (
        ("P3-O1", o1),
        ("P3-O2", o2),
        ("P3-O3", o3),
        ("P3-O4", o4),
        ("P3-O5", o5),
        ("P3-O6", o6),
    ):
        try:
            check()
        except BaseException:
            rows[identifier] = False
        else:
            rows[identifier] = True
    print(json.dumps({"rows": rows}, separators=(",", ":")))


if __name__ == "__main__":
    main()
