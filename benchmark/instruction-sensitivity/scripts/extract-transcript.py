#!/usr/bin/env python3
"""
Lane B transcript extractor.

Reads raw output from `claude -p --output-format json` (or stream-json fallback)
and writes `transcript.txt` containing the first assistant turn and the last
assistant turn — both are load-bearing for the clarification / pushback /
tradeoff axes (tail-only truncation would lose the first-turn signal).

Output transcript layout:
  [FIRST_TURN]
  <text>

  [LAST_TURN]
  <text>

`--out-json` emits diagnostics (turn count, character counts) — not consumed by
the judge.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MAX_TURN_CHARS = 4096


def extract_turns(raw: str) -> list[str]:
    raw = raw.strip()
    if not raw:
        return []

    # Mode 1: claude -p --output-format json — single JSON object with `result` string.
    try:
        obj = json.loads(raw)
    except Exception:
        obj = None

    if isinstance(obj, dict) and isinstance(obj.get("result"), str):
        text = obj["result"].strip()
        return [text] if text else []

    # Mode 2: claude -p --output-format stream-json — JSONL of events.
    turns: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except Exception:
            continue
        if evt.get("type") == "assistant":
            msg = evt.get("message", {}) or {}
            content = msg.get("content", []) or []
            text = "".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ).strip()
            if text:
                turns.append(text)
    if turns:
        return turns

    # Mode 3: plain text fallback.
    return [raw]


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    keep = limit // 2 - 32
    return text[:keep] + "\n... [truncated] ...\n" + text[-keep:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--in", dest="inp", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--out-json", required=True, type=Path)
    args = parser.parse_args()

    raw = args.inp.read_text(encoding="utf-8", errors="replace") if args.inp.exists() else ""
    turns = extract_turns(raw)

    first_turn = truncate(turns[0], MAX_TURN_CHARS) if turns else ""
    last_turn = truncate(turns[-1], MAX_TURN_CHARS) if turns else ""

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        f"[FIRST_TURN]\n{first_turn}\n\n[LAST_TURN]\n{last_turn}\n",
        encoding="utf-8",
    )
    args.out_json.write_text(
        json.dumps(
            {
                "turn_count": len(turns),
                "first_turn_chars": len(first_turn),
                "last_turn_chars": len(last_turn),
                "first_truncated": len(turns[0]) > MAX_TURN_CHARS if turns else False,
                "last_truncated": len(turns[-1]) > MAX_TURN_CHARS if turns else False,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"extract-transcript: turns={len(turns)} "
        f"first={len(first_turn)}ch last={len(last_turn)}ch",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
