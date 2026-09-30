"""Independent behavioral checks for the P4 alias reset contract."""

import inspect
import json

import attr
import attrs
import pytest


def o1():
    @attrs.define
    class C:
        _value: int = attrs.field(alias="external", metadata={"tag": 1})

    original = attrs.fields(C)._value
    reset = original.evolve(alias=None, repr=False)
    assert (reset.name, reset.alias, reset.alias_is_default) == (
        "_value",
        "value",
        True,
    )
    assert reset.repr is False
    assert reset.metadata == {"tag": 1}
    assert (original.alias, original.alias_is_default, original.repr) == (
        "external",
        False,
        True,
    )

    @attrs.define
    class D:
        _value: int

    already_default = attrs.fields(D)._value.evolve(alias=None)
    assert (
        already_default.name,
        already_default.alias,
        already_default.alias_is_default,
    ) == ("_value", "value", True)


def o2():
    for slots in (False, True):
        originals = []

        def transform(cls, attributes):
            original = attributes[0]
            originals.append(original)
            return [original.evolve(alias=None).evolve(name="_next")]

        @attr.s(auto_attribs=True, slots=slots, field_transformer=transform)
        class C:
            _value: int = attr.ib(alias="external")

        field = attr.fields(C)._next
        assert (field.name, field.alias, field.alias_is_default) == (
            "_next",
            "next",
            True,
        )
        instance = C(next=3)
        assert instance._next == 3
        assert attr.evolve(instance, next=4)._next == 4
        assert (
            originals[0].name,
            originals[0].alias,
            originals[0].alias_is_default,
        ) == ("_value", "external", False)


def o3():
    for slots in (False, True):
        originals = []

        def transform(cls, attributes):
            originals.append(attributes[0])
            return [attributes[0].evolve(name="_renamed", alias=None)]

        @attr.s(auto_attribs=True, slots=slots, field_transformer=transform)
        class C:
            _original: int = attr.ib(alias="external")

        field = attr.fields(C)._renamed
        assert field.name == "_renamed"
        assert field.alias == "renamed"
        assert field.alias_is_default is True
        assert list(inspect.signature(C).parameters) == ["renamed"]
        instance = C(renamed=3)
        assert instance._renamed == 3
        assert attr.evolve(instance, renamed=4)._renamed == 4
        assert originals[0].name == "_original"
        assert originals[0].alias == "external"
        assert originals[0].alias_is_default is False


def o4():
    @attrs.define
    class C:
        _value: int

    @attrs.define
    class D:
        _value: int = attrs.field(alias="external")

    default = attrs.fields(C)._value
    explicit = attrs.fields(D)._value
    chosen = default.evolve(name="_next", alias="chosen")
    retained = explicit.evolve(name="_next")
    overridden = explicit.evolve(alias="chosen", alias_is_default=True)
    assert (chosen.name, chosen.alias, chosen.alias_is_default) == (
        "_next",
        "chosen",
        False,
    )
    assert (retained.name, retained.alias, retained.alias_is_default) == (
        "_next",
        "external",
        False,
    )
    assert (overridden.alias, overridden.alias_is_default) == ("chosen", True)
    assert (default.name, default.alias, default.alias_is_default) == (
        "_value",
        "value",
        True,
    )
    assert (explicit.name, explicit.alias, explicit.alias_is_default) == (
        "_value",
        "external",
        False,
    )


def o5():
    @attrs.define
    class C:
        _value: int = attrs.field(alias="external")

    original = attrs.fields(C)._value
    with pytest.raises(ValueError):
        original.evolve(alias=None, alias_is_default=False)
    assert (original.alias, original.alias_is_default) == ("external", False)
    reset = original.evolve(alias=None, alias_is_default=True)
    assert (reset.name, reset.alias, reset.alias_is_default) == (
        "_value",
        "value",
        True,
    )


def o6():
    @attrs.define
    class C:
        _value: int = attrs.field(
            alias="external", metadata={"before": 1}
        )

    original = attrs.fields(C)._value
    changed = original.evolve(metadata={"after": 2}, repr=False)
    assert (changed.name, changed.alias, changed.alias_is_default) == (
        "_value",
        "external",
        False,
    )
    assert changed.metadata == {"after": 2}
    assert changed.repr is False
    assert original.metadata == {"before": 1}


def main():
    rows = {}
    for name, check in (
        ("P4-O1", o1),
        ("P4-O2", o2),
        ("P4-O3", o3),
        ("P4-O4", o4),
        ("P4-O5", o5),
        ("P4-O6", o6),
    ):
        try:
            check()
        except BaseException:
            rows[name] = False
        else:
            rows[name] = True
    print(json.dumps({"rows": rows}))


if __name__ == "__main__":
    main()
