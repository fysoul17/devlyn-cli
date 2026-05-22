#!/usr/bin/env bash
# Cross-platform `timeout` wrapper for Lane B.
#
# macOS ships without GNU `timeout` by default. brew's coreutils provides
# `gtimeout`. This helper picks whichever is available and falls back to a
# Python subprocess (always present on macOS/Linux dev machines).
#
# Critical: the fallback must preserve the caller's stdin/stdout/stderr,
# because callers (judge-blind.sh) pipe a prompt into the wrapped command.
# Using a heredoc to feed Python code would hijack the wrapper's stdin
# and the inner command would see EOF immediately.
#
# Usage: _with-timeout.sh <seconds> <cmd> [args...]
set -euo pipefail

SECS="${1:?seconds required}"
shift

if command -v gtimeout >/dev/null 2>&1; then
  exec gtimeout "$SECS" "$@"
elif command -v timeout >/dev/null 2>&1; then
  exec timeout "$SECS" "$@"
fi

exec python3 -c "
import subprocess, sys
secs = int(sys.argv[1])
cmd = sys.argv[2:]
p = subprocess.Popen(cmd)
try:
    p.wait(secs)
except subprocess.TimeoutExpired:
    p.terminate()
    try:
        p.wait(5)
    except subprocess.TimeoutExpired:
        p.kill()
    sys.exit(124)
sys.exit(p.returncode)
" "$SECS" "$@"
