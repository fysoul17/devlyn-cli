#!/usr/bin/env python3
"""Render exact phase-prompt bytes and print their SHA-256 digest."""
from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import re
import tempfile


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
    print("SELFTEST PASS: projected exact bytes + PLAN context validation")
    return 0


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
    raise SystemExit(main())
