# J4 hidden oracle

Run each row in a separate process from the implemented checkout root with `node --input-type=module`, using the public command's PATH assignment. Prepend:

```js
import assert from 'node:assert/strict'
import markdownit from './src/index.ts'
const retaining = () => {
  const md = markdownit()
  md.core.ruler.disable('strip_references')
  return md
}
const definitions = tokens => tokens.filter(t => t.type === 'reference_definition')
const plainMeta = token => ({ ...token.meta })
```

Only J4-O3 is the designated witness. All other rows must pass on both arms.

## J4-O1

Setup: A unique definition with mixed-case whitespace in its label, a destination needing normalization, and an entity in its title.

Action: Parse while retaining definitions, compare metadata with the environment, and render with retention on and off.

Expected result: Metadata contains decoded/normalized strings at the correct source map, has a null prototype, and does not change HTML or inline metadata shape.

```js
const md = retaining()
const env = {}
const src = '[Foo  Bar]: </a b> "A &amp; B"\n\n[x][foo bar] ![y][foo bar]\n'
const tokens = md.parse(src, env)
const [def] = definitions(tokens)
assert.equal(Object.getPrototypeOf(def.meta), null)
assert.deepEqual(plainMeta(def), { label: 'FOO BAR', href: '/a%20b', title: 'A & B' })
assert.deepEqual(def.map, [0, 1])
assert.equal(def.hidden, true)
assert.deepEqual(env.references['FOO BAR'], { href: '/a%20b', title: 'A & B' })
const inline = tokens.find(t => t.type === 'inline').children
for (const t of inline.filter(t => t.type === 'link_open' || t.type === 'image')) {
  assert.deepEqual({ ...t.meta }, { label: 'FOO BAR' })
}
assert.equal(md.render(src), markdownit().render(src))
assert.deepEqual(definitions(markdownit().parse(src, {})), [])
```

## J4-O2

Setup: A unique definition whose quoted title continues onto a second source line.

Action: Parse and render a reference link.

Expected result: The title is decoded with its newline preserved, and the map covers exactly the two definition lines.

```js
const md = retaining()
const env = {}
const src = '[x]: /u "one\ntwo &amp; three"\n\n[x]\n'
const tokens = md.parse(src, env)
const [def] = definitions(tokens)
assert.deepEqual(plainMeta(def), { label: 'X', href: '/u', title: 'one\ntwo & three' })
assert.deepEqual(def.map, [0, 2])
assert.deepEqual(env.references.X, { href: '/u', title: 'one\ntwo & three' })
assert.equal(md.renderer.render(tokens, md.options, env), '<p><a href="/u" title="one\ntwo &amp; three">x</a></p>\n')
```

## J4-O3 — designated witness

Setup: Two definitions on different source lines normalize to the same label and contain different destinations and titles.

Action: Retain both definition tokens, inspect each occurrence, and resolve a link through the environment.

Expected result: The environment and rendered link use the first definition, but each token carries the payload at its own source map. The twin copies the first payload into the second token.

```js
const md = retaining()
const env = {}
const src = '[Same]: /first "First"\n[same]: /second "Second"\n\n[go][same]\n'
const tokens = md.parse(src, env)
const defs = definitions(tokens)
assert.equal(defs.length, 2)
assert.deepEqual(defs.map(t => t.map), [[0, 1], [1, 2]])
assert.deepEqual(defs.map(plainMeta), [
  { label: 'SAME', href: '/first', title: 'First' },
  { label: 'SAME', href: '/second', title: 'Second' }
])
assert.deepEqual(env.references.SAME, { href: '/first', title: 'First' })
assert.equal(md.renderer.render(tokens, md.options, env), '<p><a href="/first" title="First">go</a></p>\n')
```

## J4-O4

Setup: A destination-only definition followed by a would-be title line containing trailing garbage.

Action: Retain and inspect tokens after title fallback.

Expected result: The accepted definition has an empty title and map `[0, 1]`; the rejected title line becomes ordinary paragraph content.

```js
const md = retaining()
const env = {}
const src = '[x]: /u\n"bad" trailing\n\n[x]\n'
const tokens = md.parse(src, env)
const [def] = definitions(tokens)
assert.deepEqual(plainMeta(def), { label: 'X', href: '/u', title: '' })
assert.deepEqual(def.map, [0, 1])
assert.deepEqual(env.references.X, { href: '/u', title: '' })
assert.equal(md.renderer.render(tokens, md.options, env), '<p>&quot;bad&quot; trailing</p>\n<p><a href="/u">x</a></p>\n')
```

## J4-O5

Setup: A retained unique definition, an unrelated pre-populated reference entry, and the resulting lookup record.

Action: Mutate the token metadata after parsing.

Expected result: The environment records are unchanged; metadata and lookup are separate objects and the definition stays hidden.

```js
const md = retaining()
const env = { references: { OTHER: { href: '/other', title: 'Other' } } }
const tokens = md.parse('[x]: /original "Original"\n', env)
const [def] = definitions(tokens)
assert.notEqual(def.meta, env.references.X)
def.meta.href = '/edited'
def.meta.title = 'Edited'
assert.deepEqual(env.references.X, { href: '/original', title: 'Original' })
assert.deepEqual(env.references.OTHER, { href: '/other', title: 'Other' })
assert.equal(md.renderer.render(tokens, md.options, env), '')
```
