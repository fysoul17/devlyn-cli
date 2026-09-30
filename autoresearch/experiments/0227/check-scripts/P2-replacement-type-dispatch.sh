#!/bin/sh
# Clause (spec Req 3/4): a nested serializer's returned value, incl. its type, decides recursion; scalar replacements stop traversal, replacements' children are visited.
set -eu
cd "$1"
PYTHONPATH="$PWD/src" PYTHONDONTWRITEBYTECODE=1 python3 - "$PWD" <<'PY'
import os, sys
import attr
import attrs

assert os.path.realpath(attr.__file__).startswith(os.path.realpath(sys.argv[1]) + "/src/"), attr.__file__


@attrs.define
class Child:
    secret: str


@attrs.define
class Root:
    payload: list


failures = []


def run(name, root, replace, expected, check_calls=None):
    calls = []

    def hook(inst, attribute, value):
        calls.append((inst, attribute, value))
        return replace(inst, value)

    try:
        out = attr.asdict(root, value_serializer=hook)
    except Exception as e:  # noqa: BLE001 - any exception violates the clause
        failures.append(f"{name}: raised {type(e).__name__}: {e}")
        return
    if out != expected:
        failures.append(f"{name}: got {out!r}, expected {expected!r}")
        return
    if check_calls is not None:
        msg = check_calls(calls)
        if msg:
            failures.append(f"{name}: {msg}")


def pick(target, replacement):
    return lambda inst, value: replacement if inst is None and value is target else value


def never_seen(forbidden):
    return lambda calls: next(
        (f"original child traversed ({v!r})" for _, _, v in calls
         if type(v) in (str, int) and v in forbidden), None
    )


# nested attrs instance -> scalar: emitted, original never traversed
child = Child("private")
run("attrs->str", Root([child]), pick(child, "redacted"), {"payload": ["redacted"]}, never_seen({"private"}))
child = Child("private")
run("attrs->int", Root([child]), pick(child, 5), {"payload": [5]}, never_seen({"private"}))

# nested list -> scalar
inner = [1]
run("list->int", Root([inner]), pick(inner, 0), {"payload": [0]}, never_seen({1}))
inner = [1, 2]
run("list->str", Root([inner]), pick(inner, "ab"), {"payload": ["ab"]})

# nested dict -> scalar / list
inner = {"k": 1}
run("dict->int", Root([inner]), pick(inner, 9), {"payload": [9]})
inner = {"k": 1}
run("dict->list", Root([inner]), pick(inner, [5]), {"payload": [[5]]})

# nested scalar -> collection / attrs instance: replacement's children visited normally
seven = 7
repl_child = Child("c")


def scalar_to(replacement):
    return lambda inst, value: replacement if inst is None and type(value) is int and value == seven else value


def children_visited(calls):
    if not any(i is None and a is None and v is repl_child for i, a, v in calls):
        return "replacement child element not offered to serializer"
    if not any(i is repl_child and a is attrs.fields(Child).secret for i, a, _ in calls):
        return "replacement child's field not visited"
    return None


run("int->list[attrs]", Root([seven]), scalar_to([repl_child]), {"payload": [[{"secret": "c"}]]}, children_visited)
run("int->attrs", Root([seven]), scalar_to(repl_child), {"payload": [{"secret": "c"}]},
    lambda calls: None if any(i is repl_child for i, _, _ in calls) else "replacement attrs instance not traversed")
run("int->dict", Root([seven]), scalar_to({"k": repl_child}), {"payload": [{"k": {"secret": "c"}}]})

if failures:
    sys.exit("violated:\n" + "\n".join(failures))
print("holds")
PY
