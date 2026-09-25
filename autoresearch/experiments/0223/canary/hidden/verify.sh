#!/usr/bin/env bash
# Smoke-only canary: records the model's answer; root compares it with the variant (never a matrix verdict).
python3 - "$1" <<'PY'
import json, pathlib, sys
result = pathlib.Path(sys.argv[1])
answer = json.loads((result / 'transcript.json').read_text() or '{}').get('result', '').strip()
print(json.dumps(dict(passed=True, answer=answer, instruction_sha256=json.loads((result / 'timing.json').read_text())['instruction_sha256'])))
PY
