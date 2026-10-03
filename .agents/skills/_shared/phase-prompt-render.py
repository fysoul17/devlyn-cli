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


def verify_body() -> bytes:
    skills = pathlib.Path(__file__).resolve().parent.parent
    bodies = [skills / name / "references" / "phases" / "verify.md"
              for name in ("devlyn-resolve",)]
    bodies = [path for path in bodies if path.is_file()]
    if len(bodies) != 1:
        raise SystemExit("BLOCKED:verify-input-invalid:rubric:verify.md is not uniquely installed")
    return bodies[0].read_bytes()


def build_verify_snapshot(devlyn: pathlib.Path, state: dict) -> bytes:
    """Derive the one input snapshot both VERIFY judges receive."""
    check = runpy.run_path(str(pathlib.Path(__file__).with_name("spec-verify-check.py")))
    work = devlyn.resolve().parent

    def invalid(kind: str, detail: str) -> SystemExit:
        return SystemExit(f"BLOCKED:verify-input-invalid:{kind}:{detail}")

    def hashed(kind: str, relative: object, recorded: object) -> bytes:
        if not isinstance(relative, str) or not relative or not isinstance(recorded, str) \
                or re.fullmatch(r"[0-9a-f]{64}", recorded) is None:
            raise invalid(kind, "state records no path and sha256")
        path = pathlib.Path(relative)
        path = path if path.is_absolute() else work / path
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise invalid(kind, f"{relative} is unreadable: {exc}") from exc
        if hashlib.sha256(raw).hexdigest() != recorded:
            raise invalid(kind, f"{relative} does not match its recorded sha256")
        return raw

    source = state.get("source") if isinstance(state.get("source"), dict) else {}
    generated = source.get("type") == "generated"
    if source.get("type") not in {"generated", "spec"}:
        raise invalid("contract", "state.source.type must be spec or generated")
    field = "criteria" if generated else "spec"
    contract = hashed("contract", source.get(field + "_path"), source.get(field + "_sha256"))
    goal = hashed("goal", source.get("goal_path"), source.get("goal_sha256")) if generated else b""
    expected = b""
    if not generated:
        spec_path = pathlib.Path(source["spec_path"])
        sibling = (spec_path if spec_path.is_absolute() else work / spec_path).with_name("spec.expected.json")
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


def validate_plan_context(task_context: pathlib.Path, content: bytes) -> None:
    if task_context.name != "plan.task-context":
        return
    working_directory = pathlib.Path.cwd()
    expected = (
        b"Working directory: "
        + os.fsencode(working_directory)
        + b"\nPlan output: "
        + os.fsencode(working_directory / ".devlyn" / "plan.md")
        + b"\n"
    )
    if not content.startswith(expected):
        raise SystemExit("error: invalid PLAN task-context header")


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
    projected_adapter = project_adapter(adapter_bytes)
    validate_plan_context(task_context, context_bytes)
    rendered = projected_adapter + body_bytes + context_bytes
    rendered = rendered.rstrip(b"\n")
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


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="phase-prompt-render-") as raw:
        root = pathlib.Path(raw)
        adapter = root / "adapter.md"
        body = root / "plan.md"
        context = root / "plan.task-context"
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

            invalid_contexts = (
                b"context-without-header",
                b"Working directory: relative\nPlan output: relative/.devlyn/plan.md\n",
                b"Working directory: /mismatch\nPlan output: /mismatch/.devlyn/plan.md\n",
            )
            for invalid_context in invalid_contexts:
                context.write_bytes(invalid_context)
                output.write_bytes(b"unchanged")
                try:
                    render_prompt(adapter, body, context, output)
                except SystemExit:
                    pass
                else:
                    raise AssertionError("invalid PLAN task-context header accepted")
                assert output.read_bytes() == b"unchanged"
        finally:
            os.chdir(original_directory)
    verify_self_test()
    print("SELFTEST PASS: projected exact bytes + PLAN context validation + VERIFY snapshot guards")
    return 0


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
        (work / "spec.md").write_text("# Spec\n")
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
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        if any((args.adapter, args.canonical_body, args.task_context, args.output)):
            parser.error("render paths are not allowed with --self-test")
        return self_test()
    if not all((args.adapter, args.canonical_body, args.task_context, args.output)):
        parser.error(
            "--adapter, --canonical-body, --task-context, and --output are required"
        )
    print(render_prompt(args.adapter, args.canonical_body, args.task_context, args.output))
    return 0


if __name__ == "__main__":
    runpy.run_path(str(pathlib.Path(__file__).with_name("platform-support.py")))["configure_utf8"]()
    raise SystemExit(main())
