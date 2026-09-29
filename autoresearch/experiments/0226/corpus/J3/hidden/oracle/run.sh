#!/bin/sh
set -eu

if [ "$#" -ne 1 ] || [ ! -d "$1" ]; then
    exit 1
fi

exec node "$(dirname "$0")/run.js" "$1"
