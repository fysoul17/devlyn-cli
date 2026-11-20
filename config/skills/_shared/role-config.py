#!/usr/bin/env python3
"""Resolve and pin the devlyn executor and reviewers; no model dispatch."""
from __future__ import annotations

import runpy
import argparse
import contextlib
import decimal
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
ROLES = ("executor", "reviewers")
PARTS = ("model", "effort")


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
    """The file's bytes for `value`. A number JSON cannot hold (`1e400` is read as infinity) refuses the edit: written
    back, it would be a file this reader refuses."""
    try:
        return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    except ValueError as exc:
        fail(f"a value cannot be written back as JSON: {exc}")


def user_file():
    """The user's own file, read under every checkout's: who builds and who reviews in every project. It has its own
    name, so no checkout's `.devlyn/engines.json`, the home folder's included, is ever it. None without a home folder."""
    try:
        return Path.home() / ".devlyn/engine-defaults.json"
    except RuntimeError:
        return None


NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")


def name(value, field):
    if not isinstance(value, str) or not NAME.fullmatch(value):
        fail(f"{field} must be a nonempty identifier")
    return value


INELIGIBLE = re.compile(r"^executor: no\s*$", re.M)
COMMAND = re.compile(r"^command: ([A-Za-z0-9][A-Za-z0-9_.-]*)\s*$", re.M)
REVIEW = re.compile(r"^## Review$", re.M)
INVOCATION = re.compile(r"^## Invocation$", re.M)
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


def section(text, heading):
    """The body of an adapter's section under `heading`, trimmed; None when it has none."""
    start = heading.search(text)
    if start is None:
        return None
    body = text[start.end():]
    end = SECTION.search(body)
    return body[:end.start() if end else len(body)].strip()


def review_start(engine, shared=SHARED):
    """The body of the engine's adapter section `## Review`, trimmed; None when it has none."""
    path = shared / "adapters" / f"{engine}.adapter.md"
    return section(path.read_text(encoding="utf-8"), REVIEW) if path.is_file() else None


def takes(offered, shared=SHARED):
    """Which of a model and an effort each offered engine takes per role: the placeholders its adapter's start has."""
    def parts(engine, heading):
        start = section((shared / "adapters" / f"{engine}.adapter.md").read_text(encoding="utf-8"), heading) or ""
        return [part for part in PARTS if f"<{part}>" in start]
    return {"executor": {engine: parts(engine, INVOCATION) for engine in offered["executor"]},
            "reviewers": {engine: parts(engine, REVIEW) for engine in offered["reviewers"]}}


def refuse_untaken(engine, model, effort, start, what):
    """A model or an effort is accepted only where the start it is pasted into has its placeholder."""
    for part, value, plain in (("model", model, engine), ("effort", effort, f"{engine}/{model}")):
        if value and f"<{part}>" not in start:
            fail(f"{engine}'s {what} takes no {part}; name it {plain}")


def review_command(engine, shared=SHARED):
    """The program the engine's review starts: its adapter's header line `command: <program>`, else the engine's name."""
    text = (shared / "adapters" / f"{engine}.adapter.md").read_text(encoding="utf-8")
    end = SECTION.search(text)
    match = COMMAND.search(text[:end.start() if end else len(text)])
    return match.group(1) if match else engine


def named(entry, what):
    """`engine`, `engine/model` or `engine/model/effort` as [engine, model, effort]. Every part obeys the name rule:
    a session pastes model and effort into a start line, and the file may come from the repository."""
    parts = entry.split("/") if isinstance(entry, str) else []
    if not 1 <= len(parts) <= 3 or not all(NAME.fullmatch(part) for part in parts):
        fail(f"not {what} name: {entry!r}")
    return (parts + ["", ""])[:3]


def reviewer(entry):
    return named(entry, "a reviewer")


def executor_name(entry, shared=SHARED):
    """A name for who builds in every project that this release can start: an engine that may execute, with a model
    or an effort only where its adapter's `## Invocation` has the placeholder."""
    engine, model, effort = named(entry, "an executor")
    refuse_untaken(engine, model, effort, section(adapter(engine, shared=shared), INVOCATION) or "", "invocation")
    return entry


def reviewers(entries, shared=None, kept=()):
    """Unique reviewer names; with `shared`, the engine of each name not in `kept` also needs an adapter with a review
    section, and a model or effort part needs that section's `<model>` or `<effort>` placeholder."""
    if not isinstance(entries, list):
        fail("reviewers must be an array of names")
    seen = set()
    for entry in entries:
        engine, model, effort = reviewer(entry)
        if shared is not None and entry not in kept:
            start = review_start(engine, shared)
            if start is None:
                fail(f"no review section for {engine}; valid: {', '.join(choices(shared)['reviewers'])}")
            refuse_untaken(engine, model, effort, start, "review")
        if entry in seen:
            fail(f"reviewer named twice: {entry}")
        seen.add(entry)
    return entries


def validate(config, shared=SHARED, *, user=False):
    """A checkout's executor is an engine this release may start. The user's file is checked for the shape of its names
    only, so a name another release stored never makes it unreadable: what this release can start is checked when a
    name is new (`executor_name`) and at dispatch (`select`)."""
    if not isinstance(config, dict):
        fail("configuration must be an object")
    if "executor" in config:
        if user:
            named(config["executor"], "an executor")
        else:
            adapter(config["executor"], shared=shared)
    reviewers(config.get("reviewers", []))
    return config


def read_config(path, *, optional=False, shared=SHARED, user=False):
    return read_bytes(path, optional=optional, shared=shared, user=user)[:2]


def read_bytes(path, *, optional=False, shared=SHARED, user=False):
    """`read_config`, and the bytes it read (None for a file that is not there)."""
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
                    return {}, {"path": str(path.absolute()), "sha256": None}, None
                raise
        try:
            raw = path.read_bytes()
        except FileNotFoundError:
            if not optional or os.path.lexists(path):
                raise
            # Removed since the look above (another edit cleared its last key): absent, not unreadable.
            return {}, {"path": str(path.absolute()), "sha256": None}, None
        value = validate(loads(raw), shared=shared, user=user)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"cannot read role configuration {path}: {exc}")
    return value, {"path": str(path.resolve()), "sha256": digest(raw)}, raw


