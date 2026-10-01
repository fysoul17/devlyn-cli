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
