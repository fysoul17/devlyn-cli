#!/bin/sh
# 0229 check (J3): with ignoreInvalid omitted, disable(['emphasis', '__missing__']) on a warmed default parser and enable(['emphasis', '__missing__']) on a warmed parser with emphasis disabled each throw and apply none of their changes: enabled states, default and alternate chain function sequences of core.ruler, block.ruler, inline.ruler and inline.ruler2, and rendering equal their pre-call values. Exit 0 = clause holds.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$here/J3-rejected-disable-emphasis-preserves-state.sh" "$1" 'disable:emphasis enable:emphasis'