def read_user(shared=SHARED):
    """What the user's own file holds; nothing when it or the home folder is absent. A refusal names the file: it is
    read in every project, and nothing else says which of the two files to repair."""
    path = user_file()
    if path is None:
        return {}
    try:
        return read_config(path, optional=True, shared=shared, user=True)[0]
    except ValueError as exc:
        raise ValueError(str(exc) if str(path) in str(exc) else f"{exc} (in {path})") from None


def resolve(work, default_engine, *, available=None, shared=SHARED):
    """Who builds and who reviews in the checkout at `work`: per role its own pin, else the user's for every project,
    else the invoking CLI and nobody named. An empty list is no list. Status only, never a dispatch decision; no
    reviewer is chosen that the user did not pin."""
    project, source = read_config(Path(work) / ".devlyn/engines.json", optional=True, shared=shared)
    user = read_user(shared)
    available = available or (lambda candidate: shutil.which(candidate) is not None)

    def presence(candidate):
        return "CLI-present/auth-unchecked" if available(candidate) else "CLI-unavailable"

    def pinned(role):
        """Where a role comes from and what is stored for it there."""
        for origin, config in (("engines.json", project), ("user", user)):
            if config.get(role):
                return origin, config[role]
        return "default", None

    def listed(entries):
        rows = []
        for entry in entries:
            part, model, effort = reviewer(entry)
            # A name this release has no review section for is listed, never a failure: another release may have
            # pinned it. So is one whose adapter cannot be read: it starts nothing.
            try:
                start = review_start(part, shared)
            except (OSError, UnicodeError):
                start = None
            rows.append({"name": entry, "engine": part, "model": model, "effort": effort,
                         "availability": "no-review-section" if start is None else presence(review_command(part, shared)),
                         "start": start or ""})
        return rows

    def as_named(row):
        """A reviewer is started as named or not at all: a stored model or effort its start cannot take (a name is
        kept as stored) is never started on whatever model that engine defaults to."""
        if all(f"<{part}>" in row["start"] for part in PARTS if row[part]) or not row["start"]:
            return row
        return {**row, "availability": "unsupported", "start": ""}

    origin, stored = pinned("executor")
    # read_config validates the checkout's pin; the invoking host needs no adapter to report its own default.
    engine, model, effort = named(stored, "an executor") if stored else [name(default_engine, "engine"), "", ""]
    availability = presence(engine)
    if origin == "user":
        try:
            executor_name(stored, shared)
        except (ValueError, OSError):
            availability = "unsupported"
    # The checkout's own list, as releases before the user's file printed it: apps of then show it and write it back.
    own = listed(project.get("reviewers", []))
    review_origin, review_with = ("engines.json", own) if own else ("user", listed(user.get("reviewers", [])))
    offered = choices(shared)
    return {"executor": {"engine": engine, "model": model, "effort": effort, "source": origin, "availability": availability},
            "reviewers": own,
            "review_with": [{**as_named(row), "source": review_origin} for row in review_with],
            "stored": {"project": {role: project[role] for role in ROLES if project.get(role)},
                       "user": {role: user[role] for role in ROLES if user.get(role)}},
            "inactive": [key for key in RETIRED if key in project], "input": source,
            "choices": offered, "takes": takes(offered, shared)}


def select(work, default_engine, *, available=None, shared=SHARED):
    """The executor for dispatch. A pin is a promise: an unavailable pinned engine is never substituted."""
    result = resolve(work, default_engine, available=available, shared=shared)
    executor = result["executor"]
    if executor["source"] == "user":
        executor_name(result["stored"]["user"]["executor"], shared)
    else:
        adapter(executor["engine"], shared=shared)
    if executor["source"] != "default" and executor["availability"] == "CLI-unavailable":
        # The pin to change is the one that holds it: a new one for this project would leave every other blocked.
        everywhere = " for every project" if executor["source"] == "user" else ""
        fail(f"pinned executor {executor['engine']} is unavailable; install and authenticate its CLI, "
             f"verify `{executor['engine']} --version`, and retry, or pin an available engine with "
             f"`devlyn-engines executor <name>`{everywhere}",
             f"{executor['engine']}-unavailable")
    return result


def exact(raw):
    """A file's values with every number as written: its value and its sign, which `-0` and `0` share as values. A
    number that cannot be read so (`0e99999999999999999999`) stands as its own text, equal to nothing written back."""
    def number(text):
        try:
            value = decimal.Decimal(text)
        except decimal.InvalidOperation:
            return ("number", text)
        return (value, value.is_signed())
    return json.loads(raw, parse_float=number, parse_int=number)


def changed(path, change, shared, user):
    """The file's bytes after `change`; None for a file the change leaves empty. Every key the change does not own
    keeps its value exactly: the whole file is written back, and a number this reader rounds (`1e-400`, a long decimal)
    or cannot hold (`1e400`) would otherwise change with an edit of another key."""
    config, _, was = read_bytes(path, optional=True, shared=shared, user=user)
    read = dict(config)
    change(config)
    if not config:
        return None
    try:
        raw = encoded(config)
    except ValueError as exc:
        raise ValueError(f"{exc} (in {path})") from None
    # From the very bytes the values came from: another edit of the file in between changes nothing here.
    before, after = ({} if was is None else exact(was)), exact(raw)
    # The keys the change left alone still hold the very values that were read.
    if any(after[key] != before[key] for key in config if key in read and config[key] is read[key]):
        fail(f"a number in {path} cannot be written back exactly; change that file by hand")
    return raw


@contextlib.contextmanager
def locked(path):
    """Hold the lock file beside the user's own file for the block. It is opened as itself and must be a regular
    file."""
    lock = path.with_name(path.name + ".lock")
    try:
        if lock.is_symlink():
            raise OSError("it is a link")
        handle = os.fdopen(os.open(lock, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600), "r+b")
    except OSError as exc:
        fail(f"cannot lock {lock}: {exc}")
    with handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            fail(f"cannot lock {lock}: it is not a regular file")
        with runpy.run_path(str(SHARED / "platform-support.py"))["handle_lock"](handle, lock, blocking=True):
            yield


