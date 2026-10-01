#!/bin/sh
# 0229 check (J4): spec.md Requirements 1-3, each retained reference_definition token's meta.href/meta.title are strings parsed from the definition at its own map (title '' when none is accepted), also when an earlier same-label definition or a pre-populated env.references entry (including one with missing or non-string fields) wins lookup. Exit 0 = clause holds.
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
  ['[a]: /one "One"\n[a]: /two "Two"\n', null,
    [[[0, 1], '/one', 'One'], [[1, 2], '/two', 'Two']]],
  ['[x]: /a\n[x]: /b', null,
    [[[0, 1], '/a', ''], [[1, 2], '/b', '']]],
  ['[a]: /one "One"\n', { A: { href: '/pre', title: 'P' } },
    [[[0, 1], '/one', 'One']]],
  ['[x]: /a\n[x]: /b', { X: { href: '/pre', title: 'P' } },
    [[[0, 1], '/a', ''], [[1, 2], '/b', '']]],
  // Pre-populated entries with missing or non-string fields.
  ['[x]: /a "A"\n', { X: {} },
    [[[0, 1], '/a', 'A']]],
  ['[x]: /a "A"\n', { X: { href: 1, title: null } },
    [[[0, 1], '/a', 'A']]],
]

for (const [src, references, expected] of cases) {
  const env = references ? { references } : {}
  const actual = occurrences(src, env)
  for (const [, href, title] of actual) {
    assert.equal(typeof href, 'string', JSON.stringify({ src, references, href }))
    assert.equal(typeof title, 'string', JSON.stringify({ src, references, title }))
  }
  assert.deepEqual(actual, expected, JSON.stringify({ src, references }))
}
JS
