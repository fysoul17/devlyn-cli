#!/bin/sh
set -eu

if [ "$#" -ne 1 ] || [ ! -d "$1" ]; then
  echo 'usage: oracle/run.sh <tree>' >&2
  exit 1
fi

cd "$1"
PATH=/Users/Shared/devlyn-vr-0228-dev/screen-0229/toolchains/markdown-it/node-bin:$PATH
export PATH

rows=''
separator=''
for row_id in J3-O1 J3-O2 J3-O3 J3-O4 J3-O5; do
  if result=$(node --input-type=module - "$row_id" <<'JS'
import assert from 'node:assert/strict'
import markdownit from './src/index.ts'

const managers = md => [md.core.ruler, md.block.ruler, md.inline.ruler, md.inline.ruler2]
const flags = md => managers(md).map(r => r.__rules__.map(x => [x.name, x.enabled]))
const chains = md => [
  ...managers(md).map(r => r.getRules('').slice()),
  md.block.ruler.getRules('paragraph').slice(),
  md.block.ruler.getRules('reference').slice()
]

const row = process.argv[2]
try {
  switch (row) {
    case 'J3-O1': {
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
      break
    }
    case 'J3-O2': {
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
      break
    }
    case 'J3-O3': {
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
      break
    }
    case 'J3-O4': {
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
      break
    }
    case 'J3-O5': {
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
      break
    }
    default:
      throw new Error(`Unknown oracle row: ${row}`)
  }
  process.stdout.write('true')
} catch (error) {
  process.stdout.write('false')
}
JS
  ); then
    case "$result" in
      true|false) ;;
      *) exit 1 ;;
    esac
    rows="$rows$separator\"$row_id\":$result"
    separator=','
  else
    exit 1
  fi
done
printf '{"rows":{%s}}\n' "$rows"
