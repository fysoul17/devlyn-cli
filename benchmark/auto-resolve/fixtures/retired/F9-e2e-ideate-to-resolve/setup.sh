#!/usr/bin/env bash
# F9 setup — seed a few synthetic commits with different authors so the
# `gitstats` subcommand's "top 3 authors by commit count" requirement is
# meaningfully exercised. Without this, every commit author is the runner's
# default and the ranking test is a no-op.
set -e

commit_as() {
  local name="$1" email="$2" file="$3" message="$4"
  echo "$(date +%s%N) $name" >> "$file"
  git add "$file"
  git -c user.name="$name" -c user.email="$email" commit -q -m "$message"
}

mkdir -p .bench-seed

commit_as "Alpha Author"   "alpha@bench.test"   .bench-seed/log "seed: alpha 1"
commit_as "Alpha Author"   "alpha@bench.test"   .bench-seed/log "seed: alpha 2"
commit_as "Alpha Author"   "alpha@bench.test"   .bench-seed/log "seed: alpha 3"
commit_as "Alpha Author"   "alpha@bench.test"   .bench-seed/log "seed: alpha 4"
commit_as "Beta Author"    "beta@bench.test"    .bench-seed/log "seed: beta 1"
commit_as "Beta Author"    "beta@bench.test"    .bench-seed/log "seed: beta 2"
commit_as "Beta Author"    "beta@bench.test"    .bench-seed/log "seed: beta 3"
commit_as "Gamma Author"   "gamma@bench.test"   .bench-seed/log "seed: gamma 1"
commit_as "Gamma Author"   "gamma@bench.test"   .bench-seed/log "seed: gamma 2"
commit_as "Delta Author"   "delta@bench.test"   .bench-seed/log "seed: delta 1"

echo "F9 setup: seeded 10 commits across 4 authors (Alpha 4 / Beta 3 / Gamma 2 / Delta 1)"
