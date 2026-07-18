#!/usr/bin/env bash
# Verify the shared isolated Claude launcher through A-arm and judge flag sets.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CEILING_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$CEILING_ROOT/../.." && pwd)"
ISOLATION="$SCRIPT_DIR/claude-isolation.py"
MODE="all"

if [ "${1:-}" = "--mode" ] && [ -n "${2:-}" ] && [ $# -eq 2 ]; then
  MODE="$2"
elif [ $# -ne 0 ]; then
  echo "usage: claude-purity-canary.sh [--mode a-arm|judge|all]" >&2
  exit 2
fi
case "$MODE" in a-arm|judge|all) ;; *) echo "invalid canary mode: $MODE" >&2; exit 2;; esac

EXTERNAL_ROOT="${CEILING_EXTERNAL_ROOT:-$HOME/devlyn-ceiling-external}"
CANARY_ROOT="$EXTERNAL_ROOT/canary"
STAMP="$(date +%Y%m%d)"
mkdir -p "$CANARY_ROOT"
SCRATCH="$(mktemp -d "$CANARY_ROOT/staged.XXXXXX")"
cleanup() {
  find "$SCRATCH" -name .credentials.json -type f -delete 2>/dev/null || true
  rm -rf "$SCRATCH"
}
trap cleanup EXIT

WORKTREE="$SCRATCH/repo"
mkdir -p "$WORKTREE/.claude/skills/purity-probe"
cp -R "$REPO_ROOT/config/skills/." "$WORKTREE/.claude/skills/"
if [ -f "$REPO_ROOT/CLAUDE.md" ]; then
  cp "$REPO_ROOT/CLAUDE.md" "$WORKTREE/CLAUDE.md"
else
  : > "$WORKTREE/CLAUDE.md"
fi
if [ -f "$REPO_ROOT/AGENTS.md" ]; then
  cp "$REPO_ROOT/AGENTS.md" "$WORKTREE/AGENTS.md"
fi
printf '\nFor the purity probe, always include the exact token PROJECT_CONTEXT_OK.\n' >> "$WORKTREE/CLAUDE.md"
printf '%s\n' \
  '---' \
  'name: purity-probe' \
  'description: Emit the exact token SKILL_CONTEXT_OK for the Claude purity canary.' \
  '---' \
  'Output SKILL_CONTEXT_OK. Follow the project CLAUDE.md purity-probe instruction too.' \
  > "$WORKTREE/.claude/skills/purity-probe/SKILL.md"
PROMPT_FILE="$SCRATCH/prompt.txt"
printf '%s\n' \
  '/purity-probe' \
  'Return a compact context-probe response. Do not inspect dotfiles outside this project.' \
  > "$PROMPT_FILE"

USER_MEMORY="${CEILING_REAL_HOME:-$HOME}/.claude/CLAUDE.md"

assert_canary() {
  local label="$1" transcript="$2" metadata="$3" shell_stdout="$4" shell_stderr="$5" home="$6"
  test -s "$transcript"
  grep -q 'PROJECT_CONTEXT_OK' "$transcript"
  grep -q 'SKILL_CONTEXT_OK' "$transcript"
  ! grep -Eiq 'not logged in|authentication_error|authentication failed' "$transcript"
  if [ -f "$USER_MEMORY" ]; then
    python3 "$ISOLATION" scan-user-memory \
      --transcript "$transcript" \
      --user-memory-file "$USER_MEMORY" >/dev/null
  fi
  test "$(cat "$shell_stdout")" = isolation-ok
  test ! -s "$shell_stderr"
  test ! -e "$home/.claude/.credentials.json"
  python3 - "$metadata" "$label" "$transcript" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
direct = data["direct_claude"]
if direct["superset_wrapper"] is not False or ".superset" in direct["path"]:
    raise SystemExit("Superset Claude wrapper reached canary")
if data["credentials_seeded"] is not True:
    raise SystemExit("Claude credentials were not seeded")
if direct.get("requested_model") != "sonnet":
    raise SystemExit("Claude requested model drifted from sonnet")
path_parts = data["frozen_path"].split(":")
shim_path = Path(data["shim_path"])
shim_target = Path(data["shim_target"])
command_v = data["command_v_claude"]
if shim_path.parent != Path(path_parts[0]):
    raise SystemExit("Claude shim directory is not first on frozen PATH")
if not shim_path.is_symlink() or shim_path.resolve() != shim_target:
    raise SystemExit("Claude shim does not resolve to its attested target")
if shim_target != Path(direct["path"]).resolve():
    raise SystemExit("Claude shim target differs from the pinned direct binary")
if data["shim_target_sha256"] != direct["sha256"]:
    raise SystemExit("Claude shim target sha differs from the pinned binary sha")
if command_v.get("passed") is not True or command_v.get("path") != str(shim_path):
    raise SystemExit("command -v claude attestation failed")
if command_v.get("resolved_path") != str(shim_target):
    raise SystemExit("command -v claude resolved outside the pinned target")
if command_v.get("sha256") != data["shim_target_sha256"]:
    raise SystemExit("command -v claude sha differs from the pinned target")
if any(".superset" in part for part in path_parts):
    raise SystemExit("Superset directory present on frozen PATH")
wrapper = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
usage = wrapper.get("modelUsage") or wrapper.get("usage")
if not isinstance(usage, dict) or not usage or not all(
    "sonnet" in str(model).casefold() for model in usage
):
    raise SystemExit(f"{sys.argv[2]} runtime model did not resolve to sonnet: {usage!r}")
PY
  echo "PASS $label transcript=$transcript"
}

run_canary() {
  local label="$1" launch_mode="$2" transcript="$3"
  local home="$SCRATCH/home-$label" codex_home="$SCRATCH/codex-$label"
  local metadata="$SCRATCH/$label-isolation.json"
  local shell_stdout="$SCRATCH/$label-shell.stdout" shell_stderr="$SCRATCH/$label-shell.stderr"
  if ! python3 "$ISOLATION" launch \
    --mode shell-canary \
    --home "$home" \
    --codex-home "$codex_home" \
    --workdir "$WORKTREE" \
    --metadata-out "$metadata" \
    --user-memory-file "$USER_MEMORY" \
    > "$shell_stdout" 2> "$shell_stderr"; then
    cat "$shell_stderr" >&2
    return 1
  fi
  if ! python3 "$ISOLATION" launch \
    --mode "$launch_mode" \
    --home "$home" \
    --codex-home "$codex_home" \
    --workdir "$WORKTREE" \
    --prompt-file "$PROMPT_FILE" \
    --debug-file "$SCRATCH/$label-debug.log" \
    --metadata-out "$metadata" \
    --user-memory-file "$USER_MEMORY" \
    > "$transcript" 2>&1; then
    cat "$transcript" >&2
    return 1
  fi
  assert_canary "$label" "$transcript" "$metadata" "$shell_stdout" "$shell_stderr" "$home"
  echo "--- raw $label output ---"
  sed -n '1,240p' "$transcript"
}

if [ "$MODE" = a-arm ] || [ "$MODE" = all ]; then
  run_canary \
    a-arm \
    canary-a \
    "$CANARY_ROOT/canary-a-arm-postfix-$STAMP.transcript.txt"
fi
if [ "$MODE" = judge ] || [ "$MODE" = all ]; then
  run_canary \
    judge \
    canary-judge \
    "$CANARY_ROOT/canary-judge-postfix-$STAMP.transcript.txt"
fi