def rewrite(work, user, change, shared=SHARED, *, clearing=False):
    """Read, change and replace the checkout's file, or with `user` the user's own. The user's file, which every
    project's sheet and session can edit, is changed under its lock: two edits never lose one another's. A checkout's
    file is replaced as releases before did, with no lock: a lock file there would be a path its repository controls.
    A clear of a file that is not there does nothing and creates nothing."""
    path = user_file() if user else Path(work) / ".devlyn/engines.json"
    if path is None:
        if clearing:
            return
        fail("no home folder to keep the choice for every project in")
    # Tried first without the lock: a file that cannot be read, or a change that is refused, makes no folder and no
    # lock file.
    changed(path, change, shared, user)
    if clearing and not os.path.lexists(path):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with locked(path) if user else contextlib.nullcontext():
        write(path, changed(path, change, shared, user))


def edit(work, executor, shared=SHARED, *, retired=True, user=False):
    """Pin `executor`, or with None clear the executor pin and, with `retired`, the retired keys; other keys keep
    their values. A checkout names an engine alone, which every release reads; the user's file may name its model and
    effort too."""
    def change(config):
        if executor is None:
            for key in ("executor", *(RETIRED if retired else ())):
                config.pop(key, None)
            return
        if user:
            executor_name(executor, shared)
        else:
            if isinstance(executor, str) and "/" in executor and all(map(NAME.fullmatch, executor.split("/"))):
                fail(f"one project names an engine only: {executor!r}; a model is named for every project")
            adapter(executor, shared=shared)
        config["executor"] = executor
    rewrite(work, user, change, shared, clearing=executor is None)


def edit_reviewers(work, entries, shared=SHARED, *, user=False):
    """Pin `entries` as the reviewers, or with none remove them; other keys keep their values. A name already pinned
    exactly as given is kept unasked: another release may have pinned it, and only a new name needs a review section."""
    def change(config):
        if reviewers(entries, shared, kept=config.get("reviewers", [])):
            config["reviewers"] = list(entries)
        else:
            config.pop("reviewers", None)
    rewrite(work, user, change, shared, clearing=not entries)


def clear_roles(work, shared=SHARED, *, user=False):
    """Remove who builds and who reviews in one write; every other key keeps its value."""
    def change(config):
        for role in ROLES:
            config.pop(role, None)
    rewrite(work, user, change, shared, clearing=True)


def write(path, raw):
    if raw is None:
        path.unlink(missing_ok=True)
        return
    fd, temp = tempfile.mkstemp(prefix=f"{path.name}.tmp.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
        if path.exists():
            os.chmod(temp, path.stat().st_mode & 0o777)
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def drain_checkout(packet):
    """The checkout a drained run's drain runs in, as that drain wrote it beside the run's packet at its start. A
    record that is missing or names no folder stops the run: read in any other place, another checkout's pins or the
    user's would pass for this one's."""
    try:
        # The packet as it really lies, and the record's bytes as they are: a line break in a folder's name stays
        # the one it is.
        record = Path(packet).resolve(strict=True).with_name("drain-checkout")
        work = Path(record.read_bytes().decode("utf-8"))
        there = work.is_absolute() and work.is_dir()
    except (OSError, UnicodeError, ValueError) as exc:
        fail(f"the checkout the drain of {packet} runs in cannot be read ({exc}); drain the task again", "no-drain-checkout")
    if not there:
        fail(f"{record} names {str(work)!r}, which is no folder here; drain the task again", "no-drain-checkout")
    return work


@contextlib.contextmanager
def home_at(folder):
    """The home folder for the block and the processes it starts: the user's own file is read and written under it."""
    before = {key: os.environ.get(key) for key in ("HOME", "USERPROFILE")}
    os.environ.update(HOME=str(folder), USERPROFILE=str(folder))
    try:
        yield
    finally:
        for key, value in before.items():
            os.environ.pop(key, None) if value is None else os.environ.update({key: value})


def builds(engine, source, availability="CLI-present/auth-unchecked", model="", effort=""):
    return {"engine": engine, "model": model, "effort": effort, "source": source, "availability": availability}


def self_test():
    with tempfile.TemporaryDirectory() as temp, home_at(Path(temp) / "home"):
        work = Path(temp) / "work"
        (work / ".devlyn").mkdir(parents=True)
        path = work / ".devlyn/engines.json"
        here, absent = (lambda engine: True), (lambda engine: False)
        assert resolve(work, "claude", available=here)["executor"] == builds("claude", "default")
        # An explicit pin binds; retired keys are reported, not validated, and their bytes stay.
        legacy = b'{"executor":"codex","pair_judge_priority":["grok"],"roles":{"worker":{"engine":"unknown"}},"keep":7}\n'
        path.write_bytes(legacy)
        status = resolve(work, "claude", available=here)
        assert status["executor"]["engine"] == "codex" and status["executor"]["source"] == "engines.json", status
        assert status["inactive"] == ["pair_judge_priority", "roles"] and path.read_bytes() == legacy
        # A pin file's status holds what releases before the user's file printed (who builds, the checkout's own
        # reviewers, who each role may pin from the shipped adapters), and beside it who reviews here, what each file
        # stores and which engines take a model or an effort. Violating control: an adapter alone is no choice (omp
        # has one).
        both = ["model", "effort"]
        assert status == {
            "executor": builds("codex", "engines.json"), "reviewers": [], "review_with": [],
            "stored": {"project": {"executor": "codex"}, "user": {}},
            "inactive": ["pair_judge_priority", "roles"], "input": {"path": str(path.resolve()), "sha256": digest(legacy)},
            "choices": {"executor": ["claude", "codex"], "reviewers": ["claude", "codex", "cursor", "grok"]},
            "takes": {"executor": {"claude": both, "codex": both},
                      "reviewers": {"claude": both, "codex": both, "cursor": [], "grok": both}}}, status
        assert select(work, "claude", available=here) == status
        every = sorted(p.name.removesuffix(".adapter.md") for p in (SHARED / "adapters").glob("*.adapter.md"))
        assert every == ["claude", "codex", "cursor", "grok", "omp"] and every not in status["choices"].values(), every
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
            "BLOCKED:invalid-engine-config: no review section for omp; valid: claude, codex, cursor, grok\n"), proc.stderr
        assert path.read_bytes() == b'{"executor":"codex"}'
        # Cursor reviews and takes no model or effort: its new names that carry one are refused, an exact stored one is
        # kept; the three engines whose sections take both still accept them. Violating control: the same names
        # obey the name rule, so only the section's missing placeholder refuses them.
        edit(work, None)
        edit_reviewers(work, ["cursor"])
        assert [(r["name"], r["start"].splitlines()[1]) for r in resolve(work, "claude", available=here)["reviewers"]] == [
            ("cursor", '`cursor-agent -p "<prompt>" --mode ask --sandbox enabled`.')]
        # A pinned reviewer is present when the program its review starts is: cursor's adapter names `cursor-agent`;
        # grok's names none, so grok is checked by its engine's name. Violating control: only the editor's `cursor`.
        edit_reviewers(work, ["cursor", "grok"])
        for present, expected in ((("cursor-agent", "grok"), ["CLI-present/auth-unchecked"] * 2),
                                  (("cursor",), ["CLI-unavailable"] * 2),
                                  (("cursor-agent",), ["CLI-present/auth-unchecked", "CLI-unavailable"])):
            value = resolve(work, "claude", available=lambda candidate: candidate in present)
            assert [r["availability"] for r in value["reviewers"]] == expected, (present, value["reviewers"])
        for bad in ("cursor/some-model", "cursor/some-model/high"):
            assert reviewer(bad)[0] == "cursor"
            path.write_bytes(b'{"reviewers":["cursor"]}')
            try:
                edit_reviewers(work, ["cursor", bad])
            except ValueError as exc:
                assert str(exc) == "BLOCKED:invalid-engine-config: cursor's review takes no model; name it cursor", exc
            else:
                raise AssertionError(f"{bad} was pinned")
            assert loads(path.read_bytes()) == {"reviewers": ["cursor"]}
            path.write_bytes(json.dumps({"reviewers": [bad]}).encode())
            edit_reviewers(work, [bad, "grok"])
            assert loads(path.read_bytes()) == {"reviewers": [bad, "grok"]}
        edit_reviewers(work, ["claude/model-x/high", "codex/model-y/low", "grok/model-z/max"])
        assert [(r["model"], r["effort"]) for r in resolve(work, "claude", available=here)["reviewers"]] == [
            ("model-x", "high"), ("model-y", "low"), ("model-z", "max")]
        path.write_bytes(b'{"executor":"codex"}')
        reviewer_self_test(work, path)
        path.unlink(missing_ok=True)
        user_self_test(work, path)
    print("PASS role-config self-test: executor pin, retired keys inactive, fail-closed selection, atomic validated writes, "
          "pinned reviewers listed as named, never chosen and never blocking, and the user's own file under the checkout's")
    return 0


