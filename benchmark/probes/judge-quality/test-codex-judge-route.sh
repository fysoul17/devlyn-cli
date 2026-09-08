#!/usr/bin/env bash
# Real fake-native regression for requested/observed Codex judge identity.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TMP_DIR="$(mktemp -d /tmp/codex-judge-route-test.XXXXXX)"
trap 'status=$?; if [ "$status" -eq 0 ]; then rm -rf "$TMP_DIR"; else echo "retained failure: $TMP_DIR" >&2; fi' EXIT
python3 - "$SCRIPT_DIR/run_judge_quality.py" "$TMP_DIR" <<'PY'
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
from unittest import mock

runner_path, root = map(Path, sys.argv[1:])
runner = runpy.run_path(runner_path)
fake = root / "fake-codex.py"
fake.write_text('''import json, os, pathlib, sys, time
args = sys.argv[1:]
assert args[0] == "exec", args
state = pathlib.Path(os.environ["FAKE_CODEX_STATE"])
count = int(state.read_text()) + 1 if state.exists() else 1
state.write_text(str(count))
with state.with_suffix(".argv.jsonl").open("a") as out:
    out.write(json.dumps(args) + "\\n")
def option(name):
    return args[args.index(name) + 1] if name in args else None
expected = os.environ.get("EXPECTED_MODEL") or None
assert option("-m") == expected, args
assert option("-s") == "read-only" and option("-c") == "model_reasoning_effort=xhigh", args
assert all(flag in args for flag in ("--ignore-user-config", "--ignore-rules", "--ephemeral", "--skip-git-repo-check")), args
assert args.count("--disable") == 2 and "codex_hooks" in args and "hooks" in args
mode = os.environ.get("FAKE_MODE", "ok")
model = expected or "gpt-native-default"
if mode == "wrong-model" or (mode == "drift" and count == 2): model = "gpt-other"
version = "changed" if mode == "version-drift" and count == 2 else "fake"
cwd = "/" if mode == "wrong-cwd" else option("-C")
sandbox = "workspace-write" if mode == "wrong-sandbox" else "read-only"
effort = "high" if mode == "wrong-effort" else "xhigh"
session = "" if mode == "missing-session" else "fake-" + str(count)
header = f"OpenAI Codex v{version}\\n--------\\nworkdir: {cwd}\\nmodel: {model}\\nsandbox: {sandbox}\\nreasoning effort: {effort}\\nsession id: {session}\\n--------\\nuser\\n" + args[-1] + "\\n"
if mode == "missing-header": header = ""
if mode == "duplicate-model": header = header.replace("model: ", "model: duplicate\\nmodel: ", 1)
if mode == "after-prompt": header = "\\nuser\\n" + header
if mode == "ignored-option": header = "Warning: model unsupported and ignored\\n" + header
sys.stderr.write(header); sys.stderr.flush()
if mode == "timeout": time.sleep(10)
if mode in ("retry", "drift", "version-drift") and count == 1:
    print("not json on first attempt")
else:
    print('{"findings":[]}')
sys.exit(17 if mode == "nonzero" else 0)
''')

def invoke(label, *, mode="ok", request="gpt-fake", fallback="gpt-fallback"):
    env = {k: v for k, v in os.environ.items() if k not in ("CODEX_MODEL", "OPENAI_MODEL")}
    if request is not None: env["CODEX_MODEL"] = request
    if fallback is not None: env["OPENAI_MODEL"] = fallback
    selected = request or fallback
    state = root / (label + ".calls")
    env.update(FAKE_CODEX_STATE=str(state), FAKE_MODE=mode, EXPECTED_MODEL=selected or "")
    output = root / label
    cmd = [sys.executable, str(runner_path), "--reps", "1", "--judges", "codex", "--run-id", label,
           "--results-dir", str(output), "--codex-command", f"{sys.executable} {fake}"]
    with (root / (label + ".stdout")).open("wb") as stdout, (root / (label + ".stderr")).open("wb") as stderr:
        result = subprocess.run(cmd, env=env, stdout=stdout, stderr=stderr, timeout=40)
    assert result.returncode == 0, (label, result.returncode)
    identity = json.loads((output / "codex/identity.json").read_text())
    records = json.loads((output / "summary.json").read_text())["codex"]
    assert len(records) == 12, label
    actual = [json.loads(line) for line in state.with_suffix(".argv.jsonl").read_text().splitlines()]
    attempts = [attempt for record in records for attempt in record["attempts"]]
    assert len(actual) == len(attempts)
    for args, attempt in zip(actual, attempts):
        saved = json.loads((output / "codex" / attempt["argv"]["path"]).read_text())
        assert saved[2:] == args, label
    return output, identity, records, cmd, env

