#!/usr/bin/env python3
"""Append one normalized pending intent to the project queue."""

import argparse
import os
import re
import sys
from contextlib import contextmanager
from pathlib import Path


QUEUE_PATH = Path("docs/specs/queue.md")
LOCK_PATH = Path(".devlyn/queue.lock")
# Each `add` writes its own handoff file, so two adds never consume each other's intent.
HANDOFF = re.compile(r"\.devlyn/queue-intent(-[A-Za-z0-9._-]+)?\.txt")
MINIMAL_HEADER = b"# Intent Queue\n\n"


@contextmanager
def queue_lock():
    """One writer at a time across processes, from creating the queue to the append."""
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(LOCK_PATH, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
    finally:
        os.close(fd)


def append_intent(queue_path, intent):
    normalized = " ".join(intent.split())
    if not normalized:
        raise ValueError("intent must contain non-whitespace text")
    item = f"- [ ] {normalized}\n".encode("utf-8")

    with queue_lock():
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
    parser.add_argument("handoff", type=Path, help=".devlyn/queue-intent-<unique>.txt, relative to the project root")
    args = parser.parse_args(argv)
    if not HANDOFF.fullmatch(args.handoff.as_posix()):
        parser.error(f"handoff must be .devlyn/queue-intent-<unique>.txt: {args.handoff}")
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
