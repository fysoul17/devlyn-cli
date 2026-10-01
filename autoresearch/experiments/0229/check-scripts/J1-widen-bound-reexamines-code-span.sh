#!/bin/sh
# 0229 check (J1): spec.md req 1-2, after lookahead at position 0 of '`a`' with posMax 2 caches end 1, resetting position 0 and widening posMax to 3 examines the position again and ends at 3, the uncached result. Exit 0 = clause holds.
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
state.posMax = 2
md.inline.skipToken(state)
const narrow = state.pos
state.pos = 0
state.posMax = 3
md.inline.skipToken(state)
const widened = state.pos
const expected = uncached(3)
console.log(JSON.stringify({ narrow, widened, uncached: expected }))
process.exit(narrow === 1 && widened === expected && widened === 3 ? 0 : 1)
EOF
