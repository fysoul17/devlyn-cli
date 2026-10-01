# J2 hidden oracle

Run each row in its own process from the implemented checkout root with `node --input-type=module`, using the public command's PATH assignment. Prepend:

```js
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
```

Only J2-O2 is the designated witness. All other rows must pass on both arms.

## J2-O1

Setup: Four registrations with default and alternate chains already compiled.

Action: Move `d` before `a`.

Expected result: Both newly obtained chains reflect the new order and the exact function objects survive.

```js
const { ruler, f } = makeRuler()
order(ruler)
order(ruler, 'probe')
assert.equal(ruler.moveBefore('d', 'a'), undefined)
assert.deepEqual(order(ruler), ['d', 'a', 'b', 'c'])
assert.deepEqual(order(ruler, 'probe'), ['d', 'a', 'c'])
assert.deepEqual(ruler.getRules(''), [f.d, f.a, f.b, f.c])
```

## J2-O2 — designated witness

Setup: The same four registrations and warm chains.

Action: Move `a` before nonadjacent later anchor `c`.

Expected result: The order is `[b, a, c, d]`, and the alternate order is `[a, c, d]`. The twin produces `[b, c, a, d]` in the default chain.

```js
const { ruler } = makeRuler()
order(ruler)
order(ruler, 'probe')
ruler.moveBefore('a', 'c')
assert.deepEqual(order(ruler), ['b', 'a', 'c', 'd'])
assert.deepEqual(order(ruler, 'probe'), ['a', 'c', 'd'])
```

## J2-O3

Setup: Disabled registration `c`, with both chains warmed.

Action: Move `c` before `a`, inspect chains, then enable `c`.

Expected result: The move does not enable it; re-enabling exposes it at the new position with its alternate membership intact.

```js
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
```

## J2-O4

Setup: Four registrations, including disabled `b`, and a snapshot of their states.

Action: Attempt no-op moves and moves with missing names.

Expected result: Order and enabled states remain equal; error messages select the first missing argument.

```js
const { ruler } = makeRuler()
ruler.disable('b')
const snapshot = () => ruler.__rules__.map(r => [r.name, r.enabled, r.fn, [...r.alt]])
const before = snapshot()
ruler.moveBefore('a', 'a')
ruler.moveBefore('a', 'b')
assert.throws(() => ruler.moveBefore('missing', 'other'), { message: 'Parser rule not found: missing' })
assert.throws(() => ruler.moveBefore('a', 'other'), { message: 'Parser rule not found: other' })
assert.deepEqual(snapshot(), before)
```

## J2-O5

Setup: Two core plugin rules after normal parsing, adding distinguishable text to the final inline token stream.

Action: Warm the parser, move the later plugin before the earlier plugin, and render again.

Expected result: Rendered text follows the new precedence.

```js
const md = markdownit()
for (const label of ['A', 'B']) {
  md.core.ruler.push(label, state => {
    const token = new state.Token('text', '', 0)
    token.content = label
    state.tokens.find(t => t.type === 'inline').children.push(token)
  })
}
assert.equal(md.render('x'), '<p>xAB</p>\n')
md.core.ruler.moveBefore('B', 'A')
assert.equal(md.render('x'), '<p>xBA</p>\n')
```

## J2-O6

Setup: Duplicate rule names, as allowed by existing registration methods.

Action: Move the first matching later registration before the first anchor, then disable that name.

Expected result: Only the first matching registration moves and existing first-match disabling still applies.

```js
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
```
