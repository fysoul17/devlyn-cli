#!/usr/bin/env python3
"""Resolve explicit devlyn roles; no model dispatch or lifecycle changes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROLES = ("worker", "primary_judge", "pair_judge")
SHARED = Path(__file__).resolve().parent


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


def adapter(engine, judge=False, shared=SHARED):
    name(engine, "engine")
    path = shared / "adapters" / f"{engine}.md"
    if not path.is_file():
        fail(f"no adapter for {engine}")
    text = path.read_text()
    field = "pair_judge" if judge else "executor"
    if re.search(rf"^{field}: no\s*$", text, re.M):
        fail(f"{engine} is ineligible for {'judge' if judge else 'worker'}")
    return text


def validate(config, *, run=False, shared=SHARED):
    if not isinstance(config, dict) or (run and set(config) != {"roles"}):
        fail("configuration must be an object; --role-config accepts only roles")
    if "executor" in config:
        adapter(config["executor"], shared=shared)
    if "pair_judge_priority" in config:
        priority = config["pair_judge_priority"]
        if not isinstance(priority, list):
            fail("pair_judge_priority must be an array")
        for engine in priority:
            adapter(engine, judge=True, shared=shared)
    roles = config.get("roles", {})
    if not isinstance(roles, dict) or set(roles) - set(ROLES):
        fail("roles must contain only worker, primary_judge, pair_judge")
    for role, entry in roles.items():
        if not isinstance(entry, dict) or set(entry) - {"engine", "model", "effort"} or "engine" not in entry:
            fail(f"{role} requires engine and accepts only model/effort")
        adapter(entry["engine"], judge=role != "worker", shared=shared)
        for field in ("model", "effort"):
            if field in entry:
                if not isinstance(entry[field], str) or not entry[field].strip() or entry[field] != entry[field].strip() or "\x00" in entry[field]:
                    fail(f"{role}.{field} must be a nonempty exact string")
        if "model" in entry and entry["model"] in {"default", "auto", "opus", "sonnet", "fable", "codex"}:
            fail(f"{role}.model requires an exact model ID, not an alias")
    return config


def read_config(path, *, run=False, optional=False, shared=SHARED):
    path = Path(path)
    if optional and not path.exists():
        return {}, {"path": str(path.absolute()), "sha256": None}
    try:
        raw = path.read_bytes()
        value = validate(loads(raw), run=run, shared=shared)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"cannot read role configuration {path}: {exc}")
    return value, {"path": str(path.resolve()), "sha256": digest(raw)}


def channel(engine, role, explicit=False):
    if engine == "codex":
        return "codex-monitored" if role == "worker" else "codex-monitored-isolated"
    if engine == "claude":
        if role == "worker":
            return "native-Agent"
        return "claude-CLI" if explicit or role == "pair_judge" else "inherited/adapter-defined"
    return "adapter"


def validate_channel(entry, role):
    fields = [field for field in ("model_requested", "effort_requested") if entry.get(field) is not None]
    engine = entry["engine"]
    if fields and (engine not in {"codex", "claude"} or (engine == "claude" and role == "worker")):
        fail(f"{role}/{engine}: unsupported explicit {', '.join(fields)}; use a supported Codex role, Claude CLI judge, or engine-only native worker",
             "unsupported-role-option")


def resolve(work, default_engine, *, flag_engine=None, run_input=None, no_pair=False,
            available=None, shared=SHARED, proposed=None, for_status=False):
    project, source = (read_config(Path(work) / ".devlyn/engines.json", optional=True, shared=shared)
                       if proposed is None else (validate(proposed, shared=shared), {}))
    run_config = validate(run_input["value"], run=True, shared=shared) if run_input else {}
    legacy = flag_engine or project.get("executor", default_engine)
    adapter(legacy, shared=shared)
    legacy_source = "flag" if flag_engine else "engines.json" if "executor" in project else "default"
    inputs = [source] + ([{k: run_input[k] for k in ("path", "sha256")}] if run_input else [])
    available = available or (lambda engine: shutil.which(engine) is not None)
    selected = {}
    for role in ROLES:
        if role in run_config.get("roles", {}):
            entry, origin = run_config["roles"][role], "role-config"
        elif flag_engine and role != "pair_judge":
            entry, origin = {"engine": flag_engine}, "flag"
        elif role in project.get("roles", {}):
            entry, origin = project["roles"][role], "engines.json.roles"
        elif role != "pair_judge":
            entry, origin = {"engine": legacy}, legacy_source
        else:
            continue
        selected[role] = {"engine": entry["engine"], "model_requested": entry.get("model"),
                          "effort_requested": entry.get("effort"), "source": origin,
                          "channel": channel(entry["engine"], role, any(field in entry for field in ("model", "effort")))}
        if role != "pair_judge" or not no_pair:
            validate_channel(selected[role], role)
    primary = selected["primary_judge"]["engine"]
    adapter(primary, judge=True, shared=shared)
    if not no_pair and "pair_judge" in selected and selected["pair_judge"]["engine"] == primary:
        fail("explicit pair_judge must be a different engine from primary_judge")
    if "pair_judge" not in selected:
        choices = project.get("pair_judge_priority", ["codex" if primary == "claude" else "claude"])
        other = next((engine for engine in choices if engine != primary and available(engine)), None)
        if other:
            adapter(other, judge=True, shared=shared)
        elif not no_pair and "pair_judge_priority" in project:
            candidates = [engine for engine in choices if engine != primary]
            if not candidates:
                fail("pair_judge_priority contains no OTHER engine")
            if not for_status:
                fail(f"pinned OTHER engines unavailable: {', '.join(candidates)}; install/authenticate an engine or explicitly use --no-pair", candidates[0] + "-unavailable")
        selected["pair_judge"] = {"engine": other, "model_requested": None, "effort_requested": None,
                                  "source": "engines.json" if "pair_judge_priority" in project else "default",
                                  "channel": channel(other, "pair_judge") if other else None}
        if for_status:
            selected["pair_judge"]["priority_requested"] = choices
    selected["pair_judge"]["skipped_reason"] = "user_no_pair" if no_pair else (
        "auto_pair_other_engine_unavailable" if selected["pair_judge"]["engine"] is None and "pair_judge_priority" not in project else None)
    if for_status:
        for role, entry in selected.items():
            entry["availability"] = ("unused" if role == "pair_judge" and no_pair else
                                     "unresolved/no-available-engine" if entry["engine"] is None else
                                     "CLI-present/auth-unchecked" if available(entry["engine"]) else "CLI-unavailable")
    result = {"roles": selected, "legacy_engine": legacy, "legacy_source": legacy_source, "inputs": inputs}
    return {**result, "sha256": digest(encoded(result))}


def snapshot(state):
    if not isinstance(state, dict):
        fail("state must be an object")
    if "role_resolution" not in state:
        return None
    value = state["role_resolution"]
    if not isinstance(value, dict) or value.get("sha256") != digest(encoded({k: v for k, v in value.items() if k != "sha256"})):
        fail("frozen role resolution is malformed or altered")
    if not isinstance(value.get("roles"), dict) or set(value["roles"]) != set(ROLES):
        fail("frozen role resolution has missing roles")
    for role, entry in value["roles"].items():
        if not isinstance(entry, dict):
            fail(f"frozen {role} is malformed")
        if role != "pair_judge" or entry.get("engine") is not None:
            name(entry.get("engine"), f"frozen {role}.engine")
        for field in ("model_requested", "effort_requested"):
            if field not in entry or (entry[field] is not None and (not isinstance(entry[field], str) or not entry[field])):
                fail(f"frozen {role}.{field} is malformed")
    return value


def observations(state):
    """Report only state-bound observations; argv is never effective effort."""
    result = {role: {"model_effective": None, "effort_effective": None, "evidence_basis": None} for role in ROLES}
    phases = state.get("phases", {})
    if not isinstance(phases, dict):
        fail("state phases must be an object")
    for phase in ("implement", "cleanup"):
        entry = phases.get(phase)
        if isinstance(entry, dict) and entry.get("model_effective") and entry.get("verdict") in {"PASS", "PASS_WITH_ISSUES"} and entry.get("completed_at"):
            basis = ("completed-phase/session-model-attestation"
                     if entry.get("engine") == "claude" and not entry.get("invocation_receipt") else None)
            if basis:
                result["worker"] = {"model_effective": entry["model_effective"], "effort_effective": None,
                                    "evidence_basis": basis}
    verify = phases.get("verify")
    if isinstance(verify, dict):
        evidence = verify.get("role_evidence") or {}
        if not isinstance(evidence, dict):
            fail("judge role evidence must be an object")
        for role, entry in evidence.items():
            if role in result and isinstance(entry, dict) and entry.get("identity_basis"):
                result[role] = {"model_effective": entry.get("model_observed"), "effort_effective": entry.get("effort_observed"),
                                "evidence_basis": entry.get("identity_basis")}
    return result


def primary_engine(state):
    verify = state.get("phases", {}).get("verify")
    value = verify["engine"] if isinstance(verify, dict) and "engine" in verify else state.get("engine")
    return name(value, "primary engine")


def native_version(engine):
    binary = shutil.which(engine)
    if binary is None:
        fail(f"install/authenticate {engine} and retry", f"{engine}-unavailable")
    try:
        proc = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as exc:
        fail(f"{engine} --version failed: {exc}; install/authenticate the native CLI and retry", f"{engine}-unavailable")
    if proc.returncode != 0:
        fail(f"{engine} --version exited {proc.returncode}; install/authenticate the native CLI and retry", f"{engine}-unavailable")
    match = re.search(r"\b\d+\.\d+\.\d+\b", proc.stdout)
    if not match:
        fail(f"{engine} --version did not establish a native version", "unsupported-role-option")
    return match[0]


def options(entry, role, *, model=None, version=None, cache=None, shared=SHARED):
    """Return additional argv only; caller retains the existing phase sandbox/tools."""
    engine = entry["engine"]
    requested_model, effort = entry.get("model_requested"), entry.get("effort_requested")
    model = requested_model or model
    if not requested_model and not effort:
        return {"argv": [], "capability": None}
    detail = f"{role}/{engine}: explicit model/effort unsupported; use a supported exact model or omit the override"
    validate_channel(entry, role)
    if not model:
        fail(detail + "; resolve the inherited model before validating effort", "unsupported-role-option")
    version = version or native_version(engine)
    capability = {"native_version": version, "model": model}
    if engine == "codex":
        path = Path(cache) if cache else Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "models_cache.json"
        try:
            raw = path.read_bytes()
            metadata = loads(raw)
            if not isinstance(metadata, dict) or not isinstance(metadata.get("models"), list) or any(not isinstance(row, dict) for row in metadata["models"]):
                raise ValueError("malformed native model metadata")
            rows = [row for row in metadata["models"] if row.get("slug") == model]
            if metadata.get("client_version") != version or len(rows) != 1:
                raise ValueError("native version or exact model is absent/ambiguous")
            advertised = rows[0]["supported_reasoning_levels"]
            if not isinstance(advertised, list) or any(not isinstance(item, dict) or not isinstance(item.get("effort"), str) or not item["effort"] for item in advertised):
                raise ValueError("malformed native effort metadata")
            levels = [item["effort"] for item in advertised]
        except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
            fail(f"{detail}; refresh native Codex model metadata: {exc}", "unsupported-role-option")
        capability.update(path=str(path.resolve()), sha256=digest(raw))
    else:
        text = adapter(engine, judge=True, shared=shared)
        if effort is not None:
            matches = re.findall(r"^<!-- devlyn-effort (\S+) (\S+) ([a-z,]+) -->$", text, re.M)
            levels = next((levels.split(",") for ver, selected, levels in matches if ver == version and selected == model), None)
            if levels is None:
                fail(detail + "; this Claude version/model has no validated adapter effort declaration; omit effort to select only the model", "unsupported-role-option")
        capability.update(path=str(shared / "adapters/claude.md"), sha256=digest(text.encode()))
    if effort is not None and effort not in levels:
        fail(f"{role}/{engine}/{model}: effort {effort!r} unsupported; supported: {', '.join(levels)}", "unsupported-role-option")
    args = (["-m" if engine == "codex" else "--model", requested_model] if requested_model else [])
    if effort:
        args += ["-c", "model_reasoning_effort=" + effort] if engine == "codex" else ["--effort", effort]
    return {"argv": args, "capability": capability}


def edit(work, role, value, shared=SHARED, default_engine="claude"):
    path = Path(work) / ".devlyn/engines.json"
    config, _ = read_config(path, optional=True, shared=shared)
    if role == "clear":
        for key in ("executor", "pair_judge_priority", "roles"):
            config.pop(key, None)
    elif role in ROLES:
        roles = config.setdefault("roles", {})
        if value == "clear":
            roles.pop(role, None)
            if not roles:
                config.pop("roles", None)
        else:
            if not isinstance(value, str):
                fail("role update requires --value JSON or clear")
            roles[role] = loads(value)
    else:
        fail("unknown role")
    validate(config, shared=shared)
    # Validate the complete proposed selection before replacing any bytes. Writes
    # may pin an engine installed later; availability is checked at dispatch.
    resolve(work, default_engine, proposed=config, available=lambda engine: True, shared=shared)
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
    from unittest.mock import patch

    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        (work / ".devlyn").mkdir()
        path = work / ".devlyn/engines.json"
        base = resolve(work, "codex", available=lambda e: True)
        assert [base["roles"][r]["engine"] for r in ROLES] == ["codex", "codex", "claude"]
        assert resolve(work, "claude", available=lambda e: True)["roles"]["primary_judge"]["channel"] == "inherited/adapter-defined"
        assert channel("claude", "primary_judge", explicit=True) == "claude-CLI"
        for role, engine in (("worker", "claude"), ("pair_judge", "grok")):
            unsupported = {"value": {"roles": {role: {"engine": engine, "model": "fixture-model"}}}, "path": "fixture", "sha256": "fixture"}
            try:
                resolve(work, "codex", run_input=unsupported, available=lambda e: True)
            except ValueError as exc:
                assert "unsupported-role-option" in str(exc)
            else:
                raise AssertionError("unsupported selected channel survived pre-PLAN resolution")
            if role == "pair_judge":
                assert resolve(work, "codex", run_input=unsupported, no_pair=True)["roles"][role]["skipped_reason"] == "user_no_pair"
        path.write_bytes(encoded({"executor": "claude", "custom": 7, "roles": {"worker": {"engine": "codex", "model": "gpt-6-astra", "effort": "high"}}}))
        selected = resolve(work, "codex", available=lambda e: True)
        assert selected["roles"]["primary_judge"]["engine"] == "claude"
        assert selected["roles"]["pair_judge"]["engine"] == "codex"
        over = {"value": {"roles": {"worker": {"engine": "claude"}}}, "path": "fixture", "sha256": "test"}
        assert resolve(work, "codex", run_input=over, available=lambda e: True)["roles"]["worker"]["model_requested"] is None
        flag = resolve(work, "claude", flag_engine="codex", available=lambda e: True)
        assert flag["roles"]["worker"]["effort_requested"] is None
        state = {"role_resolution": selected}
        path.write_bytes(encoded({"executor": "codex"}))
        assert snapshot(state) == selected
        assert observations({"phases": {"implement": {"engine": "codex", "model_effective": "gpt-6-astra", "invocation_receipt": {"path": "fixture"}, "verdict": "PASS", "completed_at": "fixture",
                                                      "role_argv": {"effort_requested": "high"}}, "verify": None}})["worker"] == {
            "model_effective": None, "effort_effective": None, "evidence_basis": None}
        attested = {"engine": "claude", "model_effective": "fixture-claude-model", "verdict": "PASS", "completed_at": "fixture"}
        assert observations({"phases": {"implement": attested}})["worker"] == {
            "model_effective": "fixture-claude-model", "effort_effective": None, "evidence_basis": "completed-phase/session-model-attestation"}
        assert observations({"phases": {"implement": {**attested, "verdict": "BLOCKED"}}})["worker"]["model_effective"] is None
        for malformed in (None, {}, {**selected, "sha256": "altered"}):
            try:
                snapshot({"role_resolution": malformed})
            except ValueError:
                pass
            else:
                raise AssertionError("present malformed snapshot became legacy")
        assert primary_engine({"engine": "codex", "phases": {"verify": {"engine": "claude"}}}) == "claude"
        for bad in ('{"roles":null}', '{"roles":{"worker":{"engine":"codex","effort":null}}}', '{"roles":{"x":{}}}', '{"roles":{"worker":{"engine":"codex","extra":1}}}', '{"executor":"codex","executor":"claude"}'):
            before = path.read_bytes()
            try:
                validate(loads(bad))
            except ValueError:
                pass
            else:
                raise AssertionError(bad)
            assert path.read_bytes() == before
        edit(work, "worker", '{"engine":"codex","model":"gpt-6-astra"}')
        before = path.read_bytes()
        try:
            edit(work, "worker", '{"engine":"grok"}')
        except ValueError:
            pass
        else:
            raise AssertionError("ineligible worker")
        assert path.read_bytes() == before
        path.write_bytes(encoded({"executor": "claude", "keep": 7}))
        before = path.read_bytes()
        for role, arguments in (("pair_judge", ["--value", '{"engine":"claude"}']),
                                ("worker", ["--value", "{"]), ("worker", [])):
            proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--workdir", str(work),
                                   "--set-role", role, *arguments], capture_output=True, text=True)
            assert proc.returncode == 1 and "BLOCKED:invalid-engine-config" in proc.stderr, proc.stderr
            assert "Traceback" not in proc.stderr and path.read_bytes() == before
        path.write_bytes(encoded({"executor": "claude", "pair_judge_priority": ["codex"]}))
        try:
            resolve(work, "claude", available=lambda engine: False)
        except ValueError as exc:
            assert "BLOCKED:codex-unavailable" in str(exc)
        else:
            raise AssertionError("explicit priority silently became solo")
        assert resolve(work, "claude", no_pair=True, available=lambda engine: False)["roles"]["pair_judge"]["skipped_reason"] == "user_no_pair"
        status = resolve(work, "claude", available=lambda engine: False, for_status=True)
        assert status["roles"]["pair_judge"]["engine"] is None
        assert status["roles"]["pair_judge"]["priority_requested"] == ["codex"]
        assert status["roles"]["pair_judge"]["skipped_reason"] is None
        assert status["roles"]["primary_judge"]["availability"] == "CLI-unavailable"
        before = path.read_bytes()
        proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--workdir", str(work)],
                              capture_output=True, text=True, env={**os.environ, "PATH": str(work / "no-binaries")})
        assert proc.returncode == 0 and loads(proc.stdout)["roles"]["pair_judge"]["engine"] is None, proc.stderr
        assert path.read_bytes() == before
        for engine in (None, ""):
            try:
                primary_engine({"engine": "codex", "phases": {"verify": {"engine": engine}}})
            except ValueError:
                pass
            else:
                raise AssertionError("malformed primary fell back")
        path.write_bytes(encoded({"roles": {"pair_judge": {"engine": "codex"}}}))
        try:
            resolve(work, "codex", available=lambda e: True)
        except ValueError:
            pass
        else:
            raise AssertionError("same engine pair")
        assert resolve(work, "codex", no_pair=True)["roles"]["pair_judge"]["skipped_reason"] == "user_no_pair"
        cache = work / "models.json"
        cache.write_bytes(encoded({"client_version": "0.153.4", "models": [{"slug": "gpt-6-astra", "supported_reasoning_levels": [{"effort": "ultra"}]}]}))
        entry = {"engine": "codex", "model_requested": "gpt-6-astra", "effort_requested": "ultra"}
        assert options(entry, "worker", version="0.153.4", cache=cache)["argv"][-1] == "model_reasoning_effort=ultra"
        cache.write_bytes(encoded({"client_version": "0.153.4", "models": [None]}))
        try:
            options(entry, "worker", version="0.153.4", cache=cache)
        except ValueError as exc:
            assert "unsupported-role-option" in str(exc)
        else:
            raise AssertionError("malformed native cache accepted")
        declaration = re.search(r"^<!-- devlyn-effort (\S+) (\S+) ([a-z,]+) -->$", adapter("claude", judge=True), re.M)
        assert declaration is not None
        version, known_model, levels = declaration.groups()
        explicit_effort = levels.split(",")[-1]
        assert options({"engine": "claude", "model_requested": known_model, "effort_requested": explicit_effort},
                       "primary_judge", version=version)["argv"][-1] == explicit_effort
        for future_model, future_version in (("fixture-next-model", "9.0.0"), ("fixture-other-model", "9.1.0")):
            future = {"engine": "claude", "model_requested": future_model, "effort_requested": None}
            for judge in ("primary_judge", "pair_judge"):
                result = options(future, judge, version=future_version)
                assert result["argv"] == ["--model", future_model]
                assert result["capability"]["native_version"] == future_version
                assert result["capability"]["sha256"] == digest(adapter("claude", judge=True).encode())
                try:
                    options({**future, "effort_requested": "high"}, judge, version=future_version)
                except ValueError as exc:
                    assert "adapter effort declaration" in str(exc)
                else:
                    raise AssertionError("unknown judge effort support was assumed")
        ineligible = work / "adapters"
        ineligible.mkdir()
        (ineligible / "claude.md").write_text("pair_judge: no\n")
        try:
            options(future, "primary_judge", version=future_version, shared=work)
        except ValueError as exc:
            assert "ineligible for judge" in str(exc)
        else:
            raise AssertionError("model-only selection bypassed adapter eligibility")
        for invalid in ({**entry, "effort_requested": "bogus"}, {"engine": "claude", "model_requested": "fixture-claude-model", "effort_requested": "high"}):
            try:
                options(invalid, "worker", version="0.153.4", cache=cache)
            except ValueError as exc:
                assert "unsupported-role-option" in str(exc)
            else:
                raise AssertionError("unsupported option")
        edit(work, "clear", None)
        assert not path.exists()
        with patch.object(shutil, "which", return_value="/fixture/codex"):
            for response, reason in ((FileNotFoundError("fixture"), "codex-unavailable"),
                                     (subprocess.TimeoutExpired(["codex", "--version"], 20), "codex-unavailable"),
                                     (subprocess.CompletedProcess([], 1, "", "failed"), "codex-unavailable"),
                                     (subprocess.CompletedProcess([], 0, "unparsable", ""), "unsupported-role-option")):
                kwargs = {"side_effect": response} if isinstance(response, Exception) else {"return_value": response}
                with patch.object(subprocess, "run", **kwargs):
                    try:
                        native_version("codex")
                    except ValueError as exc:
                        assert f"BLOCKED:{reason}:" in str(exc)
                    else:
                        raise AssertionError("failed native version probe accepted")
    print("PASS role-config self-test: precedence, isolation, atomic validation, capability and legacy identity")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--workdir", type=Path, default=Path.cwd())
    parser.add_argument("--default-engine", default="claude")
    parser.add_argument("--engine")
    parser.add_argument("--role-config", type=Path)
    parser.add_argument("--no-pair", action="store_true")
    parser.add_argument("--state", type=Path)
    parser.add_argument("--role", choices=ROLES)
    parser.add_argument("--resolved-model")
    parser.add_argument("--set-role", choices=(*ROLES, "clear"))
    parser.add_argument("--value")
    args = parser.parse_args()
    try:
        if args.self_test:
            return self_test()
        if args.set_role:
            edit(args.workdir, args.set_role, args.value, default_engine=args.default_engine)
        if args.state:
            state = loads(args.state.read_bytes())
            value = snapshot(state)
            if value is None:
                fail("run has no frozen roles; complete PHASE0 role resolution first")
            value = {**value, "observations": observations(state)}
        else:
            run_input = None
            if args.role_config:
                config, pin = read_config(args.role_config, run=True)
                run_input = {**pin, "value": config}
            value = resolve(args.workdir, args.default_engine, flag_engine=args.engine, run_input=run_input, no_pair=args.no_pair,
                            for_status=not args.role)
            if args.set_role:
                print("Configuration saved; CLI presence is status only. Availability/authentication is enforced before dispatch.", file=sys.stderr)
        if args.role:
            entry = value["roles"][args.role]
            value = {**entry, **options(entry, args.role, model=args.resolved_model),
                     "observation": value.get("observations", {}).get(args.role)}
        print(json.dumps(value, sort_keys=True))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
