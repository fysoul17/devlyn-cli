# J3 hidden oracle

Run each row independently with `node --input-type=module` from the implemented checkout root, using the public command's PATH assignment. Prepend:

```js
import assert from 'node:assert/strict'
import markdownit from './src/index.ts'
const managers = md => [md.core.ruler, md.block.ruler, md.inline.ruler, md.inline.ruler2]
const flags = md => managers(md).map(r => r.__rules__.map(x => [x.name, x.enabled]))
const chains = md => [
  ...managers(md).map(r => r.getRules('').slice()),
  md.block.ruler.getRules('paragraph').slice(),
  md.block.ruler.getRules('reference').slice()
]
```

Only J3-O3 is the designated witness. All other rows must pass on both arms. The state snapshots check semantics, not private cache-object identity.

## J3-O1

Setup: A default parser, rendered inline code and an entity, with warmed rule chains.

Action: Reject disabling known primary-parser names plus an unknown name; then disable the known names successfully.

Expected result: Rejection preserves flags, function sequences, and HTML. The later successful call returns the instance and changes rendering.

```js
const md = markdownit()
const src = '`x` &amp;'
const html = md.renderInline(src)
assert.equal(html, '<code>x</code> &amp;')
const beforeFlags = flags(md)
const beforeChains = chains(md)
assert.throws(() => md.disable(['backticks', 'entity', '__missing__']), {
  message: 'MarkdownIt. Failed to disable unknown rule(s): __missing__'
})
assert.deepEqual(flags(md), beforeFlags)
assert.deepEqual(chains(md), beforeChains)
assert.equal(md.renderInline(src), html)
assert.equal(md.disable(['backticks', 'entity']), md)
assert.equal(md.renderInline(src), '`x` &amp;amp;')
```

## J3-O2

Setup: The primary `backticks` and `entity` rules initially disabled, and all observed chains compiled.

Action: Reject a mixed enable batch, then enable the valid names.

Expected result: Failure preserves disabled state and HTML; the later enable restores normal entity rendering.

```js
const md = markdownit().disable(['backticks', 'entity'])
const src = '`x` &amp;'
const html = md.renderInline(src)
const beforeFlags = flags(md)
const beforeChains = chains(md)
assert.throws(() => md.enable(['backticks', 'entity', '__missing__']), {
  message: 'MarkdownIt. Failed to enable unknown rule(s): __missing__'
})
assert.deepEqual(flags(md), beforeFlags)
assert.deepEqual(chains(md), beforeChains)
assert.equal(md.renderInline(src), html)
assert.equal(md.enable(['backticks', 'entity']), md)
assert.equal(md.renderInline(src), '<code>x</code> &amp;')
```

## J3-O3 — designated witness

Setup: A default parser with both inline stages enabled, an emphasis render completed, and all observed chains compiled.

Action: Reject `disable(['emphasis', '__missing__'])` and reuse the parser.

Expected result: Every stage retains its prior flags and functions; emphasis still renders. The twin disables the secondary-inline emphasis postprocessor before throwing.

```js
const md = markdownit()
const html = md.renderInline('*x*')
assert.equal(html, '<em>x</em>')
const beforeFlags = flags(md)
const beforeChains = chains(md)
assert.throws(() => md.disable(['emphasis', '__missing__']), {
  message: 'MarkdownIt. Failed to disable unknown rule(s): __missing__'
})
assert.deepEqual(flags(md), beforeFlags)
assert.deepEqual(chains(md), beforeChains)
assert.equal(md.renderInline('*x*'), html)
```

## J3-O4

Setup: A normal instance, a repeated valid shared rule name, and permissive calls containing unknown names.

Action: Disable and re-enable `emphasis`; exercise unknown-only, empty-array, and string calls.

Expected result: Both inline stages change together, arrays are unmodified, unknown-only permissive calls do nothing, and all successful calls return the instance.

```js
const md = markdownit()
const input = ['emphasis', '__missing__', 'emphasis']
assert.equal(md.disable(input, true), md)
assert.deepEqual(input, ['emphasis', '__missing__', 'emphasis'])
for (const r of [md.inline.ruler, md.inline.ruler2]) {
  assert.equal(r.__rules__[r.__find__('emphasis')].enabled, false)
}
assert.equal(md.renderInline('*x*'), '*x*')
const before = flags(md)
assert.equal(md.enable(['__missing__'], true), md)
assert.equal(md.disable([], false), md)
assert.deepEqual(flags(md), before)
assert.equal(md.enable('emphasis'), md)
for (const r of [md.inline.ruler, md.inline.ruler2]) {
  assert.equal(r.__rules__[r.__find__('emphasis')].enabled, true)
}
assert.equal(md.renderInline('*x*'), '<em>x</em>')
```

## J3-O5

Setup: A normal instance and an ordered list of repeated unknown names surrounding a valid primary-parser name.

Action: Attempt both strict operations with the same caller-owned array.

Expected result: Both error messages retain the ordered repeated unknown names; configuration and input are preserved.

```js
const md = markdownit()
const input = ['__z__', 'entity', '__a__', '__z__']
const before = flags(md)
for (const method of ['enable', 'disable']) {
  assert.throws(() => md[method](input), {
    message: `MarkdownIt. Failed to ${method} unknown rule(s): __z__,__a__,__z__`
  })
  assert.deepEqual(flags(md), before)
  assert.deepEqual(input, ['__z__', 'entity', '__a__', '__z__'])
}
```
