#!/usr/bin/env python3
"""Render exact phase-prompt bytes and print their SHA-256 digest."""
from __future__ import annotations

import runpy
import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import tempfile


SNAPSHOT_FRAMES = ("metadata", "contract", "goal", "expected", "authorized_surface", "diff", "mechanical")
EXCLUDED_ADAPTER_SECTION = re.compile(
    rb"^## (?:Role eligibility|Invocation)(?:\r?\n|\Z).*?(?=^## |\Z)",
    re.MULTILINE | re.DOTALL,
)
EXCLUDED_ADAPTER_HEADING = re.compile(
    rb"^## (?:Role eligibility|Invocation)\r?$", re.MULTILINE
)


def project_adapter(content: bytes) -> bytes:
    projected = EXCLUDED_ADAPTER_SECTION.sub(b"", content)
    assert EXCLUDED_ADAPTER_HEADING.search(projected) is None
    return projected


def frame(name: str, payload: bytes) -> bytes:
    return name.encode("ascii") + b" " + str(len(payload)).encode("ascii") + b"\n" + payload + b"\n"


SHARED = pathlib.Path(__file__).resolve().parent
SKILL = SHARED.parent / "devlyn-resolve"
# phase → (prompt header, canonical body, output stem, phase-specific frame)
WORKER_PHASES = {
    "implement": (b"IMPLEMENT/1\n", "implement.md", "implement.prompt", "findings"),
    "probe_derive": (b"PROBE_DERIVE/1\n", "probe-derive.md", "probe-derive.prompt", "requirements"),
}


def phase_body(name: str, prefix: str, kind: str) -> bytes:
    body = SKILL / "references" / "phases" / name
    try:
        return body.read_bytes()
    except OSError as exc:
        raise SystemExit(f"BLOCKED:{prefix}:{kind}:{name} is unreadable beside the renderer: {exc}") from exc


def verify_body() -> bytes:
    return phase_body("verify.md", "verify-input-invalid", "rubric")


def hashed(work: pathlib.Path, prefix: str, kind: str, relative: object, recorded: object) -> bytes:
    """Read a state-recorded source file and refuse bytes that differ from its recorded sha256."""
    if not isinstance(relative, str) or not relative or not isinstance(recorded, str) \
            or re.fullmatch(r"[0-9a-f]{64}", recorded) is None:
        raise SystemExit(f"BLOCKED:{prefix}:{kind}:state records no path and sha256")
    path = pathlib.Path(relative)
    path = path if path.is_absolute() else work / path
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise SystemExit(f"BLOCKED:{prefix}:{kind}:{relative} is unreadable: {exc}") from exc
    if hashlib.sha256(raw).hexdigest() != recorded:
        raise SystemExit(f"BLOCKED:{prefix}:{kind}:{relative} does not match its recorded sha256")
    return raw


