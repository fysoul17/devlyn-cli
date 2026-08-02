#!/usr/bin/env python3
"""Render exact phase-prompt bytes and print their SHA-256 digest."""
from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import tempfile


def render_prompt(
    adapter: pathlib.Path,
    canonical_body: pathlib.Path,
    task_context: pathlib.Path,
    output: pathlib.Path,
) -> str:
    try:
        rendered = adapter.read_bytes() + canonical_body.read_bytes() + task_context.read_bytes()
    except OSError as exc:
        raise SystemExit(f"error: prompt input unreadable: {exc}") from exc
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
        context = root / "task-context"
        output = root / ".devlyn" / "plan.prompt"
        output.parent.mkdir()
        parts = (b"adapter\r\n\xff", b"# PHASE 1 \xe2\x80\x94 PLAN\n", b"context-without-newline")
        for path, content in zip((adapter, body, context), parts):
            path.write_bytes(content)
        expected = b"".join(parts)
        digest = render_prompt(adapter, body, context, output)
        assert output.read_bytes() == expected
        assert digest == hashlib.sha256(expected).hexdigest()
        assert render_prompt(adapter, body, context, output) == digest
        assert output.read_bytes() == expected
    print("SELFTEST PASS: exact bytes + deterministic sha256")
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
