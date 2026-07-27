#!/usr/bin/env python3
"""Deny pair-judge shell outside the probe anchor, with a model-readable reason.

Registered as a native grok `PreToolUse` hook. It fires at step 1 of the
authorization pipeline, before the permission rules and before the mode policy
whose auto-deny silently terminates the review at exit 0 (iter-0081).

The anchor is supplied via DEVLYN_PROBE_ANCHOR, derived by the orchestrator from
the same source as the --allow rule.

Measured (iter-0081 M-C6 v2, external isolation, admissible cell): Line A 6/6 —
the denial arrives as a model-visible tool_result, the judge re-routes to
read_file, the anchor still executes inside the grok process, EndTurn with zero
PermissionCancelled. Line A-chain 1/1 — `<anchor> && <write>` is denied
model-visibly, neither segment executes, and the judge then runs the bare anchor.
"""
import json
import os
import sys

REASON = (
    "DEVLYN-0081-HOOK-DENY: this shell command is outside the permitted probe "
    "anchor. Use the read_file tool for file reads. The only permitted shell "
    "command is the anchor named in your prompt, unchained."
)

SHELL_TOOLS = {"run_terminal_command", "run_terminal_cmd", "Bash"}

# A conservative, quote-OBLIVIOUS lexical veto — deliberately not a shell parser.
# It rejects these characters even inside quotes, over-denying rather than ever
# under-denying a chain. Adding quote-, escape-, or operator-aware exceptions is
# how this becomes a parser; that is a registered falsifier, not a polish.
FORBIDDEN = set(";&|`$()<>") | {"\n", "\r"}


def main():
    anchor = os.environ.get("DEVLYN_PROBE_ANCHOR", "")
    payload = json.load(sys.stdin)

    if payload.get("toolName") not in SHELL_TOOLS or not anchor:
        print(json.dumps({"decision": "allow"}))
        return

    # The anchor, or the anchor plus argv, and nothing that could start a second
    # command. A bare prefix rule would allow `<anchor> && <other>` — the vendor's
    # own documented footgun. Exact match would instead deny `<anchor> --n 5`,
    # mechanically destroying the "bounded input variations" that verify.md
    # requires of every engine. Both were rejected by both seats (iter-0081 v2).
    command = (payload.get("toolInput") or {}).get("command", "").strip()
    if command == anchor or (
        command.startswith(anchor + " ")
        and not any(ch in FORBIDDEN for ch in command)
    ):
        print(json.dumps({"decision": "allow"}))
        return

    print(json.dumps({"decision": "deny", "reason": REASON}))


if __name__ == "__main__":
    main()
