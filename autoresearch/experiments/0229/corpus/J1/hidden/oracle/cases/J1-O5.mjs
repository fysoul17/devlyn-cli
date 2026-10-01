const md = markdownit()
assert.equal(md.renderInline('[a `b`](/u)'), '<a href="/u">a <code>b</code></a>')
assert.equal(md.renderInline('`a'), '`a')
