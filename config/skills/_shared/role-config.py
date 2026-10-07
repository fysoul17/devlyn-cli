#!/usr/bin/env python3
"""Resolve and pin the devlyn executor; no model dispatch."""
from __future__ import annotations

import runpy
import argparse
import hashlib
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


def name(value, field):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value):
        fail(f"{field} must be a nonempty identifier")
    return value


def adapter(engine, shared=SHARED):
    name(engine, "engine")
    path = shared / "adapters" / f"{engine}.md"
    if not path.is_file():
        fail(f"no adapter for {engine}; valid: {', '.join(sorted(p.stem for p in (shared / 'adapters').glob('*.md')))}")
    text = path.read_text(encoding="utf-8")
    if re.search(r"^executor: no\s*$", text, re.M):
        fail(f"{engine} is ineligible as executor")
    return text


def validate(config, shared=SHARED):
    if not isinstance(config, dict):
        fail("configuration must be an object")
    if "executor" in config:
        adapter(config["executor"], shared=shared)
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
    """The project's executor pin, else the invoking CLI; status only, never a dispatch decision."""
    config, source = read_config(Path(work) / ".devlyn/engines.json", optional=True, shared=shared)
    engine = config.get("executor", default_engine)
    adapter(engine, shared=shared)
    available = available or (lambda candidate: shutil.which(candidate) is not None)
    return {"executor": {"engine": engine, "source": "engines.json" if "executor" in config else "default",
                         "availability": "CLI-present/auth-unchecked" if available(engine) else "CLI-unavailable"},
            "inactive": [key for key in RETIRED if key in config], "input": source}


def select(work, default_engine, *, available=None, shared=SHARED):
    """The executor for dispatch. A pin is a promise: an unavailable pinned engine is never substituted."""
    result = resolve(work, default_engine, available=available, shared=shared)
    executor = result["executor"]
    if executor["source"] == "engines.json" and executor["availability"] == "CLI-unavailable":
        fail(f"pinned executor {executor['engine']} is unavailable; install and authenticate its CLI, "
             f"verify `{executor['engine']} --version`, and retry, or pin an available engine with `devlyn-engines executor <name>`",
             f"{executor['engine']}-unavailable")
    return result


def edit(work, executor, shared=SHARED):
    """Pin `executor`, or with None clear devlyn's pins; unrelated keys keep their values."""
    path = Path(work) / ".devlyn/engines.json"
    config, _ = read_config(path, optional=True, shared=shared)
    if executor is None:
        for key in ("executor", *RETIRED):
            config.pop(key, None)
    else:
        adapter(executor, shared=shared)
        config["executor"] = executor
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
        (ineligible / "adapters/judge.md").write_text("## Role eligibility\n\nexecutor: no\n", encoding="utf-8")
        (ineligible / "adapters/codex.md").write_text("# Codex adapter\n", encoding="utf-8")
        path.write_bytes(legacy)
        for engine, shared, message in (("grok", SHARED, "no adapter for grok"), ("judge", ineligible, "ineligible as executor"),
                                        ("../codex", SHARED, "nonempty identifier")):
            try:
                edit(work, engine, shared=shared)
            except ValueError as exc:
                assert "BLOCKED:invalid-engine-config" in str(exc) and message in str(exc), exc
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
    print("PASS role-config self-test: executor pin, retired keys inactive, fail-closed selection and atomic validated writes")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--workdir", type=Path, default=Path.cwd())
    parser.add_argument("--default-engine", default="claude")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--select", action="store_true", help="resolve for dispatch: an unavailable pinned executor fails closed")
    action.add_argument("--set-executor", metavar="ENGINE")
    action.add_argument("--clear", action="store_true", help="remove the executor pin and the inactive retired keys")
    args = parser.parse_args()
    try:
        if args.self_test:
            return self_test()
        if args.set_executor is not None or args.clear:
            edit(args.workdir, args.set_executor)
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