def reviewer_self_test(work, path):
    """Reviewer pins: existing pins keep working, no engine is chosen for the user, naming, and unavailable reviewers."""
    team = work / "team"
    (team / "adapters").mkdir(parents=True)
    for engine, text in (("alpha", '## Review\n\nalpha "<prompt>"\n'),
                         ("beta", '## Invocation\n\nbeta\n\n## Review\n\n  beta "<prompt>" -m <model> -e <effort>\n\n## Notes\n\nnot it\n'),
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
        assert value["executor"] == builds("beta", "engines.json") and value["reviewers"] == [], value
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
         "availability": "CLI-present/auth-unchecked", "start": 'beta "<prompt>" -m <model> -e <effort>'},
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

    # A new name's model is accepted only when its engine's section has `<model>`, its effort only with `<effort>`;
    # the refusal names the plain form, and a name stored exactly as given is kept. alpha has neither placeholder, zeta
    # only `<model>`, beta both. Violating control: each refused name obeys the name rule.
    (team / "adapters/zeta.adapter.md").write_text('## Review\n\nzeta "<prompt>" -m <model>\ncommand: not-the-header\n',
                                                  encoding="utf-8")
    # The program a review starts is named only on a header line (cursor's names `cursor-agent`); a line in a
    # section never names it, so zeta's review starts `zeta`.
    assert (review_command("cursor"), review_command("zeta", team)) == ("cursor-agent", "zeta")
    path.write_bytes(b'{"reviewers":["alpha/model-x"]}')
    for bad, message in ((["alpha/model-y"], "alpha's review takes no model; name it alpha"),
                         (["alpha/model-y/high"], "alpha's review takes no model; name it alpha"),
                         (["zeta/model-x/high"], "zeta's review takes no effort; name it zeta/model-x")):
        assert all(reviewer(name) for name in bad)
        refused(lambda: edit_reviewers(work, bad, shared=team), message)
    edit_reviewers(work, ["alpha/model-x", "zeta/model-x", "beta/model-x/high"], shared=team)
    assert names(status()) == ["alpha/model-x", "zeta/model-x", "beta/model-x/high"]
    (team / "adapters/zeta.adapter.md").unlink()

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


