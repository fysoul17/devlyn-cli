#!/usr/bin/env bash
# codex-monitored.sh — run `codex exec` in a monitored shape that keeps the
# outer claude -p API stream from going silent during long Codex calls.
#
# WHY (iter-0009, post iter-0006/0007/0008):
#   • iter-0007 isolation proved a single foreground `codex exec` Bash dispatch
#     can starve the outer API stream of bytes during a 10+ min run; Anthropic's
#     byte-level idle watchdog fires (~300s) and kills the orchestrator.
#   • iter-0008 saw the orchestrator pick `codex exec ... 2>&1 | tail -200` from
#     its own pattern prior — `tail` on a pipe buffers until EOF, suppressing
#     ALL bytes. Same starvation, amplified.
#   • iter-0008 also documented codex 0.124.0 reads stdin as a `<stdin>` block
#     when the prompt is passed as an arg AND stdin is open; without
#     `< /dev/null` the call hangs indefinitely.
#
# WHAT THIS WRAPPER DOES:
#   1. Refuses to run if stdout is a pipe. Piping wrapper output to text tools
#      (tail/head/awk/sed/grep without --line-buffered) re-introduces the
#      iter-0008 starvation mechanism — the downstream tool buffers until EOF
#      and the outer claude -p byte-watchdog never sees bytes. Exits 64 with a
#      clear message so the orchestrator can self-correct on retry.
#      (Round 2 finding #1 fix: shim alone does not defeat `| tail`; the
#      wrapper must reject the pipe shape directly.)
#   2. Closes stdin (`< /dev/null`) — kills the codex 0.124.0 stdin hang.
#   3. Streams codex stdout to OUR stdout line-by-line — the orchestrator reads
#      stdout as the subagent reply (per `_shared/codex-config.md`) so we MUST
#      NOT swallow it (e.g. `tail -n 200`). codex stderr forwards to OUR stderr.
#   4. Emits a `[codex-monitored] heartbeat` line every CODEX_MONITORED_HEARTBEAT
#      seconds (default 30s) on STDERR while codex is alive. Heartbeat-on-stderr
#      keeps the orchestrator's combined-output stream non-silent without
#      polluting the codex-reply view of stdout.
#   5. Forwards SIGTERM/SIGINT from the outer watchdog to the codex child so a
#      timeout actually reaps codex (otherwise process group kill races with
#      backgrounded codex).
#   6. Preserves codex's exact exit code.
#
# USAGE:
#   bash codex-monitored.sh -C <repo> -s read-only -c model_reasoning_effort=xhigh "<prompt>"
#   bash codex-monitored.sh resume --last
#   (Args after the script name are passed verbatim to `codex exec`.)
#
# ENV OVERRIDES:
#   CODEX_MONITORED_HEARTBEAT      — heartbeat interval seconds (default 30).
#   CODEX_MONITORED_TIMEOUT_SEC    — optional hard timeout. When >0, kill the
#                                     codex process group and exit 124.
#   CODEX_BIN                      — real codex binary path. Default:
#                                     CODEX_REAL_BIN when set, else `codex`.
#                                     Set this when the shim has put us first
#                                     on PATH.
#   CODEX_MONITORED_ALLOW_PIPED    — set non-empty to skip the pipe-stdout
#                                     refusal. Reserved for tests; don't use
#                                     in skill prompts.

set -uo pipefail

# iter-0019 — solo_claude (L1) arm enforcement (defense in depth alongside
# scripts/codex-shim/codex). If this env is set, the wrapper refuses to invoke
# codex at all, regardless of how it was reached. Two enforcement points
# protect against the case where one is bypassed: the shim catches PATH-based
# resolution, and this wrapper catches direct-path invocations of
# codex-monitored.sh that don't go through the shim.
if [ -n "${CODEX_BLOCKED:-}" ]; then
  printf '[codex-monitored] CODEX_BLOCKED=%s — refusing codex invocation (solo_claude / L1 arm enforcement). args: %s\n' \
    "${CODEX_BLOCKED}" "$*" >&2
  exit 126
fi

HEARTBEAT_SEC="${CODEX_MONITORED_HEARTBEAT:-30}"
TIMEOUT_SEC="${CODEX_MONITORED_TIMEOUT_SEC:-0}"
CODEX_BIN="${CODEX_BIN:-${CODEX_REAL_BIN:-codex}}"
START=$(date +%s)
TIMEOUT_FLAG=""

# --- Pipe-stdout refusal (iter-0009 R2 finding #1) -------------------------
# `[ -p /dev/stdout ]` is the POSIX test for "is fd 1 a FIFO/pipe". Verified
# correct on macOS via lsof: distinguishes piped (`| cat`) from redirected
# (`> file`) and from claude-bash-tool capture (regular file). Without this
# refusal, `bash WRAPPER ... 2>&1 | tail -200` would buffer wrapper output —
# including the heartbeat on stderr after `2>&1` — until EOF, reproducing
# the iter-0008 byte-watchdog kill.
if [ -z "${CODEX_MONITORED_ALLOW_PIPED:-}" ] && [ -p /dev/stdout ]; then
  cat >&2 <<'EOF'
