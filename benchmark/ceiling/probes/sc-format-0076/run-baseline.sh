#!/bin/bash
set -u
S="$(cd "$(dirname "$0")" && pwd)"
RB=/Users/aipalm/Documents/GitHub/devlyn-cli/config/skills/_shared/run-bounded.py
draw() {
  local task="$1" i="$2"
  local work="$S/base-work-$task-$i"
  rm -rf "$work"; cp -a "$S/$task-base" "$work"
  ( cd "$work" && python3 "$RB" 600 -- \
      claude -p --tools "Read,Grep,Glob,Edit,Write" --dangerously-skip-permissions \
        --model claude-sonnet-5 --output-format json --strict-mcp-config \
        --mcp-config '{"mcpServers":{}}' \
      < "$S/$task-prompt-old.txt" > "$S/base-draw-$task-$i.json" 2> "$S/base-draw-$task-$i.err" )
  echo "baseline $task-$i exit=$?"
}
for task in fs1 f23; do
  for i in 1 2 3 4 5 6; do
    draw "$task" "$i" &
    while [ "$(jobs -rp | wc -l)" -ge 4 ]; do sleep 5; done
  done
done
wait
echo "BASELINE DONE"