def user_self_test(work, path):
    """The user's own file under the checkout's: per-role precedence, a model for who builds, what released apps read,
    names another release stored, one-write clears and the lock."""
    team = work / "crew"
    (team / "adapters").mkdir(parents=True)
    for engine, text in (("alpha", '## Invocation\n\nalpha "<prompt>"\n\n## Review\n\nalpha "<prompt>"\n'),
                         ("beta", '## Invocation\n\nbeta "<prompt>" -m <model> -e <effort>\n\n## Review\n\nbeta "<prompt>" -m <model>\n'),
                         ("zeta", '## Invocation\n\nzeta "<prompt>" -m <model>\n'),
                         ("delta", 'executor: no\n\n## Review\n\ndelta "<prompt>"\n')):
        (team / f"adapters/{engine}.adapter.md").write_text(text, encoding="utf-8")
    mine = user_file()
    assert mine == Path(os.environ["HOME"]) / ".devlyn/engine-defaults.json" and work not in mine.parents, mine

    def status(dispatch=False, available=lambda engine: True, host="alpha"):
        return (select if dispatch else resolve)(work, host, available=available, shared=team)

    def put(file, value):
        file.parent.mkdir(parents=True, exist_ok=True)
        file.unlink(missing_ok=True) if value is None else file.write_bytes(value)

    def stored():
        """Each file's bytes and what lies beside it: a refusal changes no byte and makes no folder or lock file."""
        return tuple((file.read_bytes() if file.exists() else None,
                      sorted(entry.name for entry in file.parent.iterdir()) if file.parent.is_dir() else None)
                     for file in (path, mine))

    def refused(action, message, reason="invalid-engine-config"):
        before = stored()
        try:
            action()
        except ValueError as exc:
            assert str(exc).startswith(f"BLOCKED:{reason}:") and message in str(exc), exc
        else:
            raise AssertionError(f"accepted; expected {message!r}")
        assert stored() == before

    def names(rows):
        return [(row["name"], row.get("source")) for row in rows]

    # A checkout file of before acts as before, with the user's file absent, empty or holding other keys.
    put(path, b'{"executor":"beta","reviewers":["alpha"]}')
    for raw in (None, b"{}", b'{"mine":1}'):
        put(mine, raw)
        for dispatch in (False, True):
            value = status(dispatch)
            assert value["executor"] == builds("beta", "engines.json") and names(value["reviewers"]) == [("alpha", None)]
            assert names(value["review_with"]) == [("alpha", "engines.json")]
            assert value["stored"] == {"project": {"executor": "beta", "reviewers": ["alpha"]}, "user": {}}, value

    # Per role, the checkout's own wins and the user's fills what it does not hold. Violating control: the checkout's
    # file replacing the user's whole would drop the user's reviewers here.
    put(path, b'{"executor":"alpha"}')
    put(mine, b'{"executor":"beta/model-x/high","reviewers":["delta","beta/model-y"]}')
    value = status(True)
    assert value["executor"] == builds("alpha", "engines.json")
    assert names(value["review_with"]) == [("delta", "user"), ("beta/model-y", "user")] and value["reviewers"] == []
    assert value["stored"] == {"project": {"executor": "alpha"},
                               "user": {"executor": "beta/model-x/high", "reviewers": ["delta", "beta/model-y"]}}
    put(path, b'{"reviewers":["alpha"]}')
    value = status(True)
    assert value["executor"] == builds("beta", "user", model="model-x", effort="high")
    # Who reviews here is the checkout's own row whole, with where it comes from.
    row = {"name": "alpha", "engine": "alpha", "model": "", "effort": "", "availability": "CLI-present/auth-unchecked",
           "start": 'alpha "<prompt>"'}
    assert value["reviewers"] == [row] and value["review_with"] == [{**row, "source": "engines.json"}], value
    # A reviewer is started as named or not at all. A stored name is kept as stored, so it may carry a model its
    # engine's review cannot take (alpha takes none, beta no effort): who reviews here then has no start for it,
    # while the checkout's own list reads as releases before printed it. Violating control: with the start left in,
    # a session would run that engine's default model and count it as the reviewer named.
    put(path, b'{"reviewers":["alpha/model-x","beta/model-y/high","beta/model-y"]}')
    value = status(True)
    assert [(r["name"], r["availability"], bool(r["start"])) for r in value["review_with"]] == [
        ("alpha/model-x", "unsupported", False), ("beta/model-y/high", "unsupported", False),
        ("beta/model-y", "CLI-present/auth-unchecked", True)], value["review_with"]
    assert all(r["start"] and r["availability"] == "CLI-present/auth-unchecked" for r in value["reviewers"])
    # A pinned reviewer whose adapter cannot be read starts nothing and fails nothing: clearing the checkout's own
    # reviewers, which hid it, is a save that succeeds.
    (team / "adapters/torn.adapter.md").write_bytes(b"## Review\n\n\xff\n")
    put(mine, b'{"reviewers":["torn"]}')
    with contextlib.redirect_stderr(io.StringIO()):
        assert names(status()["review_with"])[0] == ("alpha/model-x", "engines.json")
        edit_reviewers(work, [], shared=team)
        assert [(r["name"], r["availability"], r["start"]) for r in status(True)["review_with"]] == [("torn", "no-review-section", "")]
    (team / "adapters/torn.adapter.md").unlink()
    put(mine, b'{"executor":"beta/model-x/high","reviewers":["delta","beta/model-y"]}')
    # An empty list is no list, in either file: a checkout cannot say "nobody here". Violating control: the key's
    # presence alone would hide the user's reviewers.
    put(path, b'{"reviewers":[]}')
    value = status()
    assert names(value["review_with"]) == [("delta", "user"), ("beta/model-y", "user")] and value["stored"]["project"] == {}
    put(mine, b'{"reviewers":[]}')
    value = status(True)
    assert value["executor"] == builds("alpha", "default") and value["review_with"] == [] and value["stored"]["user"] == {}

    # Each write lands in its own file alone; other keys keep their values.
    put(path, b'{"keep":7,"executor":"alpha"}')
    put(mine, b'{"mine":1}')
    edit(work, "beta/model-x/high", shared=team, user=True)
    edit_reviewers(work, ["delta"], shared=team, user=True)
    assert loads(mine.read_bytes()) == {"mine": 1, "executor": "beta/model-x/high", "reviewers": ["delta"]}
    assert path.read_bytes() == b'{"keep":7,"executor":"alpha"}'
    edit_reviewers(work, ["alpha"], shared=team)
    assert loads(path.read_bytes()) == {"keep": 7, "executor": "alpha", "reviewers": ["alpha"]}
    assert loads(mine.read_bytes())["reviewers"] == ["delta"]
    edit(work, None, shared=team, retired=False, user=True)
    edit_reviewers(work, [], shared=team, user=True)
    assert loads(mine.read_bytes()) == {"mine": 1}
    # The whole file is written back, so a number of another key that this reader cannot hold or would round
    # refuses the edit before any byte changes; every number it keeps exactly passes. Violating controls: `1e400`
    # written back as `Infinity` is a file this reader refuses; `1e-400` would become `0.0`.
    for number, message in ((b"1e400", "cannot be written back as JSON"), (b"1e-400", "cannot be written back exactly"),
                            (b"0.1234567890123456789012", "cannot be written back exactly"),
                            (b"[1, {\"deep\": 123456789.123456789123}]", "cannot be written back exactly")):
        put(path, b'{"executor":"alpha","extra":' + number + b'}')
        refused(lambda: edit_reviewers(work, ["alpha"], shared=team), message)
        refused(lambda: edit(work, None, shared=team), message)
    assert json.dumps(json.loads(b"1e-400")) == "0.0"
    # A key of an earlier release is another key too, unless the edit is the one that removes it: then also a
    # number that cannot even be read exactly goes with it, and the keys that stay keep their values.
    put(path, b'{"executor":"alpha","roles":{"worker":1e-400}}')
    refused(lambda: edit(work, "beta", shared=team), "cannot be written back exactly")
    refused(lambda: edit(work, None, shared=team, retired=False), "cannot be written back exactly")
    edit(work, None, shared=team)
    assert not path.exists()
    put(path, b'{"roles":0e99999999999999999999,"reviewers":["alpha"],"mine":1.50}')
    refused(lambda: edit_reviewers(work, ["delta"], shared=team), "cannot be written back exactly")
    edit(work, None, shared=team)
    assert loads(path.read_bytes()) == {"reviewers": ["alpha"], "mine": 1.5}
    # A zero keeps its sign: `-0` written back as `0` is another value to a reader that tells them apart.
    put(path, b'{"executor":"alpha","extra":-0}')
    refused(lambda: edit_reviewers(work, ["alpha"], shared=team), "cannot be written back exactly")
    kept = b'{"executor":"alpha","extra":[7, 1.50, 1e3, -0.0, 123456789012345678901234567890, 0.30000000000000004, "1e-400"]}'
    put(path, kept)
    edit_reviewers(work, ["alpha"], shared=team)
    assert exact(path.read_bytes())["extra"] == exact(kept)["extra"] and loads(path.read_bytes())["reviewers"] == ["alpha"]
    put(path, b'{"executor":"alpha","extra":1e400}')
    try:
        loads(json.dumps(loads(path.read_bytes())).encode())
    except ValueError as exc:
        assert "invalid JSON constant" in str(exc), exc
    else:
        raise AssertionError("Infinity was read back")

    # Who builds: one project names an engine alone, which every release reads; the user's file takes a model and an
    # effort where the adapter's invocation has the placeholder. Refused names leave both files as they were.
    put(path, b'{"executor":"alpha"}')
    put(mine, b'{"executor":"beta"}')
    refused(lambda: edit(work, "beta/model-x", shared=team), "one project names an engine only: 'beta/model-x'")
    refused(lambda: edit(work, "../beta", shared=team), "nonempty identifier")
    for bad, message in (("alpha/model-x", "alpha's invocation takes no model; name it alpha"),
                         ("zeta/model-x/high", "zeta's invocation takes no effort; name it zeta/model-x"),
                         ("delta", "delta is ineligible as executor"), ("nobody", "no adapter for nobody; valid: alpha, beta, zeta"),
                         ('beta/x";touch y;"', "not an executor name"), ("beta/a/b/c", "not an executor name")):
        refused(lambda: edit(work, bad, shared=team, user=True), message)
    for good in ("beta/model-4.7_x/ultra", "zeta/model-x", "alpha"):
        edit(work, good, shared=team, user=True)
        assert loads(mine.read_bytes()) == {"executor": good}
    # Shell text never reaches a start line from the user's file either, and a refusal of that file names it: it is
    # read in every project. It is read whole even where the checkout holds both roles: its choice is what every
    # project's sheet shows.
    put(path, None)
    for bad in ("beta/$(id)", "beta/model/`id`", "beta/m odel"):
        put(mine, json.dumps({"executor": bad}).encode())
        for dispatch in (False, True):
            refused(lambda: status(dispatch), f"not an executor name: {bad!r} (in {mine})")
    put(path, b'{"executor":"alpha","reviewers":["alpha"]}')
    for raw, message in ((b'{"reviewers":["delta/$(id)"]}', f"(in {mine})"), (b"", str(mine)), (b"{", str(mine))):
        put(mine, raw)
        for dispatch in (False, True):
            refused(lambda: status(dispatch), message)
    put(path, None)

    # A name another release stored in the user's file never makes it unreadable: status shows it, dispatch blocks
    # with the reason, a checkout's own pin still builds, and a new choice replaces it. Violating control: read as a
    # checkout's file is, the same bytes refuse every read.
    put(mine, b'{"executor":"ghost/m","reviewers":["phantom"]}')
    value = status()
    assert value["executor"] == builds("ghost", "user", "unsupported", model="m")
    assert [(row["name"], row["availability"]) for row in value["review_with"]] == [("phantom", "no-review-section")]
    refused(lambda: status(True), "no adapter for ghost; valid: alpha, beta, zeta")
    refused(lambda: read_config(mine, shared=team), "nonempty identifier")
    put(path, b'{"executor":"alpha"}')
    assert status(True)["executor"] == builds("alpha", "engines.json")
    put(path, None)
    edit(work, "beta", shared=team, user=True)
    assert status(True)["executor"] == builds("beta", "user")
    # A pin is a promise from either file; the invoking CLI is never blocked.
    refused(lambda: status(True, available=lambda engine: engine == "alpha"),
            "pin an available engine with `devlyn-engines executor <name>` for every project", "beta-unavailable")
    # So is a name written by hand that its engine cannot be started with: alpha can execute, but takes no model.
    # Violating control: checked as an engine alone, it would be dispatched without the model it names.
    put(mine, b'{"executor":"alpha/model-x"}')
    assert status()["executor"] == builds("alpha", "user", "unsupported", model="model-x")
    refused(lambda: status(True), "alpha's invocation takes no model; name it alpha")
    assert adapter("alpha", shared=team)
    put(mine, None)
    assert status(True, available=lambda engine: False)["executor"] == builds("alpha", "default", "CLI-unavailable")

    # An app released before the user's file reads `executor` (stored when its source is the checkout's) and
    # `reviewers` as the checkout's own, and writes the whole list back into the checkout. Its next click never copies
    # the user's reviewers there. Violating control: handed who reviews here, it would.
    put(mine, b'{"executor":"beta","reviewers":["alpha"]}')
    value = status()
    shown = (value["executor"]["engine"] if value["executor"]["source"] == "engines.json" else None,
             [row["name"] for row in value["reviewers"]])
    assert shown == (None, []) and names(value["review_with"]) == [("alpha", "user")]
    edit_reviewers(work, [*shown[1], "delta"], shared=team)
    assert loads(path.read_bytes()) == {"reviewers": ["delta"]} != {"reviewers": [row["name"] for row in value["review_with"]] + ["delta"]}
    assert names(status()["review_with"]) == [("delta", "engines.json")] and loads(mine.read_bytes())["reviewers"] == ["alpha"]

    # One write removes who builds and who reviews and keeps every other key; a file left empty is deleted. A clear
    # of a file that is not there creates nothing. Violating control: two clears, one a role, are two writes, and
    # the second can fail after the first.
    put(path, b'{"executor":"beta","reviewers":["alpha"],"roles":{"judge":"x"},"mine":1}')
    writes, real = [], write
    globals()["write"] = lambda file, raw: (writes.append(raw), real(file, raw))[1]
    try:
        clear_roles(work, shared=team)
        assert len(writes) == 1 and loads(path.read_bytes()) == {"roles": {"judge": "x"}, "mine": 1}
        put(path, b'{"executor":"beta","reviewers":["alpha"],"mine":1}')
        edit(work, None, shared=team, retired=False)
        edit_reviewers(work, [], shared=team)
        assert len(writes) == 3
    finally:
        globals()["write"] = real
    put(path, b'{"executor":"beta","reviewers":["alpha"]}')
    clear_roles(work, shared=team)
    assert not path.exists()
    fresh = work / "fresh"
    fresh.mkdir()
    clear_roles(fresh, shared=team)
    edit(fresh, None, shared=team)
    edit_reviewers(fresh, [], shared=team)
    assert list(fresh.iterdir()) == []
    # A checkout's file is replaced with no lock file beside it: that path is its repository's, which could ship a
    # link there to any file of the user's. Violating control: opened as a lock is, such a link creates its target.
    put(mine, None)
    planted = path.with_name("engines.json.lock")
    planted.unlink(missing_ok=True)
    put(path, b'{"executor":"alpha"}')
    edit_reviewers(work, ["alpha"], shared=team)
    assert sorted(entry.name for entry in path.parent.iterdir()) == ["engines.json"]
    if os.name != "nt":
        planted.symlink_to(mine)
        edit_reviewers(work, ["alpha", "delta"], shared=team)
        assert loads(path.read_bytes())["reviewers"] == ["alpha", "delta"] and not mine.exists() and planted.is_symlink()
        with open(planted, "a+b"):
            assert mine.exists()
        mine.unlink()
        planted.unlink()

    # The user's own file is changed under a lock file beside it, opened as itself: a link or a folder in its place
    # refuses the edit, and nothing is made through it. A change that is refused makes no lock file at all, also one
    # refused only when its result is written back (a number that cannot be kept).
    own_lock = mine.with_name(mine.name + ".lock")
    for number in (b"1e400", b"1e-400", b"0e99999999999999999999"):
        own_lock.unlink(missing_ok=True)
        put(mine, b'{"extra":' + number + b'}')
        for action in (lambda: edit(work, "alpha", shared=team, user=True), lambda: edit_reviewers(work, ["alpha"], shared=team, user=True)):
            refused(action, f"cannot be written back")
            assert [entry.name for entry in mine.parent.iterdir()] == ["engine-defaults.json"]
    # Such a refusal of the user's file names it, like every other.
    put(mine, b'{"extra":1e400}')
    refused(lambda: edit(work, "alpha", shared=team, user=True), f"(in {mine})")
    put(mine, b'{"executor":"alpha"}')
    elsewhere = work / "elsewhere.json"
    if os.name != "nt":
        own_lock.symlink_to(elsewhere)
        refused(lambda: edit_reviewers(work, ["alpha"], shared=team, user=True), f"cannot lock {own_lock}: it is a link")
        assert not elsewhere.exists()
        own_lock.unlink()
    own_lock.mkdir()
    refused(lambda: edit_reviewers(work, ["alpha"], shared=team, user=True), f"cannot lock {own_lock}:")
    own_lock.rmdir()
    # A write that fails under the lock is reported as what it is, not as the lock's.
    def full(file, raw):
        raise OSError(28, "No space left on device")
    real, globals()["write"] = write, full
    try:
        edit_reviewers(work, ["alpha"], shared=team, user=True)
    except OSError as exc:
        assert not isinstance(exc, ValueError) and exc.errno == 28, exc
    else:
        raise AssertionError("a failed write was not reported")
    finally:
        globals()["write"] = real
    assert loads(mine.read_bytes()) == {"executor": "alpha"}
    put(mine, None)
    put(path, b'{"executor":"alpha"}')

    # A file removed between the look and the read (another edit cleared its last key) is absent, not unreadable;
    # one that must be there still is refused.
    ghost, look = fresh / "engines.json", Path.lstat
    Path.lstat = lambda self, *args, **kwargs: look(fresh if self == ghost else self, *args, **kwargs)
    try:
        assert read_config(ghost, optional=True, shared=team) == ({}, {"path": str(ghost.absolute()), "sha256": None})
        refused(lambda: read_config(ghost, shared=team), "cannot read role configuration")
    finally:
        Path.lstat = look

    # With no home folder there is no choice for every project: a checkout resolves as before, a clear of it has
    # nothing to do, and a new choice is refused.
    def nowhere():
        raise RuntimeError("no home")
    home, Path.home = Path.home, staticmethod(nowhere)
    try:
        put(path, b'{"executor":"alpha"}')
        assert status(True)["stored"] == {"project": {"executor": "alpha"}, "user": {}}
        clear_roles(work, shared=team, user=True)
        refused(lambda: edit(work, "beta", shared=team, user=True), "no home folder")
    finally:
        Path.home = home

    # Which engines take a model or an effort for each role comes from the placeholders of their adapters' starts.
    assert status()["takes"] == {"executor": {"alpha": [], "beta": ["model", "effort"], "zeta": ["model"]},
                                 "reviewers": {"alpha": [], "beta": ["model"], "delta": []}}

    # The command: `--user` goes with a change and writes the user's file alone; both files are read and checked
    # before any byte changes; an edit waits for the file's lock, so two edits never lose one another's.
    def run(*args, code=0):
        proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--workdir", str(work), *args],
                              capture_output=True, text=True, encoding="utf-8")
        assert proc.returncode == code, (args, proc.returncode, proc.stderr)
        return loads(proc.stdout.encode()) if code == 0 else proc.stderr

    put(path, None)
    put(mine, None)
    value = run("--user", "--set-executor", "codex/model-x/high")
    assert value["executor"]["source"] == "user" and (value["executor"]["model"], value["executor"]["effort"]) == ("model-x", "high")
    assert loads(mine.read_bytes()) == {"executor": "codex/model-x/high"} and not path.exists()
    assert "one project names an engine only" in run("--set-executor", "codex/model-x", code=1)
    assert "--user goes with a change" in run("--user", code=2)
    run("--set-executor", "codex")
    run("--set-reviewers", "grok")
    assert run("--clear-roles")["stored"] == {"project": {}, "user": {"executor": "codex/model-x/high"}} and not path.exists()
    put(mine, b'{"executor":"codex/$(id)"}')
    put(path, b'{"executor":"codex"}')
    before = stored()
    assert "not an executor name" in run("--set-reviewers", "grok", code=1) and stored() == before
    # A drained run works in its task's own worktree, which holds no pin. Its drain writes the checkout it runs in
    # beside the run's packet, and a status or a dispatch asked with that packet reads what is pinned there.
    # Violating control: read in the worktree, the user's reviewers would pass for the checkout's own.
    put(mine, b'{"reviewers":["grok"]}')
    put(path, b'{"executor":"codex","reviewers":["claude"]}')
    task = work / "task worktree {packet}"
    packet = work / "run {packet}" / "packet.json"
    task.mkdir(), packet.parent.mkdir()
    packet.write_bytes(b"{}")
    record = packet.with_name("drain-checkout")
    def asked(*args, code=0):
        proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--workdir", str(task), *args],
                              capture_output=True, text=True, encoding="utf-8")
        assert proc.returncode == code, (proc.returncode, proc.stderr)
        return loads(proc.stdout.encode()) if code == 0 else proc.stderr
    record.write_text(str(work), encoding="utf-8")
    for args in ((), ("--select",)):
        value = asked("--packet", str(packet), *args)
        assert (value["executor"]["engine"], value["executor"]["source"]) == ("codex", "engines.json"), value
        assert names(value["review_with"]) == [("claude", "engines.json")] and value["input"]["path"] == str(path.resolve())
    # Without the packet the answer is the folder that was asked for, whatever a run's surroundings say.
    assert names(asked()["review_with"]) == [("grok", "user")]
    # A record that is not there, or names a folder that is not there (removed since), stops the run: it never
    # falls to another place's pins.
    for text in (str(work / "gone"), "relative", str(work) + "\0", "/" + "x" * 5000, None):
        record.unlink() if text is None else record.write_bytes(text.encode("utf-8"))
        for args in ((), ("--select",)):
            assert asked("--packet", str(packet), *args, code=1).startswith("BLOCKED:no-drain-checkout: "), text
    # So does a packet that is not there: the record beside a name that names no packet answers nothing.
    record.write_bytes(str(work).encode("utf-8"))
    assert asked("--packet", str(packet.with_name("absent.json")), code=1).startswith("BLOCKED:no-drain-checkout: ")
    # The record is read byte for byte: a folder named with a carriage return is not the one named with a line feed.
    if os.name != "nt":
        for name, reviewer in (("team\rblue", "codex"), ("team\nblue", "grok")):
            put(work / name / ".devlyn/engines.json", json.dumps({"reviewers": [reviewer]}).encode("utf-8"))
        record.write_bytes(str(work / "team\rblue").encode("utf-8"))
        assert names(asked("--packet", str(packet))["review_with"]) == [("codex", "engines.json")]
    # It reads; a change is made in the folder it names.
    assert "--packet reads" in asked("--packet", str(packet), "--set-reviewers", "codex", code=2)
    assert not (task / ".devlyn").exists() and loads(path.read_bytes())["reviewers"] == ["claude"]
    put(mine, b'{"executor":"claude"}')
    lock = runpy.run_path(str(SHARED / "platform-support.py"))["file_lock"]
    with lock(mine.with_name(mine.name + ".lock"), blocking=True):
        waiting = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--workdir", str(work), "--user",
                                    "--set-reviewers", "grok"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            waiting.wait(timeout=1.5)
        except subprocess.TimeoutExpired:
            pass
        else:
            raise AssertionError("an edit did not wait for the file's lock")
        mine.write_bytes(b'{"executor":"codex"}')
    assert waiting.wait(timeout=120) == 0 and loads(mine.read_bytes()) == {"executor": "codex", "reviewers": ["grok"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--workdir", type=Path, default=Path.cwd())
    parser.add_argument("--default-engine", default="claude")
    parser.add_argument("--packet", type=Path, metavar="PACKET",
                        help="a drained run's packet, in place of --workdir: read the pins of the checkout its drain runs in")
    parser.add_argument("--user", action="store_true",
                        help="with a change: edit the user's own file, read under every checkout's (the choice for every project)")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--select", action="store_true", help="resolve for dispatch: an unavailable pinned executor fails closed")
    action.add_argument("--set-executor", metavar="NAME", help="an engine; with --user also engine/model or engine/model/effort")
    action.add_argument("--clear", action="store_true", help="remove the executor pin and the inactive retired keys")
    action.add_argument("--clear-executor", action="store_true", help="remove the executor pin alone; every other key stays")
    action.add_argument("--set-reviewers", nargs="+", metavar="NAME", help="engine, engine/model or engine/model/effort")
    action.add_argument("--clear-reviewers", action="store_true", help="remove the reviewers; the executor pin stays")
    action.add_argument("--clear-roles", action="store_true", help="remove the executor pin and the reviewers in one write")
    args = parser.parse_args()
    changes = (args.set_executor is not None, args.clear, args.clear_executor, args.set_reviewers is not None,
               args.clear_reviewers, args.clear_roles)
    if args.user and not any(changes):
        parser.error("--user goes with a change")
    if args.packet is not None and any(changes):
        parser.error("--packet reads; a change names its --workdir")
    try:
        if args.self_test:
            return self_test()
        if any(changes):
            # Both files are read and checked before any byte changes: a save is never reported as refused afterwards.
            resolve(args.workdir, args.default_engine)
        if args.set_executor is not None or args.clear:
            edit(args.workdir, args.set_executor, user=args.user)
        elif args.clear_executor:
            edit(args.workdir, None, retired=False, user=args.user)
        elif args.set_reviewers is not None or args.clear_reviewers:
            edit_reviewers(args.workdir, args.set_reviewers or [], user=args.user)
        elif args.clear_roles:
            clear_roles(args.workdir, user=args.user)
        # A drained run works in its task's own worktree, which holds no pin: what applies to it is pinned for the
        # checkout its drain runs in, and the run asks with its packet.
        work = args.workdir if args.packet is None else drain_checkout(args.packet)
        value = (select if args.select else resolve)(work, args.default_engine)
        engine = named(args.set_executor, "an executor")[0] if args.set_executor else None
        if engine and shutil.which(engine) is None:
            print(f"Pinned {args.set_executor}, which is unavailable here: where this pin applies, dispatch stops with "
                  f"BLOCKED:{engine}-unavailable until it is installed.", file=sys.stderr)
        print(json.dumps(value, sort_keys=True))
        return 0
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("platform-support.py")))["configure_utf8"]()
    raise SystemExit(main())
