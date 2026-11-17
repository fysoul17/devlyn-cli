#!/usr/bin/env python3
"""Resolve and pin the devlyn executor and reviewers; no model dispatch."""
from __future__ import annotations

import runpy
import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
SHARED = Path(__file__).resolve().parent
# Earlier releases also pinned pipeline judge and worker roles; those keys stay as written and select nothing.
RETIRED = ("pair_judge_priority", "roles")


def fail(detail, reason="invalid-engine-config"):
    raise ValueError(f"BLOCKED:{reason}: {detail}")


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def loads(raw):
    try:
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda value: fail(f"invalid JSON constant: {value}"))
    except (json.JSONDecodeError, UnicodeError, TypeError) as exc:
        fail(f"invalid JSON: {exc}")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")


def name(value, field):
    if not isinstance(value, str) or not NAME.fullmatch(value):
        fail(f"{field} must be a nonempty identifier")
    return value


INELIGIBLE = re.compile(r"^executor: no\s*$", re.M)
REVIEW = re.compile(r"^## Review$", re.M)
SECTION = re.compile(r"^## ", re.M)


def choices(shared=SHARED):
    """The engines that may be pinned: as executor, each adapter that does not declare `executor: no`; as reviewer,
    each adapter with a `## Review` section. An adapter that cannot be read as text is no choice and is named on
    stderr; the selected executor's own adapter is still validated by `adapter`."""
    texts, unreadable = {}, []
    for path in sorted((shared / "adapters").glob("*.adapter.md")):
        try:
            if path.is_file():
                texts[path.name.removesuffix(".adapter.md")] = path.read_text(encoding="utf-8")
                continue
        except (OSError, UnicodeError):
            pass
        unreadable.append(repr(str(path)))
    if unreadable:
        print(f"Adapters that cannot be read are not offered: {', '.join(unreadable)}", file=sys.stderr)
    return {"executor": sorted(e for e, text in texts.items() if not INELIGIBLE.search(text)),
            "reviewers": sorted(e for e, text in texts.items() if REVIEW.search(text))}


# Named `<engine>.adapter.md`: on a case-insensitive filesystem Claude Code loads `claude.md` as nested instructions.
def adapter(engine, shared=SHARED):
    name(engine, "engine")
    path = shared / "adapters" / f"{engine}.adapter.md"
    if not path.is_file():
        fail(f"no adapter for {engine}; valid: {', '.join(choices(shared)['executor'])}")
    text = path.read_text(encoding="utf-8")
    if INELIGIBLE.search(text):
        fail(f"{engine} is ineligible as executor")
    return text


def review_start(engine, shared=SHARED):
    """The body of the engine's adapter section `## Review`, trimmed; None when it has none."""
    path = shared / "adapters" / f"{engine}.adapter.md"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    heading = REVIEW.search(text)
    if heading is None:
        return None
    body = text[heading.end():]
    end = SECTION.search(body)
    return body[:end.start() if end else len(body)].strip()


def reviewer(entry):
    """`engine`, `engine/model` or `engine/model/effort` as [engine, model, effort]. Every part obeys the name rule:
    a session pastes model and effort into a start line, and the file may come from the repository."""
    parts = entry.split("/") if isinstance(entry, str) else []
    if not 1 <= len(parts) <= 3 or not all(NAME.fullmatch(part) for part in parts):
        fail(f"not a reviewer name: {entry!r}")
    return (parts + ["", ""])[:3]


def reviewers(entries, shared=None, kept=()):
    """Unique reviewer names; with `shared`, the engine of each name not in `kept` also needs an adapter with a review
    section."""
    if not isinstance(entries, list):
        fail("reviewers must be an array of names")
    seen = set()
    for entry in entries:
        engine = reviewer(entry)[0]
        if shared is not None and entry not in kept and review_start(engine, shared) is None:
            fail(f"no review section for {engine}; valid: {', '.join(choices(shared)['reviewers'])}")
        if entry in seen:
            fail(f"reviewer named twice: {entry}")
        seen.add(entry)
    return entries


