# J1 hidden oracle

Run each row in an independent process from the implemented checkout root, using `node --input-type=module` with the row's JavaScript on stdin after this common prelude:

```js
import assert from 'node:assert/strict'
import markdownit from './src/index.ts'
```

Use the same command-level PATH assignment as the public command. An assertion failure is a failed row. Only J1-O3 is the designated witness; every other row must pass on both arms.

## J1-O1

Setup: A code span with a full-range lookahead already cached, nonempty pending text, and a nonzero nesting level.

Action: Reset the cursor and narrow the range so the closer is excluded.

Expected result: The second lookahead advances only over the opener; tokens, pending text, and nesting level are preserved.

```js
const md = markdownit()
const state = new md.inline.State('`a`', md, {}, [])
state.pending = 'keep'
state.level = 2
md.inline.skipToken(state)
assert.equal(state.pos, 3)
state.pos = 0
state.posMax = 2
md.inline.skipToken(state)
assert.equal(state.pos, 1)
assert.deepEqual(state.tokens, [])
assert.equal(state.pending, 'keep')
assert.equal(state.level, 2)
assert.equal(state.posMax, 2)
```

## J1-O2

Setup: An observing rule before `text`, and a code span entirely inside an unchanged window.

Action: Call lookahead twice from the same position.

Expected result: The second call uses the cached end without invoking rules again.

```js
const md = markdownit()
let calls = 0
md.inline.ruler.before('text', 'observe', () => { calls++; return false })
const state = new md.inline.State('`a`', md, {}, [])
md.inline.skipToken(state)
assert.equal(state.pos, 3)
assert.equal(calls, 1)
state.pos = 0
md.inline.skipToken(state)
assert.equal(state.pos, 3)
assert.equal(calls, 1)
assert.equal(state.cache[0], 3)
```

## J1-O3 — designated witness

Setup: The same code span is first examined with an upper bound excluding its closing backtick.

Action: Restore the full bound and examine the same starting position.

Expected result: The cached unmatched opener is reconsidered and the complete code span is skipped. The twin stops at 1 instead of 3.

```js
const md = markdownit()
const state = new md.inline.State('`a`', md, {}, [])
state.posMax = 2
md.inline.skipToken(state)
assert.equal(state.pos, 1)
state.pos = 0
state.posMax = state.src.length
md.inline.skipToken(state)
assert.equal(state.pos, 3)
assert.deepEqual(state.tokens, [])
assert.equal(state.level, 0)
```

## J1-O4

Setup: A cache entry whose ending position remains inside a smaller window.

Action: Narrow the window and repeat lookahead with an observing rule installed.

Expected result: The new bound causes another rule invocation even though the resulting end happens to be equal.

```js
const md = markdownit()
let calls = 0
md.inline.ruler.before('text', 'observe', () => { calls++; return false })
const state = new md.inline.State('`a` xx', md, {}, [])
md.inline.skipToken(state)
assert.equal(state.pos, 3)
state.pos = 0
state.posMax = 3
md.inline.skipToken(state)
assert.equal(state.pos, 3)
assert.equal(calls, 2)
```

## J1-O5

Setup: A normal parser instance.

Action: Render a link containing a code span and then an unmatched code opener.

Expected result: Existing Markdown behavior is unchanged.

```js
const md = markdownit()
assert.equal(md.renderInline('[a `b`](/u)'), '<a href="/u">a <code>b</code></a>')
assert.equal(md.renderInline('`a'), '`a')
```
