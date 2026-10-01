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
