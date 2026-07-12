#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys


try:
    message = json.loads(sys.stdin.read())
except json.JSONDecodeError as exc:
    raise SystemExit(f"message is not valid JSON: {exc}")
if not isinstance(message, str) or not message.strip():
    raise SystemExit("final message is empty")
text = re.sub(r"[\s\-‐‑‒–—]+", " ", message.casefold()).strip()
utc = re.search(r"\b(?:utc|z)\b", text)
source_offset = re.search(r"\b(?:(?:source|original)\s+)?offset\b", text)
decision = "?" in message or any(
    phrase in text
    for phrase in ("please choose", "which representation", "need a decision", "can you confirm", "tell me whether", "should we")
)
if not utc or not source_offset:
    raise SystemExit("message must name both UTC/Z normalization and source-offset preservation")
if not decision:
    raise SystemExit("message must request the unresolved decision")
