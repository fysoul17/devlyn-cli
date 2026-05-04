#!/usr/bin/env bash
# devlyn:reap — scan orphan processes by safe-to-kill category.
# Read-only. Never kills anything. Always exits 0 on success.
#
# Output format: one TSV line per category with
#   CATEGORY  COUNT  OLDEST_ETIME  PIDS  NOTE
# Followed by an "UNKNOWN_ORPHANS" line reporting non-system orphans we
# deliberately left out of the whitelist — these will NOT be touched by reap.sh.

set -u
LC_ALL=C
export LC_ALL

# PPID=1 user-owned processes. Column layout: PID  PPID  ETIME  COMMAND...
ME="$(id -un)"
SNAPSHOT="$(ps -eo pid=,ppid=,user=,etime=,command= 2>/dev/null | awk -v me="$ME" '$2==1 && $3==me')"

# -----------------------------------------------------------------------------
# Category matchers (grep -E patterns). These target processes that are KNOWN
# to leak from specific tools that do not reap their children on exit.
# Conservative by design — if unsure, leave it UNKNOWN.
# -----------------------------------------------------------------------------
match_telegram_bun()      { grep -E '/bun[^ ]* server\.ts( |$)'; }
match_superset_codex_sh() { grep -E '/bin/bash .*/\.superset/bin/codex( |$)'; }
match_superset_codex_tl() { grep -E 'tail .*superset-codex-session-.*\.jsonl'; }
match_workerd_dev()       { grep -E '@cloudflare/workerd-darwin-[^/]+/bin/workerd serve '; }

emit() {
  local name="$1"; shift
  local note="$1"; shift
  local lines; lines="$(cat)"
  local count; count="$(printf '%s\n' "$lines" | grep -c . || true)"
  if [ "${count:-0}" -eq 0 ]; then
    printf '%-24s\t0\t-\t-\t%s\n' "$name" "$note"
    return
  fi
  local pids oldest
  # ps column order is: pid ppid user etime command...
  pids="$(printf '%s\n' "$lines" | awk '{print $1}' | paste -sd, -)"
  oldest="$(printf '%s\n' "$lines" | awk '{print $4}' | sort -r | head -1)"
  printf '%-24s\t%s\t%s\t%s\t%s\n' "$name" "$count" "$oldest" "$pids" "$note"
}

printf 'CATEGORY                \tCOUNT\tOLDEST\tPIDS\tNOTE\n'

# Verify the bun server belongs to the telegram plugin before classifying it.
# cwd is the reliable signal; command line alone is ambiguous.
TELEGRAM_PIDS=""
if [ -n "$SNAPSHOT" ]; then
  BUN_CANDIDATES="$(printf '%s\n' "$SNAPSHOT" | match_telegram_bun | awk '{print $1}')"
  for pid in $BUN_CANDIDATES; do
    cwd="$(lsof -a -d cwd -p "$pid" 2>/dev/null | awk 'NR==2 {for(i=9;i<=NF;i++) printf "%s ", $i; print ""}')"
    case "$cwd" in
      *"/plugins/cache/claude-plugins-official/telegram/"*)
        TELEGRAM_PIDS="${TELEGRAM_PIDS}${pid}
" ;;
    esac
  done
fi

if [ -n "$TELEGRAM_PIDS" ]; then
  # Reconstruct rows for accurate ETIME/command display.
  printf '%s' "$TELEGRAM_PIDS" | grep -v '^$' | while read -r pid; do
    printf '%s\n' "$SNAPSHOT" | awk -v p="$pid" '$1==p'
  done | emit "telegram-bun"         "cwd=.../telegram/ plugin — safe"
else
  printf '' | emit "telegram-bun"    "cwd=.../telegram/ plugin — safe"
fi

printf '%s\n' "$SNAPSHOT" | match_superset_codex_sh | emit \
  "superset-codex-bash"     ".superset/bin/codex wrapper leak — safe"
printf '%s\n' "$SNAPSHOT" | match_superset_codex_tl | emit \
  "superset-codex-tail"     "superset-codex-session-*.jsonl tail — safe"
printf '%s\n' "$SNAPSHOT" | match_workerd_dev | emit \
  "workerd-dev"             "cloudflare dev server — opt-in (include=workerd)"

# -----------------------------------------------------------------------------
# UNKNOWN_ORPHANS: everything else that is PPID=1 and user-owned. Informational
# only. These will NOT be killed without a human explicitly extending the
# whitelist. macOS system helpers (launchd, /usr/libexec/**, Application
# bundles, Electron helpers, etc.) are filtered out — they're not orphans in
# the leak sense, they legitimately run under launchd.
# -----------------------------------------------------------------------------
SYSTEM_FILTER='(^|/)(launchd|aslmanager|cloudphotod|automountd|autofsd|usernotificationsd|voicebankingd|veraport)( |$)|^/System/|^/usr/libexec/|^/usr/sbin/|^/Library/Apple|^/Library/Developer/PrivateFrameworks/CoreSimulator|^/Library/PrivilegedHelperTools/|^/Applications/|CoreSimulator|raonsecure|TEK_|ChatGPTHelper|FigmaAgent|figma_agent|iniLINE|CrossEX|com\.apple\.|Superset Helper|Electron Framework|QuickLookUIService|SandboxHelper|MTLCompilerService|extensionkitservice|ssh-agent|Squirrel|app-server-broker\.mjs'

UNKNOWN="$(printf '%s\n' "$SNAPSHOT" \
  | grep -Ev "$SYSTEM_FILTER" \
  | awk '{printf "%s\t", $1; for(i=5;i<=NF;i++) printf "%s ", $i; print ""}')"

# Strip already-whitelisted categories from the UNKNOWN set so we don't
# double-count them.
WHITELIST_PIDS="$( {
  printf '%s' "$TELEGRAM_PIDS"
  printf '%s\n' "$SNAPSHOT" | match_superset_codex_sh | awk '{print $1}'
  printf '%s\n' "$SNAPSHOT" | match_superset_codex_tl | awk '{print $1}'
  printf '%s\n' "$SNAPSHOT" | match_workerd_dev | awk '{print $1}'
} | grep -v '^$' | sort -u)"

printf '\nUNKNOWN_ORPHANS (informational — NOT killed by reap.sh):\n'
if [ -z "$UNKNOWN" ]; then
  printf '  (none)\n'
else
  # awk can't take a multi-line string via -v (literal newlines are rejected),
  # so pass the whitelist as a temp file instead.
  WL_TMP="$(mktemp -t devlyn-reap-wl)"
  # shellcheck disable=SC2064
  trap "rm -f '$WL_TMP'" EXIT
  printf '%s\n' "$WHITELIST_PIDS" > "$WL_TMP"
  printf '%s\n' "$UNKNOWN" | awk -v wlf="$WL_TMP" '
    BEGIN {
      while ((getline line < wlf) > 0) if (line != "") wh[line]=1
      close(wlf)
    }
    { if (!($1 in wh)) print "  " $0 }
  '
fi
