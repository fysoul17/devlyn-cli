#!/usr/bin/env python3
"""Line C — deterministic unit matrix for the anchor guard (iter-0081 v2).

Necessary, never sufficient: it proves the local decision only. Hook loading,
the deny reason reaching the model, and turn continuation are vendor-boundary
facts that only the live cell can establish.
"""
import json
import pathlib
import subprocess
import sys

GUARD = pathlib.Path(__file__).with_name("pretooluse-anchor-guard.py")
ANCHOR = "python3 /X/probe.py"

CASES = [
    (ANCHOR, "allow"),
    (f"  {ANCHOR}  ", "allow"),
    (f"{ANCHOR} --n 5", "allow"),
    (f"{ANCHOR} && echo pwned", "deny"),
    (f"{ANCHOR} || echo x", "deny"),
    (f"{ANCHOR}; rm -rf /", "deny"),
    (f"{ANCHOR} | tee out", "deny"),
    (f"{ANCHOR} > out.txt", "deny"),
    (f"{ANCHOR} &", "deny"),
    (f"{ANCHOR} $(evil)", "deny"),
    (f"{ANCHOR} `evil`", "deny"),
    (f"{ANCHOR} --arg 'a|b'", "deny"),          # quote-oblivious, on purpose
    (f"{ANCHOR}\nrm -rf /", "deny"),
    ('python3 -c "print(1)"', "deny"),
    ("python3 /X/probe.pyEXTRA", "deny"),        # no word boundary → not the anchor
]


def decide(command, tool="run_terminal_command"):
    payload = {"toolName": tool, "toolInput": {"command": command}}
    out = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={"DEVLYN_PROBE_ANCHOR": ANCHOR, "PATH": "/usr/bin:/bin"},
    )
    return json.loads(out.stdout)["decision"]


def main():
    failures = []
    for command, want in CASES:
        got = decide(command)
        if got != want:
            failures.append(f"  {command!r}: want {want}, got {got}")
    if decide("anything", tool="read_file") != "allow":
        failures.append("  non-shell tool must pass through")
    if failures:
        print("anchor-guard FAIL:\n" + "\n".join(failures))
        raise SystemExit(1)
    print(f"anchor-guard self-test ✓ ({len(CASES) + 1} cases)")


if __name__ == "__main__":
    main()
