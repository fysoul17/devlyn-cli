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
