#!/usr/bin/env bash
set -euo pipefail

: "${FINAL_MESSAGE_PATH:?FINAL_MESSAGE_PATH is required}"
: "${BASELINE_COMMIT_SHA:?BASELINE_COMMIT_SHA is required}"
: "${FIXTURE_HIDDEN_DIR:?FIXTURE_HIDDEN_DIR is required}"

git diff --quiet "$BASELINE_COMMIT_SHA" -- . \
  ':(exclude).devlyn/**' ':(exclude).claude/**' \
  ':(exclude)AGENTS.md' ':(exclude)CLAUDE.md'
if git ls-files --others --exclude-standard | python3 -c '
import sys
ignored = (".devlyn/", ".claude/")
paths = [line.strip() for line in sys.stdin if line.strip()]
product = [path for path in paths if path not in {"AGENTS.md", "CLAUDE.md"} and not path.startswith(ignored)]
raise SystemExit(1 if product else 0)
'; then
  :
else
  echo "product tree has untracked changes" >&2
  exit 1
fi
python3 - "$FINAL_MESSAGE_PATH" <<'PY' | "$FIXTURE_HIDDEN_DIR/validate-message.py"
import json
import sys
from pathlib import Path
print(json.dumps(Path(sys.argv[1]).read_text(encoding="utf-8")))
PY
