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
