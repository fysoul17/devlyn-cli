#!/usr/bin/env python3
"""Authenticate explicit read-only judge transport; never accept mutation receipts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import runpy
import sys
import tempfile

sys.dont_write_bytecode = True
ROLE = runpy.run_path(Path(__file__).with_name("role-config.py"))
loads, encoded, digest = (ROLE[key] for key in ("loads", "encoded", "digest"))


def require(ok, detail):
    if not ok:
        raise ValueError("BLOCKED:judge-role-evidence: " + detail)


def option(argv, *names):
    values = []
    for index, item in enumerate(argv):
        for name in names:
            if item == name:
                require(index + 1 < len(argv), f"missing {name}")
                values.append(argv[index + 1])
            elif item.startswith(name + "="):
                values.append(item[len(name) + 1:])
    require(len(values) <= 1, f"duplicate {names[0]}")
    return values[0] if values else None


def seal(devlyn, name):
    path = devlyn / name
    require(path.parent == devlyn and not path.is_symlink() and path.is_file(), f"not a regular canonical artifact: {name}")
    raw = path.read_bytes()
    return {"path": ".devlyn/" + name, "sha256": digest(raw), "bytes": len(raw)}, raw


def claude_result(raw, exit_code):
    value = loads(raw)
    require(type(exit_code) is int and exit_code == 0 and isinstance(value, dict), "unsuccessful Claude execution")
    require(value.get("type") == "result" and value.get("subtype") == "success"
            and value.get("is_error") is False and value.get("stop_reason") == "end_turn"
            and isinstance(value.get("session_id"), str) and bool(value["session_id"].strip())
            and isinstance(value.get("result"), str), "unsuccessful or malformed Claude terminal envelope")
    model = runpy.run_path(Path(__file__).with_name("state-phase-write.py"))["select_claude_primary_model"](value)
    return value["result"].encode(), model, value["session_id"]


def codex_header(stderr):
    prefix, separator, _ = stderr.partition("\nuser\n")
    require(bool(separator), "native header must precede the echoed user prompt")
    starts = list(re.finditer(r"^OpenAI Codex v[^\n]+\n--------\n", prefix, re.M))
    require(len(starts) == 1, "missing or conflicting first native Codex header")
    header = prefix[starts[0].end():]
    require(header.endswith("\n--------"), "malformed native Codex header boundary")
    fields = {"cli_version": "codex-cli " + starts[0].group(0).splitlines()[0].removeprefix("OpenAI Codex v")}
    for key in ("model", "workdir", "sandbox", "session id", "reasoning effort"):
        values = re.findall(r"^" + re.escape(key) + r": (.+)$", header, re.M)
        require(len(values) == 1 and bool(values[0].strip()), f"missing/conflicting native {key}")
        fields[key] = values[0]
    return fields


def describe(devlyn, state, role, exit_code):
    require(type(exit_code) is int and exit_code == 0, "judge process did not complete successfully")
    resolution = ROLE["snapshot"](state)
    require(resolution is not None and role in ("primary_judge", "pair_judge"), "missing frozen judge selection")
    entry = resolution["roles"][role]
    engine = entry["engine"]
    require(engine in {"codex", "claude"}, "this judge channel has no explicit-field evidence contract")
    require(not entry.get("skipped_reason"), "cannot authenticate a skipped judge")
    verify = state.get("phases", {}).get("verify", {})
    require(isinstance(verify, dict) and type(verify.get("round")) is int, "missing VERIFY round")
    require(ROLE["primary_engine"](state) == resolution["roles"]["primary_judge"]["engine"], "primary differs from frozen selection")
    stem = engine + "-judge.r" + str(verify["round"])
    artifacts = {}
    for key, suffix in (("argv", ".argv.json"), ("prompt", ".prompt"), ("stderr", ".stderr")):
        artifacts[key], raw = seal(devlyn, stem + suffix)
        if key == "argv":
            argv = loads(raw)
        elif key == "prompt":
            prompt = raw.decode()
        else:
            stderr = raw.decode()
    require(isinstance(argv, list) and all(isinstance(x, str) for x in argv), "argv must be an array of strings")
    require(prompt in argv, "canonical prompt is not an exact dispatched argument")
    diagnostics = stderr.partition("\nuser\n")[0] if engine == "codex" else stderr
    require(not re.search(r"(?im)^.*(?:model|effort).*\b(?:ignor\w*|clamp\w*|unsupported|not supported)\b", diagnostics), "native diagnostic rejected or ignored an explicit option")
    requested_model, requested_effort = entry.get("model_requested"), entry.get("effort_requested")
    supplied_model = option(argv, "-m", "--model")
    if requested_model is not None:
        require(supplied_model == requested_model, "requested model differs from argv")
    if engine == "claude":
        for flag, expected in (("--permission-mode", "dontAsk"), ("--tools", "Read,Grep,Glob"),
                               ("--allowedTools", "Read,Grep,Glob"), ("--setting-sources", "project"), ("--output-format", "json")):
            require(option(argv, flag) == expected, f"Claude {flag} differs from read-only contract")
        require("--strict-mcp-config" in argv and loads(option(argv, "--mcp-config") or "null") == {"mcpServers": {}}, "Claude MCP isolation missing")
        require(any(Path(arg).name == "run-bounded.py" and argv[i + 1:i + 3] == ["600", "--"] for i, arg in enumerate(argv)), "Claude 600s bound missing")
        if requested_effort:
            require(option(argv, "--effort") == requested_effort, "requested effort differs from argv")
        artifacts["raw"], raw = seal(devlyn, stem + ".output.json")
        derived, observed, session = claude_result(raw, exit_code)
        effort = None
        basis = "native-Claude-result-modelUsage"
    else:
        require(option(argv, "-s", "--sandbox") == "read-only", "judge sandbox is not read-only")
        cwd = option(argv, "-C", "--cd")
        require(isinstance(cwd, str) and Path(cwd).is_absolute() and Path(cwd).resolve() == devlyn.parent.resolve(), "judge cwd differs from actual worktree")
        require(not any(arg in argv for arg in ("--dangerously-bypass-approvals-and-sandbox", "--yolo", "--full-auto")), "judge bypass is forbidden")
        flags = [argv[i + 1] for i, item in enumerate(argv[:-1]) if item in {"-c", "--config"}]
        efforts = [flag.split("=", 1)[1].strip('"') for flag in flags if flag.startswith("model_reasoning_effort=")]
        require(len(efforts) == 1 and (not requested_effort or efforts[0] == requested_effort), "missing/conflicting requested effort")
        require("[codex-monitored] isolated=1\n" in diagnostics, "missing actual isolation marker")
        require(re.search(r"^\[codex-monitored\] start: .* timeout=600s ", diagnostics, re.M) is not None, "missing actual 600s bound")
        header = codex_header(stderr)
        require(Path(header["workdir"]).is_absolute() and Path(header["workdir"]).resolve() == devlyn.parent.resolve()
                and header["sandbox"] == "read-only", "observed workdir/sandbox mismatch")
        observed, effort, session = header["model"], header["reasoning effort"], header["session id"]
        require(effort == efforts[0], "native effort differs from dispatched effort")
        artifacts["raw"], derived = seal(devlyn, stem + ".stdout")
        basis = "native-Codex-configuration-header"
    require(requested_model is None or observed == requested_model, "observed model differs from explicit requested model")
    artifacts["stdout"] = {"path": ".devlyn/" + stem + ".stdout", "sha256": digest(derived), "bytes": len(derived)}
    record = {"schema": 1, "run_id": state.get("run_id"), "round": verify["round"], "role": role,
              "engine": engine, "model_requested": requested_model, "effort_requested": requested_effort,
              "model_observed": observed, "effort_observed": effort, "session_id": session,
              "identity_basis": basis, "exit_code": exit_code, "resolution_sha256": resolution["sha256"], "artifacts": artifacts}
    return record, derived


def authenticate(devlyn, state, role):
    resolution = ROLE["snapshot"](state)
    engine = resolution["roles"][role]["engine"]
    stem = engine + "-judge.r" + str(state["phases"]["verify"]["round"])
    binding, raw = seal(devlyn, stem + ".role-evidence.json")
    document = loads(raw)
    actual, derived = describe(devlyn, state, role, document.get("exit_code"))
    require(actual == document, "retained role evidence differs from current raw/selection")
    _, stdout = seal(devlyn, stem + ".stdout")
    require(stdout == derived, "derived stdout differs from retained native result")
    _, canonical = seal(devlyn, engine + "-judge.stdout")
    require(canonical == derived, "canonical collector stdout differs from retained native result")
    return {**binding, "model_observed": actual["model_observed"], "effort_observed": actual["effort_observed"],
            "identity_basis": actual["identity_basis"], "artifacts": list(actual["artifacts"].values())}


def required_roles(state):
    resolution = ROLE["snapshot"](state)
    if resolution is None:
        return []
    return [role for role in ("primary_judge", "pair_judge")
            if not resolution["roles"][role].get("skipped_reason")
            and any(resolution["roles"][role].get(key) is not None for key in ("model_requested", "effort_requested"))]


def self_test():
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp).resolve(); devlyn = work / ".devlyn"; devlyn.mkdir()
        config = {"roles": {"primary_judge": {"engine": "claude", "model": "fixture-claude-model", "effort": "high"},
                            "pair_judge": {"engine": "codex", "model": "gpt-6-astra", "effort": "high"}}}
        (devlyn / "engines.json").write_bytes(encoded(config))
        selection = ROLE["resolve"](work, "codex", available=lambda e: True)
        state = {"run_id": "fixture", "role_resolution": selection, "engine": "codex", "phases": {"verify": {"engine": "claude", "round": 0}}}
        envelope = {"type": "result", "subtype": "success", "is_error": False, "stop_reason": "end_turn",
                    "session_id": "fixture-claude", "result": "PASS", "modelUsage": {"fixture-claude-model": {}}}
        argv = ["python3", "run-bounded.py", "600", "--", "claude", "-p", "review", "--model", "fixture-claude-model", "--effort", "high", "--permission-mode", "dontAsk", "--tools", "Read,Grep,Glob", "--allowedTools", "Read,Grep,Glob", "--setting-sources", "project", "--output-format", "json", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}']
        for suffix, raw in (("argv.json", encoded(argv)), ("prompt", b"review"), ("stderr", b""), ("output.json", encoded(envelope))):
            (devlyn / ("claude-judge.r0." + suffix)).write_bytes(raw)
        receipt, text = describe(devlyn, state, "primary_judge", 0)
        assert text == b"PASS" and receipt["effort_observed"] is None
        (devlyn / "claude-judge.stdout").write_bytes(text)
        (devlyn / "claude-judge.r0.stdout").write_bytes(text)
        (devlyn / "claude-judge.r0.role-evidence.json").write_bytes(encoded(receipt))
        authenticate(devlyn, state, "primary_judge")
        for field, value in (("subtype", "error_max_turns"), ("stop_reason", "tool_use"), ("is_error", True), ("session_id", ""), ("result", None)):
            bad = {**envelope, field: value}
            try:
                claude_result(encoded(bad), 0)
            except ValueError:
                pass
            else:
                raise AssertionError(field)
        for status in (1, 124, True):
            try:
                describe(devlyn, state, "primary_judge", status)
            except ValueError:
                pass
            else:
                raise AssertionError("failed exit accepted")
        (devlyn / "claude-judge.stdout").write_bytes(b"forged PASS")
        try:
            authenticate(devlyn, state, "primary_judge")
        except ValueError:
            pass
        else:
            raise AssertionError("derived tampering accepted")
        prompt = "review unsupported model/effort warning handling\n"
        argv = ["bash", "codex-monitored.sh", "-C", str(work), "-s", "read-only", "-m", "gpt-6-astra", "-c", "model_reasoning_effort=high", prompt]
        header = f"[codex-monitored] start: ts=fixture timeout=600s bin=codex\n[codex-monitored] isolated=1\nOpenAI Codex v0.153.4\n--------\nworkdir: {work}\nmodel: gpt-6-astra\nsandbox: read-only\nreasoning effort: high\nsession id: fixture-codex\n--------\nuser\nreview\n"
        header = header.replace("\nuser\nreview\n", "\nuser\n" + prompt)
        for suffix, raw in (("argv.json", encoded(argv)), ("prompt", prompt.encode()), ("stderr", header.encode()), ("stdout", b"PASS\n")):
            (devlyn / ("codex-judge.r0." + suffix)).write_bytes(raw)
        receipt, _ = describe(devlyn, state, "pair_judge", 0)
        assert receipt["model_observed"] == "gpt-6-astra"
        alias = work / "logical-cwd"
        alias.symlink_to(work, target_is_directory=True)
        alias_argv = [str(alias) if arg == str(work) else arg for arg in argv]
        alias_header = header.replace(f"workdir: {work}\n", f"workdir: {alias}\n")
        (devlyn / "codex-judge.r0.argv.json").write_bytes(encoded(alias_argv))
        (devlyn / "codex-judge.r0.stderr").write_text(alias_header)
        receipt, _ = describe(devlyn, state, "pair_judge", 0)
        assert receipt["artifacts"]["argv"]["sha256"] == digest(encoded(alias_argv))
        assert (devlyn / "codex-judge.r0.stderr").read_text() == alias_header
        elsewhere = work / "elsewhere"; elsewhere.mkdir()
        (devlyn / "codex-judge.r0.argv.json").write_bytes(encoded([str(elsewhere) if arg == str(work) else arg for arg in argv]))
        try:
            describe(devlyn, state, "pair_judge", 0)
        except ValueError:
            pass
        else:
            raise AssertionError("different physical worktree accepted")
        (devlyn / "codex-judge.r0.argv.json").write_bytes(encoded(argv))
        for bad in ("Warning: model effort unsupported and ignored\n" + header, "\nuser\n" + header, header.replace("\nmodel:", "\nmodel: gpt-5.6-sol\nmodel:"), header.replace("sandbox: read-only", "sandbox: workspace-write"), header.replace("model: gpt-6-astra", "model: gpt-5.6-sol"), header.replace("[codex-monitored] isolated=1\n", ""), header.replace("timeout=600s", "timeout=300s")):
            (devlyn / "codex-judge.r0.stderr").write_text(bad)
            try:
                describe(devlyn, state, "pair_judge", 0)
            except ValueError:
                pass
            else:
                raise AssertionError("invalid native header accepted")
    print("PASS judge-role-evidence self-test: success/error/timeout, raw derivation, tampering and native header identity")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--devlyn-dir", type=Path, default=Path(".devlyn"))
    parser.add_argument("--role", choices=("primary_judge", "pair_judge"))
    parser.add_argument("--exit-code", type=int)
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.role is None or args.exit_code is None:
        parser.error("--role and --exit-code are required")
    try:
        devlyn = args.devlyn_dir.resolve()
        state = loads((devlyn / "pipeline.state.json").read_bytes())
        record, derived = describe(devlyn, state, args.role, args.exit_code)
        stem = record["engine"] + "-judge.r" + str(record["round"])
        target = devlyn / (stem + ".role-evidence.json")
        require(not target.exists(), "role evidence already exists for this round")
        stdout = devlyn / (record["engine"] + "-judge.stdout")
        require(not stdout.exists(), "canonical stdout already exists")
        if record["engine"] == "claude":
            require(not (devlyn / (stem + ".stdout")).exists(), "derived stdout already exists")
            (devlyn / (stem + ".stdout")).write_bytes(derived)
        stdout.write_bytes(derived)
        target.write_bytes(encoded(record))
        print(json.dumps(authenticate(devlyn, state, args.role), sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