def build_verify_snapshot(devlyn: pathlib.Path, state: dict) -> bytes:
    """Derive the one input snapshot both VERIFY judges receive."""
    check = runpy.run_path(str(pathlib.Path(__file__).with_name("spec-verify-check.py")))
    work = devlyn.resolve().parent

    def invalid(kind: str, detail: str) -> SystemExit:
        return SystemExit(f"BLOCKED:verify-input-invalid:{kind}:{detail}")

    source = state.get("source") if isinstance(state.get("source"), dict) else {}
    generated = source.get("type") == "generated"
    if source.get("type") not in {"generated", "spec"}:
        raise invalid("contract", "state.source.type must be spec or generated")
    field = "criteria" if generated else "spec"
    contract = hashed(work, "verify-input-invalid", "contract", source.get(field + "_path"), source.get(field + "_sha256"))
    goal = (hashed(work, "verify-input-invalid", "goal", source.get("goal_path"), source.get("goal_sha256"))
            if generated else b"")
    expected = b""
    if not generated:
        spec_path = pathlib.Path(source["spec_path"])
        sibling = (spec_path if spec_path.is_absolute() else work / spec_path).with_name("spec.expected.json")
        bound_error = check["expected_contract_error"](source, spec_path if spec_path.is_absolute() else work / spec_path)
        if bound_error:
            raise invalid("expected", bound_error)
        if sibling.exists():
            _data, error = check["load_expected_contract"](sibling)
            if error:
                raise invalid("expected", error)
            expected = sibling.read_bytes()
    base = ((state.get("base_ref") or {}).get("sha") or "")
    if re.fullmatch(r"[0-9a-f]{40}", base) is None:
        raise invalid("base", "state.base_ref.sha must be a full commit sha")
    revs = subprocess.run(["git", "rev-parse", base + "^{commit}", "HEAD^{commit}"],
                          cwd=work, capture_output=True, text=True)
    commits = revs.stdout.split()
    if revs.returncode != 0 or len(commits) != 2 or commits[0] != base:
        raise invalid("base", "base or HEAD is not a resolvable commit")
    verify_only = state.get("mode") == "verify-only"
    if (devlyn / "external-diff.patch").is_file() and not verify_only:
        raise invalid("diff", ".devlyn/external-diff.patch requires mode verify-only")
    diff_text, error = check["diff_text_for_expected"](work, devlyn, state)
    if error:
        raise invalid("diff", error)
    surface = None
    if not verify_only:
        surface, error = check["load_authorized_surface"](devlyn)
        if error:
            raise invalid("surface", error)
    try:
        mechanical = (devlyn / "spec-verify.results.json").read_bytes()
    except OSError as exc:
        raise invalid("mechanical", f"sealed results are unreadable: {exc}") from exc
    verify = state["phases"]["verify"]
    metadata = {
        "run_id": state.get("run_id"), "round": verify.get("round"),
        "verify_started_at": verify.get("started_at"), "workdir": str(work), "mode": state.get("mode"),
        "source": {"type": source["type"], "contract": source.get(field + "_path"),
                   "goal": source.get("goal_path") if generated else None},
        "base_sha": base, "head_sha": commits[1],
        "present": {"goal": generated, "expected": bool(expected), "authorized_surface": surface is not None},
    }
    payloads = {
        "metadata": json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        "contract": contract, "goal": goal, "expected": expected,
        "authorized_surface": b"" if surface is None else json.dumps(surface).encode("utf-8"),
        "diff": diff_text.encode("utf-8", "surrogateescape"), "mechanical": mechanical,
    }
    return b"".join(frame(name, payloads[name]) for name in SNAPSHOT_FRAMES)


