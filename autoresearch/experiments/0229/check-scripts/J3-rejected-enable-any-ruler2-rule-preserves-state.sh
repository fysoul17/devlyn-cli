#!/bin/sh
# 0229 check (J3): with ignoreInvalid omitted, disable(['emphasis', '__missing__']) on a warmed default parser, and enable([rule, '__missing__']) on a warmed parser with that rule disabled for each inline.ruler2 rule (balance_pairs, strikethrough, emphasis, fragments_join), throw and apply none of their changes: enabled states, default and alternate chain function sequences of all four rulers, and rendering equal their pre-call values. Exit 0 = clause holds.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$here/J3-rejected-disable-emphasis-preserves-state.sh" "$1" \
  'disable:emphasis enable:balance_pairs enable:strikethrough enable:emphasis enable:fragments_join'
