#!/bin/sh
# 0229 check (J1): spec.md req 1-2, on '`a`' a full-range lookahead at position 0 (posMax 3, end 3), then the same position at posMax 2 (end 1), then restoring posMax 3 examines the position again and ends at 3, each step equal to the uncached result. Exit 0 = clause holds.
set -eu
cd "$1"
node --input-type=module <<'EOF'
import markdownit from './src/index.ts'
const md = markdownit()
const src = '`a`'
const uncached = (posMax) => {
  const fresh = new md.inline.State(src, md, {}, [])
  fresh.posMax = posMax
  md.inline.skipToken(fresh)
  return fresh.pos
}
const state = new md.inline.State(src, md, {}, [])
const ends = []
for (const posMax of [3, 2, 3]) {
  state.pos = 0
  state.posMax = posMax
  md.inline.skipToken(state)
  ends.push(state.pos)
}
const expected = [3, 2, 3].map(uncached)
console.log(JSON.stringify({ ends, uncached: expected }))
process.exit(JSON.stringify(ends) === JSON.stringify(expected) && JSON.stringify(ends) === '[3,1,3]' ? 0 : 1)
EOF