[codex-monitored] error: stdout is a pipe.

Piping the wrapper to tail/head/awk/sed/grep buffers wrapper output until EOF,
which starves the outer claude -p byte-watchdog (iter-0008 starvation mechanism)
and kills the run after ~300s with empty transcript.

Fix: invoke the wrapper directly so the bash tool captures its stdout. The
wrapper streams full Codex output and emits a heartbeat on stderr; you do NOT
need to truncate.

  WRONG: bash codex-monitored.sh ... 2>&1 | tail -200
  RIGHT: bash codex-monitored.sh ...

If you absolutely must filter, use a line-buffered tool (e.g. `grep --line-buffered`)
and set CODEX_MONITORED_ALLOW_PIPED=1 in the wrapper's environment.
EOF
  exit 64
fi

# --- Heartbeat + signal forwarding ----------------------------------------
heartbeat_loop() {
  local pid="$1"
  while kill -0 "$pid" 2>/dev/null; do
    sleep "$HEARTBEAT_SEC"
    if kill -0 "$pid" 2>/dev/null; then
      local elapsed=$(( $(date +%s) - START ))
      printf '[codex-monitored] heartbeat: elapsed=%ds\n' "$elapsed" >&2
    fi
  done
}

timeout_loop() {
  local pid="$1"
  local seconds="$2"
  local flag="$3"
  [ "$seconds" -gt 0 ] || return 0
  sleep "$seconds"
  if kill -0 "$pid" 2>/dev/null; then
    : > "$flag"
    printf '[codex-monitored] timeout: elapsed=%ds limit=%ds\n' \
      "$(( $(date +%s) - START ))" "$seconds" >&2
    kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
    sleep 5
    kill -KILL -- "-$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null || true
  fi
}

terminate_process_group() {
  local pgid="$1"
  local reason="$2"
  if ! kill -0 -- "-$pgid" 2>/dev/null; then
    return 0
  fi
  printf '[codex-monitored] reap: reason=%s pgid=%s\n' "$reason" "$pgid" >&2
  kill -TERM -- "-$pgid" 2>/dev/null || true
  local i
  for i in 1 2 3 4 5; do
    sleep 1
    if ! kill -0 -- "-$pgid" 2>/dev/null; then
      return 0
    fi
  done
  kill -KILL -- "-$pgid" 2>/dev/null || true
}

forward_signal() {
  local sig="$1"
  if [ -n "${CODEX_PID:-}" ] && kill -0 "$CODEX_PID" 2>/dev/null; then
    kill -"$sig" -- "-$CODEX_PID" 2>/dev/null || kill -"$sig" "$CODEX_PID" 2>/dev/null || true
  fi
  if [ -n "${HB_PID:-}" ] && kill -0 "$HB_PID" 2>/dev/null; then
    kill -TERM "$HB_PID" 2>/dev/null || true
  fi
  if [ -n "${WATCHDOG_PID:-}" ] && kill -0 "$WATCHDOG_PID" 2>/dev/null; then
    kill -TERM "$WATCHDOG_PID" 2>/dev/null || true
  fi
}

cleanup() {
  forward_signal TERM
  [ -z "$TIMEOUT_FLAG" ] || rm -f "$TIMEOUT_FLAG"
}

trap 'forward_signal TERM; exit 143' TERM
trap 'forward_signal INT; exit 130' INT
trap cleanup EXIT

printf '[codex-monitored] start: ts=%s heartbeat=%ds timeout=%ss bin=%s\n' \
  "$(date -u +%FT%TZ)" "$HEARTBEAT_SEC" "$TIMEOUT_SEC" "$CODEX_BIN" >&2

# Launch codex with stdin closed; output streams directly to OUR stdout/stderr.
set -m
"$CODEX_BIN" exec "$@" < /dev/null &
CODEX_PID=$!
set +m
printf '[codex-monitored] codex pid=%d\n' "$CODEX_PID" >&2

heartbeat_loop "$CODEX_PID" &
HB_PID=$!

if [ "$TIMEOUT_SEC" -gt 0 ]; then
  TIMEOUT_FLAG=$(mktemp "${TMPDIR:-/tmp}/codex-monitored-timeout.XXXXXX")
  rm -f "$TIMEOUT_FLAG"
  timeout_loop "$CODEX_PID" "$TIMEOUT_SEC" "$TIMEOUT_FLAG" &
  WATCHDOG_PID=$!
fi

wait "$CODEX_PID"
EXIT=$?
terminate_process_group "$CODEX_PID" "post-exit-descendants"

kill -TERM "$HB_PID" 2>/dev/null || true
wait "$HB_PID" 2>/dev/null || true
if [ -n "${WATCHDOG_PID:-}" ]; then
  kill -TERM "$WATCHDOG_PID" 2>/dev/null || true
  wait "$WATCHDOG_PID" 2>/dev/null || true
fi
if [ -n "$TIMEOUT_FLAG" ] && [ -f "$TIMEOUT_FLAG" ]; then
  EXIT=124
fi

printf '[codex-monitored] codex exited: code=%d elapsed=%ds\n' \
  "$EXIT" $(( $(date +%s) - START )) >&2
exit "$EXIT"
