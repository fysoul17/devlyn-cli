#!/bin/sh
# 0229 check (J2): spec.md req 2, a rule moved from an earlier position before a later non-adjacent anchor lands immediately before it ([a,b,c] moveBefore('a','c') gives [b,a,c]). Exit 0 = clause holds.
set -eu
cd "$1"
node --input-type=module <<'EOF'
import Ruler from './src/ruler.ts'
const ruler = new Ruler()
for (const name of ['a', 'b', 'c']) ruler.push(name, () => name)
ruler.moveBefore('a', 'c')
const order = ruler.getRules('').map(fn => fn()).join(',')
console.log(order)
process.exit(order === 'b,a,c' ? 0 : 1)
EOF