def validate(config, shared=SHARED):
    if not isinstance(config, dict):
        fail("configuration must be an object")
    if "executor" in config:
        adapter(config["executor"], shared=shared)
    reviewers(config.get("reviewers", []))
    return config


def read_config(path, *, optional=False, shared=SHARED):
    path = Path(path)
    try:
        if optional:
            try:
                path.lstat()
            except FileNotFoundError:
                for parent in path.parents:
                    try:
                        mode = parent.stat().st_mode
                    except FileNotFoundError:
                        continue
                    if not stat.S_ISDIR(mode):
                        fail(f"cannot read role configuration {path}: {parent} is not a directory")
                    return {}, {"path": str(path.absolute()), "sha256": None}
                raise
        raw = path.read_bytes()
        value = validate(loads(raw), shared=shared)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"cannot read role configuration {path}: {exc}")
    return value, {"path": str(path.resolve()), "sha256": digest(raw)}


def resolve(work, default_engine, *, available=None, shared=SHARED):
    """The project's executor pin, else the invoking CLI, the pinned reviewers, and the engines each may pin; status
    only, never a dispatch decision. No reviewer is chosen that the user did not pin."""
    config, source = read_config(Path(work) / ".devlyn/engines.json", optional=True, shared=shared)
    engine = config.get("executor", default_engine)
    # read_config validates pins; the invoking host needs no adapter to report its own default.
    name(engine, "engine")
    available = available or (lambda candidate: shutil.which(candidate) is not None)

    def presence(candidate):
        return "CLI-present/auth-unchecked" if available(candidate) else "CLI-unavailable"

    pinned = []
    for entry in config.get("reviewers", []):
        part, model, effort = reviewer(entry)
        # A name this release has no review section for is listed, never a failure: another release may have pinned it.
        start = review_start(part, shared)
        pinned.append({"name": entry, "engine": part, "model": model, "effort": effort,
                       "availability": "no-review-section" if start is None else presence(part), "start": start or ""})
    return {"executor": {"engine": engine, "source": "engines.json" if "executor" in config else "default",
                         "availability": presence(engine)},
            "reviewers": pinned, "inactive": [key for key in RETIRED if key in config], "input": source,
            "choices": choices(shared)}


def select(work, default_engine, *, available=None, shared=SHARED):
    """The executor for dispatch. A pin is a promise: an unavailable pinned engine is never substituted."""
    result = resolve(work, default_engine, available=available, shared=shared)
    executor = result["executor"]
    adapter(executor["engine"], shared=shared)
    if executor["source"] == "engines.json" and executor["availability"] == "CLI-unavailable":
        fail(f"pinned executor {executor['engine']} is unavailable; install and authenticate its CLI, "
             f"verify `{executor['engine']} --version`, and retry, or pin an available engine with `devlyn-engines executor <name>`",
             f"{executor['engine']}-unavailable")
    return result


def edit(work, executor, shared=SHARED, *, retired=True):
    """Pin `executor`, or with None clear the executor pin and, with `retired`, the retired keys; other keys keep
    their values."""
    path = Path(work) / ".devlyn/engines.json"
    config, _ = read_config(path, optional=True, shared=shared)
    if executor is None:
        for key in ("executor", *(RETIRED if retired else ())):
            config.pop(key, None)
    else:
        adapter(executor, shared=shared)
        config["executor"] = executor
    write(path, config)


def edit_reviewers(work, entries, shared=SHARED):
    """Pin `entries` as the reviewers, or with none remove them; other keys keep their values. A name already pinned
    exactly as given is kept unasked: another release may have pinned it, and only a new name needs a review section."""
    path = Path(work) / ".devlyn/engines.json"
    config, _ = read_config(path, optional=True, shared=shared)
    if reviewers(entries, shared, kept=config.get("reviewers", [])):
        config["reviewers"] = list(entries)
    else:
        config.pop("reviewers", None)
    write(path, config)


