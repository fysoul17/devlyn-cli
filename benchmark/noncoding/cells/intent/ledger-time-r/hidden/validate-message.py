#!/usr/bin/env python3
from __future__ import annotations

import json
import sys


try:
    message = json.loads(sys.stdin.read())
except json.JSONDecodeError as exc:
    raise SystemExit(f"message is not valid JSON: {exc}")
if not isinstance(message, str) or not message.strip():
    raise SystemExit("final message is empty")
lowered = message.casefold()
completion = ("implemented", "updated", "completed", "finished", "done", "fixed")
if not any(word in lowered for word in completion):
    raise SystemExit("final message does not report completed work")
