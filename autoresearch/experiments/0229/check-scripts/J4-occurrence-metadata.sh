#!/bin/sh
# 0229 check (J4): spec.md Requirements 2-3, each retained reference_definition token's meta.href/meta.title are the values parsed from the definition at its own map (title '' when none is accepted), also when an earlier same-label definition or a pre-populated env.references entry wins lookup. Exit 0 = clause holds.
set -eu
cd "$1"
exec node --input-type=module <<'JS'
import assert from 'node:assert/strict'
import markdownit from './src/index.ts'

const md = markdownit()
md.core.ruler.disable('strip_references')
const occurrences = (src, env) => md.parse(src, env)
  .filter(t => t.type === 'reference_definition')
  .map(t => [t.map, t.meta.href, t.meta.title])

// [source, pre-populated env.references or null, expected [map, href, title] per definition token]
const cases = [
  ['[x]: /first "First"\n[x]: /second\n"bad" trailing\n', null,
    [[[0, 1], '/first', 'First'], [[1, 2], '/second', '']]],
  ['[x]: /first "First"\n\n[x]: /second\n"bad" trailing\n', null,
    [[[0, 1], '/first', 'First'], [[2, 3], '/second', '']]],
  ['[x]: /first "A"\n[x]: /second "B"\n', null,
    [[[0, 1], '/first', 'A'], [[1, 2], '/second', 'B']]],
  ['[a]: /one "One"\n[a]: /two "Two"\n', null,
    [[[0, 1], '/one', 'One'], [[1, 2], '/two', 'Two']]],
  ['[x]: /a "A"\n[x]: /b "B"', null,
    [[[0, 1], '/a', 'A'], [[1, 2], '/b', 'B']]],
  ['[x]: /a\n[x]: /b', null,
    [[[0, 1], '/a', ''], [[1, 2], '/b', '']]],
  ['[x]: /a "A"\n', { X: { href: '/pre', title: '' } },
    [[[0, 1], '/a', 'A']]],
  ['[a]: /one "One"\n', { A: { href: '/pre', title: 'P' } },
    [[[0, 1], '/one', 'One']]],
  ['[x]: /first "First"\n[x]: /second\n"bad" trailing\n', { X: { href: '/pre', title: 'P' } },
    [[[0, 1], '/first', 'First'], [[1, 2], '/second', '']]],
]

for (const [src, references, expected] of cases) {
  const env = references ? { references } : {}
  assert.deepEqual(occurrences(src, env), expected, JSON.stringify({ src, references }))
}
JS
