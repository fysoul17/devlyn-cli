#!/bin/sh
# 0229 check (J2): spec.md req 2-3, [a,b,c] moveBefore('a','c') gives [b,a,c], and a disabled a (a, c in a warmed alternate chain) moved before c and re-enabled appears before c in the default ([b,a,c]) and alternate ([a,c]) chains. Exit 0 = clause holds.
set -eu
cd "$1"
node --input-type=module <<'EOF'
import Ruler from './src/ruler.ts'
const names = fns => fns.map(fn => fn()).join(',')

const plain = new Ruler()
for (const name of ['a', 'b', 'c']) plain.push(name, () => name)
plain.moveBefore('a', 'c')
const plainOrder = names(plain.getRules(''))

const ruler = new Ruler()
ruler.push('a', () => 'a', { alt: ['probe'] })
ruler.push('b', () => 'b')
ruler.push('c', () => 'c', { alt: ['probe'] })
ruler.disable('a')
ruler.getRules('')
ruler.getRules('probe')
ruler.moveBefore('a', 'c')
ruler.enable('a')
const def = names(ruler.getRules(''))
const alt = names(ruler.getRules('probe'))

console.log(JSON.stringify({ plainOrder, def, alt }))
process.exit(plainOrder === 'b,a,c' && def === 'b,a,c' && alt === 'a,c' ? 0 : 1)
EOF
