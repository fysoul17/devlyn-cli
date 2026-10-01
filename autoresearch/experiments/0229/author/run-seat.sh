#!/bin/bash
# 0229 isolated corpus seat (0227's, with the 0229 workspace root). usage: run-seat.sh <author|sol> <label> <cwd> <prompt-file> <sandbox>
# Fresh HOME/CODEX_HOME under env -i, pinned codex-cli 0.156.1, web search, apps/connectors, plugins,
# sub-agents, browser and computer use disabled; the stderr transcript is kept for the read scan.
set -u
role=$1; label=$2; cwd=$3; prompt=$4; sandbox=$5
W=/Users/Shared/devlyn-vr-0228-dev/screen-0229/private/workspaces
H=$W/homes/$role-$label
CODEX=/Users/Shared/devlyn-0225-codex-0.156.1/node_modules/.bin/codex
case $role in author) model=gpt-6-astra effort=ultra ;; sol) model=gpt-6-sol effort=xhigh ;; *) exit 64 ;; esac
mkdir -p "$H/.codex" "$W/out"
cp ~/.codex/auth.json "$H/.codex/auth.json"; chmod 600 "$H/.codex/auth.json"
cd "$cwd" || exit 66
env -i HOME="$H" CODEX_HOME="$H/.codex" CODEX_BIN="$CODEX" PATH=/Users/aipalm/.nvm/versions/node/v20.19.0/bin:/opt/homebrew/bin:/usr/bin:/bin \
  USER="$USER" LANG=en_US.UTF-8 TMPDIR="$TMPDIR" PYTHONDONTWRITEBYTECODE=1 \
  CODEX_MONITORED_ISOLATED=1 DEVLYN_CODEX_PROMPT_FILE="$prompt" \
  bash /Users/aipalm/.local/share/nx01/core-continuation-20260912/config/skills/_shared/codex-monitored.sh \
  -C "$cwd" --skip-git-repo-check -s "$sandbox" -m "$model" -c model_reasoning_effort="$effort" -c 'web_search="disabled"' \
  --disable apps --disable plugins --disable remote_plugin --disable multi_agent --disable browser_use --disable computer_use - \
  > "$W/out/$role-$label.out.md" 2> "$W/out/$role-$label.err"
rc=$?
rm -f "$H/.codex/auth.json"
echo "$role $label exit=$rc"
