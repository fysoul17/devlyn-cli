#!/usr/bin/env bash
# devlyn:reap — kill orphan processes from safe whitelist categories.
# Verifies PPID==1 and user-ownership AGAIN at kill time to avoid racing a
# legitimately-reparented process. Unknown orphans are never killed.
#
# Usage:
#   reap.sh                       # default categories, SIGTERM
#   reap.sh --force               # SIGKILL instead of SIGTERM
#   reap.sh --include workerd     # add workerd-dev to the default set
#   reap.sh --only telegram-bun   # restrict to a single category
#   reap.sh --dry-run             # print what WOULD be killed, kill nothing

set -u
LC_ALL=C
export LC_ALL

ME="$(id -un)"
SIGNAL="TERM"
DRY=0
INCLUDE=""
ONLY=""

while [ $# -gt 0 ]; do
  case "$1" in
    --force)     SIGNAL="KILL" ;;
    --dry-run)   DRY=1 ;;
    --include)   shift; INCLUDE="${INCLUDE},$1" ;;
    --only)      shift; ONLY="$1" ;;
    -h|--help)
      sed -n '2,14p' "$0"; exit 0 ;;
    *)
      printf 'unknown flag: %s\n' "$1" >&2; exit 2 ;;
  esac
  shift
done

DEFAULT_CATEGORIES="telegram-bun,superset-codex-bash,superset-codex-tail"
if [ -n "$ONLY" ]; then
  CATEGORIES="$ONLY"
else
  CATEGORIES="${DEFAULT_CATEGORIES}${INCLUDE}"
fi

SNAPSHOT="$(ps -eo pid=,ppid=,user=,etime=,command= 2>/dev/null | awk -v me="$ME" '$2==1 && $3==me')"

collect_pids() {
  local category="$1"
  case "$category" in
    telegram-bun)
      # cwd-verified — same logic as scan.sh
      printf '%s\n' "$SNAPSHOT" \
        | grep -E '/bun[^ ]* server\.ts( |$)' \
        | awk '{print $1}' \
        | while read -r pid; do
            cwd="$(lsof -a -d cwd -p "$pid" 2>/dev/null | awk 'NR==2 {for(i=9;i<=NF;i++) printf "%s ", $i; print ""}')"
            case "$cwd" in
              *"/plugins/cache/claude-plugins-official/telegram/"*) printf '%s\n' "$pid" ;;
            esac
          done
      ;;
    superset-codex-bash)
      printf '%s\n' "$SNAPSHOT" | grep -E '/bin/bash .*/\.superset/bin/codex( |$)' | awk '{print $1}' ;;
    superset-codex-tail)
      printf '%s\n' "$SNAPSHOT" | grep -E 'tail .*superset-codex-session-.*\.jsonl' | awk '{print $1}' ;;
    workerd)
      printf '%s\n' "$SNAPSHOT" | grep -E '@cloudflare/workerd-darwin-[^/]+/bin/workerd serve ' | awk '{print $1}' ;;
    *)
      printf 'unknown category: %s\n' "$category" >&2
      return 1 ;;
  esac
}

TOTAL_KILLED=0
TOTAL_SKIPPED=0

# Split the comma-separated category list without letting IFS leak into the
# inner loop that iterates newline-separated PIDs.
CATS_ARR=()
OLD_IFS="$IFS"
IFS=,
for c in $CATEGORIES; do
  [ -n "$c" ] && CATS_ARR+=("$c")
done
IFS="$OLD_IFS"

for cat in "${CATS_ARR[@]}"; do
  pids="$(collect_pids "$cat")" || continue
  if [ -z "$pids" ]; then
    printf '[%s] nothing to kill\n' "$cat"
    continue
  fi
  while IFS= read -r pid; do
    [ -z "$pid" ] && continue
    # Re-verify right before killing. Any of these mean "don't touch":
    #   - process already gone
    #   - PPID is no longer 1 (got adopted by a real parent — not our target)
    #   - owner changed (extremely unlikely but cheap to check)
    live_info="$(ps -o ppid=,user= -p "$pid" 2>/dev/null)"
    if [ -z "$live_info" ]; then
      printf '[%s] %s  skipped (already exited)\n' "$cat" "$pid"
      TOTAL_SKIPPED=$((TOTAL_SKIPPED+1))
      continue
    fi
    live_ppid="$(printf '%s' "$live_info" | awk '{print $1}')"
    live_user="$(printf '%s' "$live_info" | awk '{print $2}')"
    if [ "$live_ppid" != "1" ] || [ "$live_user" != "$ME" ]; then
      printf '[%s] %s  skipped (ppid=%s user=%s — no longer orphan)\n' "$cat" "$pid" "$live_ppid" "$live_user"
      TOTAL_SKIPPED=$((TOTAL_SKIPPED+1))
      continue
    fi
    if [ "$DRY" -eq 1 ]; then
      printf '[%s] %s  would SIG%s\n' "$cat" "$pid" "$SIGNAL"
    else
      if kill -s "$SIGNAL" "$pid" 2>/dev/null; then
        printf '[%s] %s  SIG%s sent\n' "$cat" "$pid" "$SIGNAL"
        TOTAL_KILLED=$((TOTAL_KILLED+1))
      else
        printf '[%s] %s  kill failed\n' "$cat" "$pid"
        TOTAL_SKIPPED=$((TOTAL_SKIPPED+1))
      fi
    fi
  done <<< "$pids"
done

if [ "$DRY" -eq 1 ]; then
  printf '\ndry-run complete.\n'
else
  printf '\ndone. killed=%s skipped=%s\n' "$TOTAL_KILLED" "$TOTAL_SKIPPED"
fi