def render_worker(devlyn: pathlib.Path, phase: str, engine: str, round_: int) -> tuple[bytes, pathlib.Path]:
    """Exact worker prompt bytes from state: the owner adds no text of its own."""
    header, body_name, stem, extra = WORKER_PHASES[phase]
    work = devlyn.resolve().parent
    writer = runpy.run_path(str(SHARED / "state-phase-write.py"))

    def invalid(kind: str, detail: str) -> SystemExit:
        return SystemExit(f"BLOCKED:phase-input-invalid:{kind}:{detail}")

    try:
        state = writer["read_state"](devlyn / "pipeline.state.json")
    except (OSError, ValueError, SystemExit) as exc:
        raise invalid("state", str(exc)) from exc
    phases = state.get("phases") if isinstance(state.get("phases"), dict) else {}
    plan = phases.get("plan")
    if not isinstance(plan, dict) or plan.get("completed_at") is None or plan.get("verdict") not in {"PASS", "PASS_WITH_ISSUES"}:
        raise invalid("plan", "PLAN must complete with a passing verdict before a worker prompt renders")
    try:
        writer["validate_plan_output"](state, devlyn, phase)
    except SystemExit as exc:
        raise invalid("plan", str(exc)) from exc
    # The prompt reflects completed state only: render after the predecessor completes, before the phase opens.
    for name in ("probe_derive", "implement", "verify"):
        entry = phases.get(name)
        if isinstance(entry, dict) and entry.get("started_at") and entry.get("completed_at") is None:
            raise invalid("predecessor", f"phases.{name} is still open; complete it before rendering")
    adapter = SHARED / "adapters" / f"{engine}.md"
    if not adapter.is_file():
        raise invalid("adapter", f"no adapter for engine {engine!r}")
    source = state.get("source") if isinstance(state.get("source"), dict) else {}
    generated = source.get("type") == "generated"
    field = "criteria" if generated else "spec"
    contract = hashed(work, "phase-input-invalid", "contract", source.get(field + "_path"), source.get(field + "_sha256"))
    goal = (hashed(work, "phase-input-invalid", "goal", source.get("goal_path"), source.get("goal_sha256"))
            if generated else b"")
    metadata = {
        "run_id": state.get("run_id"), "phase": phase, "round": round_, "workdir": str(work), "mode": state.get("mode"),
        "base_sha": (state.get("base_ref") or {}).get("sha"),
        "source": {"type": source.get("type"), "contract": source.get(field + "_path"),
                   "goal": source.get("goal_path") if generated else None},
        "bindings": {"DEVLYN_SKILL_DIR": str(SKILL), "DEVLYN_SHARED_DIR": str(SHARED),
                     "CODEX_MONITORED_PATH": str(SHARED / "codex-monitored.sh")},
    }
    if phase == "probe_derive":
        check = runpy.run_path(str(SHARED / "spec-verify-check.py"))
        contract_path = pathlib.Path(source[field + "_path"])
        try:
            requirements, error = check["resolve_required_risk_probe_requirements"](
                contract_path if contract_path.is_absolute() else work / contract_path)
        except (OSError, UnicodeError) as exc:
            requirements, error = None, str(exc)
        if error:
            raise invalid("requirements", error)
        payload = json.dumps(requirements, sort_keys=True).encode("utf-8")
    else:
        implement = phases.get("implement") if isinstance(phases.get("implement"), dict) else None
        progress = implement.get("exec") if implement else None
        total = writer["execution_phase_count"]((devlyn / "plan.md").read_bytes())
        if writer["valid_phase_gate_progress"](progress):
            metadata["exec"] = {"current": progress["current"], "total": progress["total"]}
        elif implement is None and total >= 2:
            metadata["exec"] = {"current": 1, "total": total}
        predecessor = writer["repair_predecessor"](state)
        name, entry = predecessor if predecessor else (None, {})
        merged = entry.get("merged") if name == "verify" else None
        payload = b""
        metadata["repair_of"] = None
        if name == "verify" and entry.get("verdict") == "NEEDS_WORK" and isinstance(merged, dict):
            findings = work / str(merged.get("findings_file") or "")
            if findings.is_symlink() or not findings.is_file():
                raise invalid("findings", "the merged VERIFY findings file is missing or not a regular file")
            try:
                payload, metadata["repair_of"] = findings.read_bytes(), "verify"
            except OSError as exc:
                raise invalid("findings", f"the merged VERIFY findings file is unreadable: {exc}") from exc
        elif name == "implement" and entry.get("verdict") == "FAIL" and "exec" in metadata:
            metadata["repair_of"] = "phase_gate"
    try:
        adapter_bytes = adapter.read_bytes()
    except OSError as exc:
        raise invalid("adapter", f"{adapter.name} is unreadable: {exc}") from exc
    frames = {"adapter": project_adapter(adapter_bytes), "body": phase_body(body_name, "phase-input-invalid", "body"),
              "metadata": json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode("utf-8"),
              "contract": contract, "goal": goal, extra: payload}
    prompt = header + b"".join(frame(name, frames[name]) for name in ("adapter", "body", "metadata", "contract", "goal", extra))
    return prompt, devlyn / f"{stem}.{round_}"


def write_atomic(output: pathlib.Path, rendered: bytes) -> str:
    if not output.parent.is_dir():
        raise SystemExit(f"error: prompt output parent is not a directory: {output.parent}")
    fd, temporary = tempfile.mkstemp(dir=output.parent, prefix=output.name + ".tmp.")
    temporary_path = pathlib.Path(temporary)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(output)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
    return hashlib.sha256(rendered).hexdigest()


