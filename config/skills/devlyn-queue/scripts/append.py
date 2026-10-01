#!/usr/bin/env python3
"""Append one normalized pending intent to the project queue."""

import argparse
import sys
from pathlib import Path


QUEUE_PATH = Path("docs/specs/queue.md")
HANDOFF_PATH = Path(".devlyn/queue-intent.txt")
MINIMAL_HEADER = b"# Intent Queue\n\n"


def append_intent(queue_path, intent):
    normalized = " ".join(intent.split())
    if not normalized:
        raise ValueError("intent must contain non-whitespace text")
    item = f"- [ ] {normalized}\n".encode("utf-8")

    if not queue_path.exists():
        queue_path.parent.mkdir(parents=True, exist_ok=True)
        queue_path.write_bytes(MINIMAL_HEADER + item)
        return

    with queue_path.open("rb") as queue:
        queue.seek(0, 2)
        size = queue.tell()
        if size:
            queue.seek(-1, 2)
            ends_with_newline = queue.read(1) == b"\n"
        else:
            ends_with_newline = True

    prefix = b"" if ends_with_newline else b"\n"
    with queue_path.open("ab") as queue:
        queue.write(prefix + item)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Append one pending intent at the physical end of docs/specs/queue.md."
    )
    parser.add_argument("handoff", type=Path, choices=(HANDOFF_PATH,))
    args = parser.parse_args(argv)
    try:
        try:
            intent = args.handoff.read_text(encoding="utf-8")
        finally:
            args.handoff.unlink(missing_ok=True)
        append_intent(QUEUE_PATH, intent)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"queue add failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
