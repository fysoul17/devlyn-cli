#!/bin/sh
# 0229 check (J3): with ignoreInvalid omitted, disable(['emphasis', '__missing__']) (emphasis is registered in inline.ruler and inline.ruler2) throws and applies none of its changes: on a warmed default parser, enabled states, default and alternate chain function sequences of core.ruler, block.ruler, inline.ruler and inline.ruler2, and rendering equal their pre-call values. Exit 0 = clause holds.
# Optional $2: space-separated operation:rule cases replacing the default, used by the other J3 rejected-batch checks.
set -eu
cd "$1"
exec node --input-type=module - "${2:-disable:emphasis}" <<'JS'
import assert from 'node:assert/strict'
import markdownit from './src/index.ts'

const managers = md => [md.core.ruler, md.block.ruler, md.inline.ruler, md.inline.ruler2]
const flags = md => managers(md).map(r => r.__rules__.map(x => [x.name, x.enabled]))
const chains = md => [
  ...managers(md).map(r => r.getRules('').slice()),
  md.block.ruler.getRules('paragraph').slice(),
  md.block.ruler.getRules('reference').slice()
]
const src = '*x* ~~y~~ **z** _w_\n'

for (const item of process.argv[2].split(' ')) {
  const [operation, name] = item.split(':')
  const where = `${operation}(['${name}', '__missing__'])`
  const md = markdownit()
  // A rejected enable must have something to change: start from the rule disabled.
  if (operation === 'enable') md.disable(name)
  const html = md.render(src) // compiles every chain before the rejected call
  const beforeFlags = flags(md)
  const beforeChains = chains(md)
  assert.throws(() => md[operation]([name, '__missing__']), Error, `${where} did not throw`)
  assert.deepEqual(flags(md), beforeFlags, `${where}: enabled states changed`)
  assert.deepEqual(chains(md), beforeChains, `${where}: chain function sequences changed`)
  assert.equal(md.render(src), html, `${where}: rendering changed`)
}
JS