def render_verify(role: str, engine: str, snapshot: bytes) -> bytes:
    """Exact judge prompt bytes: projected adapter, rubric, role, shared snapshot."""
    if role not in {"primary_judge", "pair_judge"}:
        raise SystemExit(f"error: unknown VERIFY role {role!r}")
    adapter = pathlib.Path(__file__).with_name("adapters") / f"{engine}.md"
    return (b"VERIFY/1\n" + frame("adapter", project_adapter(adapter.read_bytes()))
            + frame("rubric", verify_body()) + frame("role", role.encode("ascii"))
            + frame("snapshot", snapshot))


def prompt_frames(prompt: bytes) -> dict[str, bytes]:
    """Strictly split a rendered VERIFY prompt into its named frames."""
    if not prompt.startswith(b"VERIFY/1\n"):
        raise ValueError("not a VERIFY/1 prompt")
    frames, offset = {}, len(b"VERIFY/1\n")
    for name in ("adapter", "rubric", "role", "snapshot"):
        header_end = prompt.find(b"\n", offset)
        label, _, length = prompt[offset:header_end].partition(b" ")
        if header_end < 0 or label != name.encode("ascii") or not length.isdigit():
            raise ValueError(f"malformed VERIFY prompt frame {name}")
        start, end = header_end + 1, header_end + 1 + int(length)
        if prompt[end:end + 1] != b"\n":
            raise ValueError(f"malformed VERIFY prompt frame {name}")
        frames[name], offset = prompt[start:end], end + 1
    if offset != len(prompt):
        raise ValueError("trailing bytes after VERIFY prompt frames")
    return frames


def render_prompt(
    adapter: pathlib.Path,
    canonical_body: pathlib.Path,
    task_context: pathlib.Path,
    output: pathlib.Path,
) -> str:
    try:
        adapter_bytes = adapter.read_bytes()
        body_bytes = canonical_body.read_bytes()
        context_bytes = task_context.read_bytes()
    except OSError as exc:
        raise SystemExit(f"error: prompt input unreadable: {exc}") from exc
    rendered = (project_adapter(adapter_bytes) + body_bytes + context_bytes).rstrip(b"\n")
    return write_atomic(output, rendered)


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="phase-prompt-render-") as raw:
        root = pathlib.Path(raw)
        adapter = root / "adapter.md"
        body = root / "plan.md"
        context = root / "task-context"
        output = root / ".devlyn" / "plan.prompt"
        output.parent.mkdir()
        original_directory = pathlib.Path.cwd()
        os.chdir(root)
        try:
            working_directory = pathlib.Path.cwd()
            adapter_bytes = (
                b"# Claude adapter\r\n"
                b"## Identity\r\nkept-identity-\xff\r\n"
                b"## Role eligibility\nremove-role\r\n"
                b"## Output discipline\r\nkept-output-\x80\n"
                b"## Invocation\r\nremove-invocation\n"
                b"## Anti-patterns\nkept-tail-without-newline"
            )
            projected_adapter = (
                b"# Claude adapter\r\n"
                b"## Identity\r\nkept-identity-\xff\r\n"
                b"## Output discipline\r\nkept-output-\x80\n"
                b"## Anti-patterns\nkept-tail-without-newline"
            )
            for metadata_free in (
                b"# Codex adapter\r\n## Identity\nkept-\xfe",
                b"# omp adapter\n## Output discipline\r\nkept\x81",
            ):
                assert project_adapter(metadata_free) == metadata_free

            body_bytes = b"# PHASE 1 \xe2\x80\x94 PLAN\n"
            context_bytes = (
                b"Working directory: "
                + os.fsencode(working_directory)
                + b"\nPlan output: "
                + os.fsencode(working_directory / ".devlyn" / "plan.md")
                + b"\ncontext-without-newline"
            )
            for path, content in (
                (adapter, adapter_bytes),
                (body, body_bytes),
                (context, context_bytes),
            ):
                path.write_bytes(content)
            expected = projected_adapter + body_bytes + context_bytes
            digest = render_prompt(adapter, body, context, output)
            assert output.read_bytes() == expected
            assert digest == hashlib.sha256(expected).hexdigest()
            assert render_prompt(adapter, body, context, output) == digest
            assert output.read_bytes() == expected

            context_prefix = context_bytes.removesuffix(b"context-without-newline")
            for terminal_lfs in (b"", b"\n", b"\n\n"):
                case_context = context_prefix + b"context-terminal-lf-case" + terminal_lfs
                context.write_bytes(case_context)
                expected = (projected_adapter + body_bytes + case_context).rstrip(b"\n")
                digest = render_prompt(adapter, body, context, output)
                written = output.read_bytes()
                assert not written.endswith(b"\n")
                assert digest == hashlib.sha256(written).hexdigest()
                assert written == expected

        finally:
            os.chdir(original_directory)
    verify_self_test()
    worker_self_test()
    print("SELFTEST PASS: projected exact bytes + VERIFY snapshot guards + worker prompts from state")
    return 0


