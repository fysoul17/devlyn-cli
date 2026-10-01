import assert from 'node:assert/strict'
import markdownit from './src/index.ts'
const retaining = () => {
  const md = markdownit()
  md.core.ruler.disable('strip_references')
  return md
}
const definitions = tokens => tokens.filter(t => t.type === 'reference_definition')
const plainMeta = token => ({ ...token.meta })

try {
  switch (process.env.ORACLE_ROW) {
    case 'J4-O1': {
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
      break
    }
    case 'J4-O2': {
      const md = retaining()
      const env = {}
      const src = '[x]: /u "one\ntwo &amp; three"\n\n[x]\n'
      const tokens = md.parse(src, env)
      const [def] = definitions(tokens)
      assert.deepEqual(plainMeta(def), { label: 'X', href: '/u', title: 'one\ntwo & three' })
      assert.deepEqual(def.map, [0, 2])
      assert.deepEqual(env.references.X, { href: '/u', title: 'one\ntwo & three' })
      assert.equal(md.renderer.render(tokens, md.options, env), '<p><a href="/u" title="one\ntwo &amp; three">x</a></p>\n')
      break
    }
    case 'J4-O3': {
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
      break
    }
    case 'J4-O4': {
      const md = retaining()
      const env = {}
      const src = '[x]: /u\n"bad" trailing\n\n[x]\n'
      const tokens = md.parse(src, env)
      const [def] = definitions(tokens)
      assert.deepEqual(plainMeta(def), { label: 'X', href: '/u', title: '' })
      assert.deepEqual(def.map, [0, 1])
      assert.deepEqual(env.references.X, { href: '/u', title: '' })
      assert.equal(md.renderer.render(tokens, md.options, env), '<p>&quot;bad&quot; trailing</p>\n<p><a href="/u">x</a></p>\n')
      break
    }
    case 'J4-O5': {
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
      break
    }
    default:
      throw new Error(`unknown oracle row: ${process.env.ORACLE_ROW}`)
  }
} catch {
  process.exit(42)
}