for label, request, fallback, model in (
    ("precedence", "gpt-fake", "gpt-fallback", "gpt-fake"),
    ("fallback-request", None, "gpt-fallback", "gpt-fallback"),
    ("native-default", None, None, "gpt-native-default"),
):
    output, identity, records, cmd, env = invoke(label, request=request, fallback=fallback)
    assert identity["identity_validated"] is True and identity["model_id_or_alias"] == model, identity
    assert identity["cli_version"] == "codex-cli fake" and identity["model_requested"] == (request or fallback)
    assert all(len(record["attempts"]) == 1 and record["error"] is None for record in records)
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in output.rglob("*") if p.is_file()}
    repeat = subprocess.run(cmd, env=env, capture_output=True, timeout=10)
    assert repeat.returncode != 0 and b"fresh results directory" in repeat.stderr
    assert before == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in output.rglob("*") if p.is_file()}
    print("PASS", label, "actual argv/native header and no overwrite")

_, identity, records, _, _ = invoke("parse-retry", mode="retry")
assert identity["identity_validated"] is True and len(records[0]["attempts"]) == 2
assert records[0]["attempts"][0]["error"].startswith("parse_error:")
assert records[0]["parsed"] == {"findings": []}
print("PASS parse retry retains both successful native identities and raw streams")

for mode in ("wrong-model", "missing-header", "duplicate-model", "after-prompt", "wrong-cwd", "wrong-sandbox", "wrong-effort", "missing-session", "ignored-option", "nonzero", "drift", "version-drift"):
    _, identity, records, _, _ = invoke(mode, mode=mode)
    assert identity["identity_validated"] is False and identity["model_id_or_alias"] is None, (mode, identity)
    if mode in ("drift", "version-drift"):
        assert len(records[0]["attempts"]) == 2
    else:
        assert all(len(record["attempts"]) == 1 for record in records), mode
        prefix = "transport_error:" if mode == "nonzero" else "identity_error:"
        assert all(record["error"].startswith(prefix) for record in records), mode
    if mode == "nonzero":
        assert records[0]["attempts"][0]["exit_code"] == 17
        assert records[0]["attempts"][0]["native"]["model"] == "gpt-fake"
    print("PASS rejection", mode)

# Both preflights precede even an earlier judge in a mixed request.
fakebin = root / "fakebin"; fakebin.mkdir()
claude = fakebin / "claude"
claude.write_text('#!/bin/sh\nprintf "called\\n" >> "$FAKE_ANY_CALL"\nprintf \'{"findings":[]}\\n\'\n')
claude.chmod(0o755)
for label, request, fallback, occupied, message in (
    ("blank-primary", " \t", "gpt-fallback", False, "whitespace-only Codex model"),
    ("blank-fallback", None, "\t\n", False, "whitespace-only Codex model"),
    ("occupied-mixed", "gpt-fake", None, True, "fresh results directory"),
):
    output = root / label
    if occupied:
        (output / "codex").mkdir(parents=True)
        (output / "codex/old-result.json").write_bytes(b"preserve old result\n")
    env = {k: v for k, v in os.environ.items() if k not in ("CODEX_MODEL", "OPENAI_MODEL")}
    if request is not None: env["CODEX_MODEL"] = request
    if fallback is not None: env["OPENAI_MODEL"] = fallback
    any_call = root / (label + ".claude-calls")
    codex_call = root / (label + ".codex-calls")
    env.update(PATH=str(fakebin) + os.pathsep + os.environ["PATH"], FAKE_ANY_CALL=str(any_call),
               FAKE_CODEX_STATE=str(codex_call), EXPECTED_MODEL=request or fallback or "")
    cmd = [sys.executable, str(runner_path), "--reps", "1", "--judges", "sonnet,codex", "--run-id", label,
           "--results-dir", str(output), "--codex-command", f"{sys.executable} {fake}"]
    result = subprocess.run(cmd, env=env, capture_output=True, timeout=40)
    (root / (label + ".stdout")).write_bytes(result.stdout)
    (root / (label + ".stderr")).write_bytes(result.stderr)
    assert result.returncode != 0 and message.encode() in result.stderr, label
    assert not any_call.exists() and not codex_call.exists(), label
    assert not (output / "sonnet").exists() and not (output / "summary.json").exists()
    if occupied:
        assert (output / "codex/old-result.json").read_bytes() == b"preserve old result\n"
    print("PASS zero dispatch", label)

# Shorten only the test wait around a real child, preserving the 300s call.
real_popen = subprocess.Popen
waits = []
class ShortWait(real_popen):
    def wait(self, timeout=None):
        waits.append(timeout)
        return super().wait(timeout=0.2 if timeout == 300 else timeout)

work = root / "timeout-work"; work.mkdir()
with mock.patch.dict(os.environ, {"FAKE_MODE": "timeout", "FAKE_CODEX_STATE": str(root / "timeout.calls"), "EXPECTED_MODEL": "gpt-fake"}), mock.patch.object(subprocess, "Popen", ShortWait):
    parsed, error, attempt = runner["call_codex"]("review\n", work, [sys.executable, str(fake)], work / "case-rep1-attempt1.stdout.txt", work / "case-rep1-attempt1.stderr.txt", "gpt-fake")
assert waits[0] == 300 and parsed is None and error == "transport_error: timeout"
assert attempt["exit_code"] != 0 and attempt["identity_error"] is not None
assert attempt["native"]["model"] == "gpt-fake"
print("PASS real child timeout, nonzero reap, raw/header retained; production bound remains 300s")
PY

echo "PASS test-codex-judge-route"
