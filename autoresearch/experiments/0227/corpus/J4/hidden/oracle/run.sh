#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo 'usage: oracle/run.sh <tree>' >&2
  exit 2
fi

tree=$(cd "$1" && pwd)
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT HUP INT TERM

tar -C "$tree" --exclude=.git --exclude=node_modules --exclude=dist --exclude=.tap -cf - . | tar -C "$scratch" -xf -
if [ ! -e "$tree/node_modules" ]; then
  echo 'node_modules is required in the supplied tree' >&2
  exit 1
fi
ln -s "$tree/node_modules" "$scratch/node_modules"
cp "$(dirname "$0")/runner.mjs" "$scratch/runner.mjs"

export PATH=/Users/Shared/devlyn-vr-0227/toolchains/node-lru-cache/node-bin:$PATH
if ! (cd "$scratch" && npm run prepare > build.log 2>&1); then
  cat "$scratch/build.log" >&2
  exit 1
fi
node "$scratch/runner.mjs"
