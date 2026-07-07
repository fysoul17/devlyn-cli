#!/usr/bin/env python3
from __future__ import annotations

import os, signal, subprocess, sys


def fail(message: str) -> int:
    sys.stderr.write(f"error: {message}\n")
    return 2


def main(argv: list[str]) -> int:
    if len(argv) < 4:
        return fail("usage: run-bounded.py <seconds> -- <cmd> [args...]")
    try:
        seconds = int(argv[1])
    except ValueError:
        return fail("seconds must be a positive integer")
    if seconds <= 0:
        return fail("seconds must be a positive integer")
    if argv[2] != "--":
        return fail("expected -- before command")

    child = subprocess.Popen(argv[3:], start_new_session=True)
    try:
        return child.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            return 124
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait()
        return 124


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