def write(path, config):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not config:
        path.unlink(missing_ok=True)
        return
    fd, temp = tempfile.mkstemp(prefix="engines.json.tmp.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded(config))
        if path.exists():
            os.chmod(temp, path.stat().st_mode & 0o777)
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def self_test():
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        (work / ".devlyn").mkdir()
        path = work / ".devlyn/engines.json"
        here, absent = (lambda engine: True), (lambda engine: False)
        assert resolve(work, "claude", available=here)["executor"] == {
            "engine": "claude", "source": "default", "availability": "CLI-present/auth-unchecked"}
        # An explicit pin binds; retired keys are reported, not validated, and their bytes stay.
        legacy = b'{"executor":"codex","pair_judge_priority":["grok"],"roles":{"worker":{"engine":"unknown"}},"keep":7}\n'
        path.write_bytes(legacy)
        status = resolve(work, "claude", available=here)
        assert status["executor"]["engine"] == "codex" and status["executor"]["source"] == "engines.json", status
        assert status["inactive"] == ["pair_judge_priority", "roles"] and path.read_bytes() == legacy
        # A pin file's status is as before with one more key: who each role may pin, from the shipped adapters.
        # Violating controls: the status as before lacks that key; an adapter alone is no choice (omp has one).
        before = {"executor": {"engine": "codex", "source": "engines.json", "availability": "CLI-present/auth-unchecked"},
                  "reviewers": [], "inactive": ["pair_judge_priority", "roles"],
                  "input": {"path": str(path.resolve()), "sha256": digest(legacy)}}
        assert status == {**before, "choices": {"executor": ["claude", "codex"], "reviewers": ["claude", "codex", "grok"]}}
        assert status != before and select(work, "claude", available=here) == status, status
        every = sorted(p.name.removesuffix(".adapter.md") for p in (SHARED / "adapters").glob("*.adapter.md"))
        assert every == ["claude", "codex", "grok", "omp"] and every not in status["choices"].values(), every
        # A worker profile never becomes the executor.
        path.write_bytes(b'{"roles":{"worker":{"engine":"codex"}}}')
        assert resolve(work, "claude", available=here)["executor"]["engine"] == "claude"
        # Dispatch fails closed for an unavailable pin; the invoking CLI is reported, never blocked.
        path.write_bytes(b'{"executor":"codex"}')
        try:
            select(work, "claude", available=absent)
        except ValueError as exc:
            assert str(exc).startswith("BLOCKED:codex-unavailable:"), exc
        else:
            raise AssertionError("an unavailable pinned executor was dispatched")
        assert resolve(work, "claude", available=absent)["executor"]["availability"] == "CLI-unavailable"
        path.unlink()
        assert select(work, "claude", available=absent)["executor"]["source"] == "default"
        # Pins are validated before any byte changes.
        ineligible = work / "shared"
        (ineligible / "adapters").mkdir(parents=True)
        (ineligible / "adapters/judge.adapter.md").write_text("## Role eligibility\n\nexecutor: no\n", encoding="utf-8")
        (ineligible / "adapters/codex.adapter.md").write_text("# Codex adapter\n", encoding="utf-8")
        path.write_bytes(legacy)
        # A refused name lists only the engines that can execute.
        for engine, shared, message in (("kimi", SHARED, "no adapter for kimi; valid: claude, codex"),
                                        ("grok", SHARED, "grok is ineligible as executor"),
                                        ("grok", ineligible, "no adapter for grok; valid: codex"),
                                        ("judge", ineligible, "ineligible as executor"),
                                        ("../codex", SHARED, "nonempty identifier")):
            try:
                edit(work, engine, shared=shared)
            except ValueError as exc:
                assert str(exc).startswith("BLOCKED:invalid-engine-config:") and str(exc).endswith(message), exc
            else:
                raise AssertionError(f"{engine} was pinned")
            assert path.read_bytes() == legacy
        for bad in (b'{"executor":"codex","executor":"claude"}', b'{"executor":NaN}', b'[]', b'{"executor":"grok"}'):
            path.write_bytes(bad)
            try:
                resolve(work, "claude", available=here)
            except ValueError as exc:
                assert "BLOCKED:invalid-engine-config" in str(exc), exc
            else:
                raise AssertionError(bad)
        path.write_bytes(legacy)
        edit(work, "claude")
        assert loads(path.read_bytes()) == {**loads(legacy), "executor": "claude"}
        edit(work, None)
        assert loads(path.read_bytes()) == {"keep": 7}
        path.write_bytes(b'{"executor":"codex","roles":{}}')
        edit(work, None)
        assert not path.exists()
        # The CLI reports blocks on stderr without a traceback and changes nothing.
        path.write_bytes(b'{"executor":"codex"}')
        proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--workdir", str(work), "--select"],
                              capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PATH": str(work / "no-binaries")})
        assert proc.returncode == 1 and proc.stderr.startswith("BLOCKED:codex-unavailable:"), proc.stderr
        assert "Traceback" not in proc.stderr and path.read_bytes() == b'{"executor":"codex"}'
        # Of the shipped adapters, these can start a reviewer.
        proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--workdir", str(work), "--set-reviewers", "omp"],
                              capture_output=True, text=True, encoding="utf-8")
        assert proc.returncode == 1 and proc.stderr == (
            "BLOCKED:invalid-engine-config: no review section for omp; valid: claude, codex, grok\n"), proc.stderr
        assert path.read_bytes() == b'{"executor":"codex"}'
        reviewer_self_test(work, path)
    print("PASS role-config self-test: executor pin, retired keys inactive, fail-closed selection, atomic validated writes, "
          "and pinned reviewers listed as named, never chosen and never blocking")
    return 0


