import { spawnSync } from 'node:child_process'
import { resolve } from 'node:path'

const tree = resolve(process.argv[2])
const prelude = `
import assert from 'node:assert/strict'
import Ruler from './src/ruler.ts'
import markdownit from './src/index.ts'

function makeRuler () {
  const ruler = new Ruler()
  const f = Object.fromEntries(['a', 'b', 'c', 'd'].map(name => [name, () => name]))
  for (const name of ['a', 'b', 'c', 'd']) {
    ruler.push(name, f[name], { alt: name === 'b' ? [] : ['probe'] })
  }
  return { ruler, f }
}
const order = (ruler, chain = '') => ruler.getRules(chain).map(fn => fn())
`

const rows = {
  'J2-O1': `
const { ruler, f } = makeRuler()
order(ruler)
order(ruler, 'probe')
assert.equal(ruler.moveBefore('d', 'a'), undefined)
assert.deepEqual(order(ruler), ['d', 'a', 'b', 'c'])
assert.deepEqual(order(ruler, 'probe'), ['d', 'a', 'c'])
assert.deepEqual(ruler.getRules(''), [f.d, f.a, f.b, f.c])
`,
  'J2-O2': `
const { ruler } = makeRuler()
order(ruler)
order(ruler, 'probe')
ruler.moveBefore('a', 'c')
assert.deepEqual(order(ruler), ['b', 'a', 'c', 'd'])
assert.deepEqual(order(ruler, 'probe'), ['a', 'c', 'd'])
`,
  'J2-O3': `
const { ruler, f } = makeRuler()
ruler.disable('c')
order(ruler)
order(ruler, 'probe')
ruler.moveBefore('c', 'a')
assert.deepEqual(order(ruler), ['a', 'b', 'd'])
assert.deepEqual(order(ruler, 'probe'), ['a', 'd'])
ruler.enable('c')
assert.deepEqual(ruler.getRules(''), [f.c, f.a, f.b, f.d])
assert.deepEqual(order(ruler, 'probe'), ['c', 'a', 'd'])
`,
  'J2-O4': `
const { ruler } = makeRuler()
ruler.disable('b')
const snapshot = () => ruler.__rules__.map(r => [r.name, r.enabled, r.fn, [...r.alt]])
const before = snapshot()
ruler.moveBefore('a', 'a')
ruler.moveBefore('a', 'b')
assert.throws(() => ruler.moveBefore('missing', 'other'), { message: 'Parser rule not found: missing' })
assert.throws(() => ruler.moveBefore('a', 'other'), { message: 'Parser rule not found: other' })
assert.deepEqual(snapshot(), before)
`,
  'J2-O5': `
const md = markdownit()
for (const label of ['A', 'B']) {
  md.core.ruler.push(label, state => {
    const token = new state.Token('text', '', 0)
    token.content = label
    state.tokens.find(t => t.type === 'inline').children.push(token)
  })
}
assert.equal(md.render('x'), '<p>xAB</p>\\n')
md.core.ruler.moveBefore('B', 'A')
assert.equal(md.render('x'), '<p>xBA</p>\\n')
`,
  'J2-O6': `
const ruler = new Ruler()
const a = () => 'a'
const first = () => 'first'
const second = () => 'second'
ruler.push('a', a)
ruler.push('dup', first)
ruler.push('dup', second)
ruler.moveBefore('dup', 'a')
assert.deepEqual(ruler.getRules(''), [first, a, second])
ruler.disable('dup')
assert.deepEqual(ruler.getRules(''), [a, second])
`
}

const result = {}
for (const [id, body] of Object.entries(rows)) {
  const source = `${prelude}\ntry {\n${body}\nprocess.stdout.write('true')\n} catch {\nprocess.stdout.write('false')\n}`
  const child = spawnSync('node', ['--input-type=module', '--eval', source], {
    cwd: tree,
    env: process.env,
    encoding: 'utf8'
  })
  if (child.error || child.status !== 0 || !['true', 'false'].includes(child.stdout)) {
    process.stderr.write(`Could not run ${id}: ${child.error?.message || child.stderr || child.stdout}\n`)
    process.exit(1)
  }
  result[id] = child.stdout === 'true'
}

process.stdout.write(`${JSON.stringify({ rows: result })}\n`)