def split_frames(prompt: bytes, header: bytes, names: tuple[str, ...]) -> dict[str, bytes]:
    assert prompt.startswith(header), prompt[:40]
    frames, offset = {}, len(header)
    for name in names:
        end = prompt.index(b"\n", offset)
        label, _, length = prompt[offset:end].partition(b" ")
        assert label == name.encode("ascii"), (label, name)
        start = end + 1
        frames[name], offset = prompt[start:start + int(length)], start + int(length) + 1
    assert offset == len(prompt)
    return frames


def worker_self_test() -> None:
    global SHARED, SKILL
    writer = runpy.run_path(str(SHARED / "state-phase-write.py"))
    with tempfile.TemporaryDirectory(prefix="phase-prompt-render-worker-") as raw:
        work = pathlib.Path(raw).resolve()
        devlyn = work / ".devlyn"
        devlyn.mkdir()
        contract = b"# Spec\r\n\n<!-- devlyn:verification -->\n## Verification\n\n- prints ok \xff\n"
        (work / "spec.md").write_bytes(contract)
        plan = b'<!-- devlyn:authorized-surface -->\n```json\n{"authorized_surface": ["app.py"]}\n```\n'
        (devlyn / "plan.md").write_bytes(plan)
        stamp = "2026-10-03T00:00:00.000Z"
        state = {"version": "3.0", "run_id": "rs-render", "mode": "spec", "base_ref": {"sha": "a" * 40},
                 "source": {"type": "spec", "spec_path": "spec.md", "spec_sha256": hashlib.sha256(contract).hexdigest()},
                 "rounds": {"global": 0, "max_rounds": 4},
                 "phases": {"plan": {"started_at": stamp, "completed_at": stamp, "round": 0, "verdict": "PASS",
                                     "output_sha256": hashlib.sha256(plan).hexdigest()},
                            "probe_derive": None, "implement": None, "verify": None, "final_report": None}}

        def save(value):
            writer["write_state"](devlyn / "pipeline.state.json", value)

        names = ("adapter", "body", "metadata", "contract", "goal")
        save(state)
        prompt, output = render_worker(devlyn, "implement", "codex", 0)
        frames = split_frames(prompt, b"IMPLEMENT/1\n", names + ("findings",))
        metadata = json.loads(frames["metadata"])
        assert output == devlyn / "implement.prompt.0" and frames["contract"] == contract and frames["goal"] == b""
        assert frames["body"] == (SKILL / "references/phases/implement.md").read_bytes() and frames["findings"] == b""
        assert frames["adapter"] == project_adapter((SHARED / "adapters/codex.md").read_bytes())
        assert metadata["bindings"] == {"DEVLYN_SKILL_DIR": str(SKILL), "DEVLYN_SHARED_DIR": str(SHARED),
                                        "CODEX_MONITORED_PATH": str(SHARED / "codex-monitored.sh")}
        assert "exec" not in metadata and metadata["repair_of"] is None and render_worker(devlyn, "implement", "codex", 0)[0] == prompt

        # Phase-gated plans frame the current phase; a VERIFY repair frames the merged findings.
        phased = plan + b"## Execution phases\n### Phase 1 \xe2\x80\x94 a\n### Phase 2 \xe2\x80\x94 b\n"
        (devlyn / "plan.md").write_bytes(phased)
        gated = json.loads(json.dumps(state))
        gated["phases"]["plan"]["output_sha256"] = hashlib.sha256(phased).hexdigest()
        save(gated)
        assert json.loads(split_frames(render_worker(devlyn, "implement", "codex", 0)[0], b"IMPLEMENT/1\n",
                                       names + ("findings",))["metadata"])["exec"] == {"current": 1, "total": 2}
        repair = json.loads(json.dumps(gated))
        repair["phases"]["implement"] = {"started_at": stamp, "completed_at": stamp, "round": 0, "verdict": "PASS",
                                         "exec": {"total": 2, "current": 2, "statuses": ["PASS", "PASS"]}}
        repair["phases"]["verify"] = {"started_at": stamp, "completed_at": stamp, "round": 0, "verdict": "NEEDS_WORK",
                                      "merged": {"verdict": "NEEDS_WORK", "findings_file": ".devlyn/verify-merged.findings.jsonl"}}
        save(repair)
        merged = b'{"id":"F1","severity":"HIGH"}\n'
        (devlyn / "verify-merged.findings.jsonl").write_bytes(merged)
        repaired = split_frames(render_worker(devlyn, "implement", "codex", 1)[0], b"IMPLEMENT/1\n", names + ("findings",))
        assert repaired["findings"] == merged and json.loads(repaired["metadata"])["repair_of"] == "verify"
        assert json.loads(repaired["metadata"])["exec"] == {"current": 2, "total": 2}

        def refused(kind, value, phase="implement", engine="codex"):
            save(value)
            output_path = devlyn / ("implement.prompt.9" if phase == "implement" else "probe-derive.prompt.9")
            output_path.write_bytes(b"unchanged")
            try:
                prompt_bytes, target = render_worker(devlyn, phase, engine, 9)
                write_atomic(target, prompt_bytes)
            except SystemExit as exc:
                assert str(exc).startswith(f"BLOCKED:phase-input-invalid:{kind}:"), exc
            else:
                raise AssertionError(f"{kind} input accepted")
            assert output_path.read_bytes() == b"unchanged", kind

        for name in ("probe_derive", "implement", "verify"):
            still_open = json.loads(json.dumps(repair))
            still_open["phases"][name] = {"started_at": stamp, "completed_at": None, "round": 1, "verdict": None}
            refused("predecessor", still_open)
        # Unreadable worker inputs refuse in the same format (POSIX permissions; root reads anyway).
        merged_file = devlyn / "verify-merged.findings.jsonl"
        if os.name != "nt":
            merged_file.chmod(0)
            if not os.access(merged_file, os.R_OK):
                refused("findings", repair)
            merged_file.chmod(0o600)
            saved = SHARED, SKILL
            try:
                fake = work / "fake-skills"
                (fake / "_shared" / "adapters").mkdir(parents=True)
                (fake / "devlyn-resolve" / "references" / "phases").mkdir(parents=True)
                for script in saved[0].glob("*.py"):
                    (fake / "_shared" / script.name).symlink_to(script)
                for name in ("implement.md", "probe-derive.md"):
                    (fake / "devlyn-resolve/references/phases" / name).write_bytes(b"body")
                adapter_copy = fake / "_shared/adapters/codex.md"
                adapter_copy.write_bytes(b"# adapter")
                SHARED, SKILL = fake / "_shared", fake / "devlyn-resolve"
                adapter_copy.chmod(0)
                if not os.access(adapter_copy, os.R_OK):
                    refused("adapter", repair)
                adapter_copy.chmod(0o600)
                body_copy = fake / "devlyn-resolve/references/phases/implement.md"
                body_copy.chmod(0)
                if not os.access(body_copy, os.R_OK):
                    refused("body", repair)
                body_copy.chmod(0o600)
            finally:
                SHARED, SKILL = saved
        merged_file.unlink()
        refused("findings", repair)
        refused("adapter", gated, engine="nonexistent")
        open_plan = json.loads(json.dumps(gated)); open_plan["phases"]["plan"]["completed_at"] = None
        refused("plan", open_plan)
        (devlyn / "plan.md").write_bytes(phased + b"widened\n")
        refused("plan", gated)
        (devlyn / "plan.md").write_bytes(phased)
        tampered = json.loads(json.dumps(gated)); tampered["source"]["spec_sha256"] = "0" * 64
        refused("contract", tampered)
        unreadable = json.loads(json.dumps(gated)); unreadable["source"]["spec_path"] = "missing.md"
        refused("contract", unreadable, phase="probe_derive")
        refused("requirements", gated, phase="probe_derive")  # the requirement resolver needs UTF-8 text
        requirement = {"tag": "fixture_cleanup", "derived_from": "prints ok"}
        criteria = ("# C\r\n\n<!-- devlyn:verification -->\n## Verification\n\n- prints ok\n\n```json\n"
                    + json.dumps({"verification_commands": [{"cmd": "true"}], "required_risk_probe_requirements": [requirement]})
                    + "\n```\n").encode("utf-8")
        (devlyn / "criteria.generated.md").write_bytes(criteria)
        (devlyn / "goal.raw.txt").write_bytes(b"goal")
        generated = json.loads(json.dumps(gated))
        generated.update(mode="free-form", source={"type": "generated", "criteria_path": ".devlyn/criteria.generated.md",
                                                   "criteria_sha256": hashlib.sha256(criteria).hexdigest(),
                                                   "goal_path": ".devlyn/goal.raw.txt", "goal_sha256": "0" * 64})
        refused("goal", generated)
        generated["source"]["goal_sha256"] = hashlib.sha256(b"goal").hexdigest()
        save(generated)
        assert split_frames(render_worker(devlyn, "implement", "codex", 0)[0], b"IMPLEMENT/1\n",
                            names + ("findings",))["goal"] == b"goal"
        probe, probe_output = render_worker(devlyn, "probe_derive", "claude", 0)
        probe_frames = split_frames(probe, b"PROBE_DERIVE/1\n", names + ("requirements",))
        assert probe_output == devlyn / "probe-derive.prompt.0" and json.loads(probe_frames["requirements"]) == [requirement]
        assert probe_frames["contract"] == criteria and probe_frames["body"] == (SKILL / "references/phases/probe-derive.md").read_bytes()


