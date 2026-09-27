#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import runpy
import subprocess
import sys

PLATFORM = runpy.run_path(Path(__file__).with_name("platform-support.py"))


def fail(message: str) -> int:
    sys.stderr.write(f"error: {message}\n")
    return 2


def main(argv: list[str]) -> int:
    if len(argv) < 4:
        return fail("usage: run-bounded.py <seconds> [--stdin-file <path> [--record-transport]] -- <cmd> [args...]")
    try:
        seconds = int(argv[1])
    except ValueError:
        return fail("seconds must be a positive integer")
    if seconds <= 0:
        return fail("seconds must be a positive integer")
    index, prompt, record_transport = 2, None, False
    if argv[index] == "--stdin-file":
        if len(argv) < 6:
            return fail("--stdin-file requires a path and command")
        prompt, index = argv[index + 1], index + 2
        if argv[index] == "--record-transport":
            record_transport, index = True, index + 1
    if argv[index] != "--" or not argv[index + 1:]:
        return fail("expected -- before command")
    stream = None
    try:
        command = argv[index + 1:]
        actual = PLATFORM["native_argv"](command)
        if record_transport:
            transport = runpy.run_path(Path(__file__).with_name("invocation-receipt.py"))
            stream, carrier, record = transport["prepare_transport"](prompt, command, actual, seconds)
            transport["write_transport"](carrier, record)
        elif prompt is not None:
            stream = PLATFORM["open_stdin"](prompt)
        code = PLATFORM["run_process"](actual, stream if stream is not None else subprocess.DEVNULL, seconds)
        if record_transport:
            transport["finish_transport"](carrier, code)
        return code
    except (OSError, ValueError) as exc:
        return fail(str(exc))
    finally:
        if stream is not None:
            stream.close()


if __name__ == "__main__":
    PLATFORM["configure_utf8"]()
    raise SystemExit(PLATFORM["system_exit_code"](main(sys.argv)))