def reviewer_self_test(work, path):
    """Reviewer pins: existing pins keep working, no engine is chosen for the user, naming, and unavailable reviewers."""
    team = work / "team"
    (team / "adapters").mkdir(parents=True)
    for engine, text in (("alpha", '## Review\n\nalpha "<prompt>"\n'),
                         ("beta", '## Invocation\n\nbeta\n\n## Review\n\n  beta "<prompt>" -m <model>\n\n## Notes\n\nnot it\n'),
                         ("gamma", "executor: no\n\n## Reviewing\n\nnot a review section\n"),
                         ("delta", 'executor: no\n\n## Review\n\ndelta "<prompt>"\n')):
        (team / f"adapters/{engine}.adapter.md").write_text(text, encoding="utf-8")

    def status(available=lambda engine: True, host="alpha", dispatch=False):
        return (select if dispatch else resolve)(work, host, available=available, shared=team)

    def only(*engines):
        return lambda engine: engine in engines

    def names(value):
        return [entry["name"] for entry in value["reviewers"]]

    def refused(action, message=""):
        before = path.read_bytes() if path.exists() else None
        try:
            action()
        except ValueError as exc:
            assert str(exc).startswith("BLOCKED:invalid-engine-config:") and str(exc).endswith(message), exc
        else:
            raise AssertionError(f"accepted; expected {message!r}")
        assert (path.read_bytes() if path.exists() else None) == before

    # PinsKeepWorking: a pin in use resolves as before; a file without reviewers lists none.
    path.write_bytes(b'{"executor":"beta"}')
    for dispatch in (False, True):
        value = status(dispatch=dispatch)
        assert value["executor"] == {"engine": "beta", "source": "engines.json",
                                     "availability": "CLI-present/auth-unchecked"} and value["reviewers"] == [], value
    # A pin is still a promise beside a pinned reviewer; the reviewer never stands in for it.
    path.write_bytes(b'{"executor":"beta","reviewers":["alpha"]}')
    try:
        status(available=only("alpha"), dispatch=True)
    except ValueError as exc:
        assert str(exc).startswith("BLOCKED:beta-unavailable:"), exc
    else:
        raise AssertionError("an unavailable pinned executor was dispatched")
    for raw in (None, b"{}"):
        path.unlink(missing_ok=True)
        if raw:
            path.write_bytes(raw)
        value = status()
        assert (value["executor"]["engine"], value["executor"]["source"], value["reviewers"]) == ("alpha", "default", [])
    # Setting reviewers keeps every other key; `clear` keeps the reviewers.
    path.write_bytes(b'{"executor":"beta","roles":{"judge":"x"},"pair_judge_priority":["y"],"mine":1}')
    edit_reviewers(work, ["alpha"], shared=team)
    assert loads(path.read_bytes()) == {"executor": "beta", "roles": {"judge": "x"}, "pair_judge_priority": ["y"],
                                        "mine": 1, "reviewers": ["alpha"]}
    # Clearing the executor alone keeps the retired keys, the reviewers and other keys byte for byte, and deletes a
    # file left empty. Violating control: `clear` on the same file also removes the retired keys.
    written = path.read_bytes()
    edit(work, None, shared=team, retired=False)
    assert path.read_bytes() == encoded({key: value for key, value in loads(written).items() if key != "executor"})
    path.write_bytes(written)
    edit(work, None, shared=team)
    assert loads(path.read_bytes()) == {"mine": 1, "reviewers": ["alpha"]}
    path.write_bytes(b'{"executor":"beta"}')
    edit(work, None, shared=team, retired=False)
    assert not path.exists()
    # A host that cannot execute is still refused; a review-only adapter never executes.
    refused(lambda: status(host="gamma", dispatch=True), "gamma is ineligible as executor")
    refused(lambda: status(host="delta", dispatch=True), "delta is ineligible as executor")
    refused(lambda: status(host="unknown-host", dispatch=True), "no adapter for unknown-host; valid: alpha, beta")
    refused(lambda: edit(work, "delta", shared=team), "delta is ineligible as executor")

    # NoEngineIsChosenForTheUser: nothing named, nothing chosen, with every reviewer's CLI present.
    path.write_bytes(b'{"executor":"beta"}')
    assert names(status()) == [] and names(status(dispatch=True)) == []
    # Violating control: a picker that fills in another engine would choose one here.
    def picker(value, host="alpha"):
        return names(value) or [e for e in ("alpha", "beta", "delta") if e != host and review_start(e, team)][:1]
    assert picker(status()) == ["beta"] and names(status()) == []
    # Named reviewers are exactly those, in the order named, each with its model, effort and trimmed start.
    edit_reviewers(work, ["beta/model-x/ultra", "delta"], shared=team)
    assert status()["reviewers"] == [
        {"name": "beta/model-x/ultra", "engine": "beta", "model": "model-x", "effort": "ultra",
         "availability": "CLI-present/auth-unchecked", "start": 'beta "<prompt>" -m <model>'},
        {"name": "delta", "engine": "delta", "model": "", "effort": "",
         "availability": "CLI-present/auth-unchecked", "start": 'delta "<prompt>"'}], status()
    # The user's own engine may be named: a fresh run of it.
    edit_reviewers(work, ["alpha"], shared=team)
    assert names(status(host="alpha")) == ["alpha"]

    # Naming: model and effort pass through; a wrong name is refused with the valid engines; nothing moves.
    assert reviewer("beta") == ["beta", "", ""] and reviewer("beta/model-x/ultra") == ["beta", "model-x", "ultra"]
    path.write_bytes(b'{"executor":"beta","reviewers":["alpha"]}')
    for bad in ("gamma", "nobody"):
        refused(lambda: edit_reviewers(work, [bad], shared=team), f"no review section for {bad}; valid: alpha, beta, delta")
    refused(lambda: edit_reviewers(work, ["beta", "beta"], shared=team), "reviewer named twice: beta")
    for bad in ("beta/", "/x", "a/b/c/d", "", "../x"):
        refused(lambda: edit_reviewers(work, [bad], shared=team), f"not a reviewer name: {bad!r}")
    for raw in (b'{"reviewers":"alpha"}', b'{"reviewers":[1]}', b'{"reviewers":["alpha","alpha"]}', b'{"reviewers":["/x"]}'):
        path.write_bytes(raw)
        refused(status)
    # No part can carry shell text, whether set or read from a file the repository ships: a session pastes model and
    # effort into a start line. Allowed control: dots, digits, underscores and hyphens.
    path.write_bytes(b'{"executor":"beta"}')
    for bad in ('beta/x";touch y;"', "beta/m odel", "beta/$(id)", "beta/model/`id`", "beta/a;b"):
        refused(lambda: edit_reviewers(work, [bad], shared=team), f"not a reviewer name: {bad!r}")
        path.write_bytes(json.dumps({"reviewers": [bad]}).encode())
        for dispatch in (False, True):
            refused(lambda: status(dispatch=dispatch), f"not a reviewer name: {bad!r}")
        path.write_bytes(b'{"executor":"beta"}')
    edit_reviewers(work, ["beta/model-4.7_x/ultra"], shared=team)
    assert [(r["model"], r["effort"]) for r in status()["reviewers"]] == [("model-4.7_x", "ultra")]
    # Clearing the reviewers keeps the executor pin, and deletes a file left empty.
    path.write_bytes(b'{"executor":"beta","reviewers":["alpha"]}')
    edit_reviewers(work, [], shared=team)
    assert loads(path.read_bytes()) == {"executor": "beta"}
    path.write_bytes(b'{"reviewers":["alpha"]}')
    edit_reviewers(work, [], shared=team)
    assert not path.exists()

    # Unavailable: every pinned reviewer is listed, the ones that cannot start with why; nothing blocks.
    path.write_bytes(b'{"reviewers":["beta","delta"]}')
    value = status(available=only("alpha", "delta"), dispatch=True)
    assert [(r["name"], r["availability"]) for r in value["reviewers"]] == [
        ("beta", "CLI-unavailable"), ("delta", "CLI-present/auth-unchecked")], value
    # None can start: each is named, and dispatch still selects the executor and claims no reviewer.
    value = status(available=only("alpha"), dispatch=True)
    assert value["executor"]["engine"] == "alpha" and [(r["name"], r["availability"]) for r in value["reviewers"]] == [
        ("beta", "CLI-unavailable"), ("delta", "CLI-unavailable")], value
    # A name with no review section in this release is listed with an empty start, never a failure.
    path.write_bytes(b'{"executor":"beta","reviewers":["gamma/m","ghost","alpha"]}')
    for dispatch in (False, True):
        assert [(r["name"], r["availability"], r["start"]) for r in status(dispatch=dispatch)["reviewers"]] == [
            ("gamma/m", "no-review-section", ""), ("ghost", "no-review-section", ""),
            ("alpha", "CLI-present/auth-unchecked", 'alpha "<prompt>"')]
    # Such a stored name never blocks removing or adding another name; the same name given new is refused, and so is
    # a name given twice. Violating control: checked as new, as before this release, they refuse the whole change.
    edit_reviewers(work, ["gamma/m", "ghost"], shared=team)
    assert names(status()) == ["gamma/m", "ghost"]
    edit_reviewers(work, ["gamma/m", "ghost", "beta"], shared=team)
    assert names(status()) == ["gamma/m", "ghost", "beta"]
    for bad, message in ((["gamma/m", "gamma"], "no review section for gamma; valid: alpha, beta, delta"),
                         (["ghost/model-x"], "no review section for ghost; valid: alpha, beta, delta"),
                         (["ghost", "ghost"], "reviewer named twice: ghost")):
        refused(lambda: edit_reviewers(work, bad, shared=team), message)
    refused(lambda: reviewers(["gamma/m", "ghost", "beta"], team), "no review section for gamma; valid: alpha, beta, delta")
    edit_reviewers(work, ["beta"], shared=team)
    refused(lambda: edit_reviewers(work, ["beta", "ghost"], shared=team), "no review section for ghost; valid: alpha, beta, delta")

    # Who each role may pin comes from the adapters: gamma's `## Reviewing` is no review section and delta declares
    # `executor: no` (violating controls: neither an adapter alone nor a heading that only starts alike is a choice).
    # A new adapter is a new choice with no other change.
    for dispatch in (False, True):
        assert status(dispatch=dispatch)["choices"] == {"executor": ["alpha", "beta"],
                                                       "reviewers": ["alpha", "beta", "delta"]}
    (team / "adapters/epsilon.adapter.md").write_text("## Review\n\nepsilon\n", encoding="utf-8")
    assert status()["choices"] == {"executor": ["alpha", "beta", "epsilon"],
                                   "reviewers": ["alpha", "beta", "delta", "epsilon"]}

    # An adapter that cannot be read as text (not UTF-8, or a folder named like one) is no choice and is named on
    # stderr; status and dispatch still return a healthy executor, pinned or not. Violating control: each raises when
    # read, as the first version of `choices` read every adapter. The selected executor's own one is still refused.
    (team / "adapters/broken.adapter.md").write_bytes(b"## Review\n\n\xff\n")
    (team / "adapters/folder.adapter.md").mkdir()
    for raw, engine in ((None, "alpha"), (b'{"executor":"beta"}', "beta")):
        path.unlink(missing_ok=True)
        if raw:
            path.write_bytes(raw)
        for dispatch in (False, True):
            with contextlib.redirect_stderr(io.StringIO()) as err:
                value = status(dispatch=dispatch)
            assert value["executor"]["engine"] == engine and value["choices"] == {
                "executor": ["alpha", "beta", "epsilon"], "reviewers": ["alpha", "beta", "delta", "epsilon"]}, value
            assert err.getvalue().count("\n") == 1 and "broken.adapter.md" in err.getvalue() \
                and "folder.adapter.md" in err.getvalue(), err.getvalue()
    for unreadable in ("broken", "folder"):
        try:
            (team / f"adapters/{unreadable}.adapter.md").read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        raise AssertionError(f"{unreadable} was read")
    with contextlib.redirect_stderr(io.StringIO()):
        for engine, message in (("broken", "invalid start byte"), ("folder", "no adapter for folder; valid: alpha, beta, epsilon")):
            path.write_bytes(json.dumps({"executor": engine}).encode())
            for dispatch in (False, True):
                refused(lambda: status(dispatch=dispatch), message)
        path.unlink()
        refused(lambda: status(host="folder", dispatch=True), "no adapter for folder; valid: alpha, beta, epsilon")
        try:
            status(host="broken", dispatch=True)
        except UnicodeError:
            pass
        else:
            raise AssertionError("an unreadable default executor adapter was dispatched")
    # A skipped path is named as `repr` renders it: one line that encodes as strict UTF-8, the way stderr is set, even
    # when its string holds a lone surrogate (a folder name that is not UTF-8; macOS refuses one, so the string is built
    # here) and a newline. Violating control: the plain path string does not encode.
    odd = Path(f"{work}/odd \udcff\nname/adapters/broken.adapter.md")

    class OddFolder:
        def __truediv__(self, name):
            return self

        def glob(self, pattern):
            return iter([odd])
    with contextlib.redirect_stderr(io.StringIO()) as err:
        assert choices(OddFolder()) == {"executor": [], "reviewers": []}
    assert len(err.getvalue().encode("utf-8").splitlines()) == 1 and "broken.adapter.md" in err.getvalue(), err.getvalue()
    try:
        str(odd).encode("utf-8")
    except UnicodeEncodeError:
        pass
    else:
        raise AssertionError("the plain path string encoded")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--workdir", type=Path, default=Path.cwd())
    parser.add_argument("--default-engine", default="claude")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--select", action="store_true", help="resolve for dispatch: an unavailable pinned executor fails closed")
    action.add_argument("--set-executor", metavar="ENGINE")
    action.add_argument("--clear", action="store_true", help="remove the executor pin and the inactive retired keys")
    action.add_argument("--clear-executor", action="store_true", help="remove the executor pin alone; every other key stays")
    action.add_argument("--set-reviewers", nargs="+", metavar="NAME", help="engine, engine/model or engine/model/effort")
    action.add_argument("--clear-reviewers", action="store_true", help="remove the reviewers; the executor pin stays")
    args = parser.parse_args()
    try:
        if args.self_test:
            return self_test()
        if args.set_executor is not None or args.clear:
            edit(args.workdir, args.set_executor)
        elif args.clear_executor:
            edit(args.workdir, None, retired=False)
        elif args.set_reviewers is not None or args.clear_reviewers:
            edit_reviewers(args.workdir, args.set_reviewers or [])
        value = (select if args.select else resolve)(args.workdir, args.default_engine)
        if args.set_executor and value["executor"]["availability"] == "CLI-unavailable":
            print(f"Pinned {args.set_executor}, which is unavailable here: dispatch stops with "
                  f"BLOCKED:{args.set_executor}-unavailable until it is installed.", file=sys.stderr)
        print(json.dumps(value, sort_keys=True))
        return 0
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("platform-support.py")))["configure_utf8"]()
    raise SystemExit(main())