def verify_self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="phase-prompt-render-verify-") as raw:
        work = pathlib.Path(raw).resolve()
        devlyn = work / ".devlyn"
        devlyn.mkdir()

        def git(*args):
            return subprocess.run(["git", "-c", "user.name=f", "-c", "user.email=f@example.com", *args], cwd=work,
                                  check=True, capture_output=True, text=True).stdout.strip()
        git("init", "-q")
        (work / ".gitignore").write_text(".devlyn/\n")
        (work / "spec.md").write_bytes(b"# Spec\n")  # hashed below: exact bytes on every platform
        (work / "app.py").write_text("a\n")
        git("add", ".")
        git("commit", "-qm", "base")
        base = git("rev-parse", "HEAD")
        (work / "app.py").write_text("b\n")
        git("commit", "-qam", "change")
        (devlyn / "plan.md").write_text('<!-- devlyn:authorized-surface -->\n## Files\n```json\n{"authorized_surface": ["app.py"]}\n```\n')
        (devlyn / "spec-verify.results.json").write_text('{"commands": [], "process_evidence": null}\n')
        state = {"run_id": "r", "mode": "spec", "base_ref": {"sha": base},
                 "source": {"type": "spec", "spec_path": "spec.md",
                            "spec_sha256": hashlib.sha256(b"# Spec\n").hexdigest()},
                 "phases": {"verify": {"round": 0, "started_at": "t"}}}
        snapshot = build_verify_snapshot(devlyn, state)
        assert b"diff --git a/app.py b/app.py" in snapshot and b"# Spec\n" in snapshot
        prompts = [render_verify(role, "claude", snapshot) for role in ("primary_judge", "pair_judge")]
        frames = [prompt_frames(prompt) for prompt in prompts]
        assert frames[0]["snapshot"] == frames[1]["snapshot"] == snapshot
        assert frames[0]["adapter"] == frames[1]["adapter"] and b"## Invocation" not in frames[0]["adapter"]
        assert frames[0]["rubric"] == verify_body() and frames[1]["role"] == b"pair_judge"
        for broken in (prompts[0] + b"x", prompts[0].replace(b"role 13", b"role 12", 1), b"VERIFY/2\n"):
            try:
                prompt_frames(broken)
            except ValueError:
                pass
            else:
                raise AssertionError("malformed VERIFY prompt framing accepted")

        def rejected(kind, mutate, undo=lambda: None):
            broken = json.loads(json.dumps(state))
            mutate(broken)
            try:
                build_verify_snapshot(devlyn, broken)
            except SystemExit as exc:
                assert str(exc).startswith(f"BLOCKED:verify-input-invalid:{kind}:"), exc
            else:
                raise AssertionError(f"{kind} input accepted")
            finally:
                undo()
        rejected("contract", lambda s: s["source"].update(spec_sha256="0" * 64))
        rejected("goal", lambda s: s["source"].update(type="generated", criteria_path="spec.md",
                                                       criteria_sha256=state["source"]["spec_sha256"],
                                                       goal_path="spec.md", goal_sha256="0" * 64))
        rejected("base", lambda s: s["base_ref"].update(sha="abc"))
        rejected("expected", lambda s: (work / "spec.expected.json").write_text("{"),
                 lambda: (work / "spec.expected.json").unlink())
        rejected("expected", lambda s: s["source"].update(expected_sha256="0" * 64))
        rejected("expected", lambda s: ((work / "spec.expected.json").write_bytes(b"{}"), s["source"].update(expected_sha256=None)),
                 lambda: (work / "spec.expected.json").unlink())
        rejected("diff", lambda s: (devlyn / "external-diff.patch").write_text(""),
                 lambda: (devlyn / "external-diff.patch").unlink())
        rejected("surface", lambda s: (devlyn / "plan.md").rename(devlyn / "plan.md.off"),
                 lambda: (devlyn / "plan.md.off").rename(devlyn / "plan.md"))
        rejected("mechanical", lambda s: (devlyn / "spec-verify.results.json").rename(devlyn / "results.off"),
                 lambda: (devlyn / "results.off").rename(devlyn / "spec-verify.results.json"))
        verify_only = {**state, "mode": "verify-only"}
        (devlyn / "plan.md").unlink()
        (devlyn / "external-diff.patch").write_text("diff --git a/x b/x\n")
        assert b"diff --git a/x b/x" in build_verify_snapshot(devlyn, verify_only)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", type=pathlib.Path)
    parser.add_argument("--canonical-body", type=pathlib.Path)
    parser.add_argument("--task-context", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--devlyn-dir", type=pathlib.Path)
    parser.add_argument("--phase", choices=sorted(WORKER_PHASES))
    parser.add_argument("--engine")
    parser.add_argument("--round", type=int)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    generic = (args.adapter, args.canonical_body, args.task_context, args.output)
    worker = (args.devlyn_dir, args.phase, args.engine, args.round)
    if args.self_test:
        if any(generic) or any(value is not None for value in worker):
            parser.error("render paths are not allowed with --self-test")
        return self_test()
    if any(value is not None for value in worker):
        if any(generic) or any(value is None for value in worker) or args.round < 0:
            parser.error("worker mode takes exactly --devlyn-dir, --phase, --engine and a non-negative --round")
        prompt, output = render_worker(args.devlyn_dir, args.phase, args.engine, args.round)
        print(write_atomic(output, prompt))
        return 0
    if not all((args.adapter, args.canonical_body, args.task_context, args.output)):
        parser.error(
            "--adapter, --canonical-body, --task-context, and --output are required"
        )
    print(render_prompt(args.adapter, args.canonical_body, args.task_context, args.output))
    return 0


if __name__ == "__main__":
    runpy.run_path(str(pathlib.Path(__file__).with_name("platform-support.py")))["configure_utf8"]()
    raise SystemExit(main())
