#!/bin/bash
# iter-0076 Stage A gate (iii): sonnet SC format probe — 6 draws x 2 real prompts
set -u
S="$(cd "$(dirname "$0")" && pwd)"
RB=/Users/aipalm/Documents/GitHub/devlyn-cli/config/skills/_shared/run-bounded.py
draw() {
  local task="$1" i="$2"
  local work="$S/work-$task-$i"
  rm -rf "$work"
  cp -a "$S/$task-base" "$work"
  ( cd "$work" && python3 "$RB" 600 -- \
      claude -p --tools "Read,Grep,Glob,Edit,Write" --dangerously-skip-permissions \
        --model claude-sonnet-5 --output-format json --strict-mcp-config \
        --mcp-config '{"mcpServers":{}}' \
      < "$S/$task-prompt-mre.txt" > "$S/draw-$task-$i.json" 2> "$S/draw-$task-$i.err" )
  echo "draw $task-$i exit=$?"
}
pids=()
for task in fs1 f23; do
  for i in 1 2 3 4 5 6; do
    draw "$task" "$i" &
    pids+=($!)
    # cap concurrency at 4
    while [ "$(jobs -rp | wc -l)" -ge 4 ]; do sleep 5; done
  done
done
wait
echo "ALL DRAWS DONE"
