#!/usr/bin/env bash
# Build the 0222 image from pinned artifacts: build.sh <empty-or-cache-dir>.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
ctx=$1
mkdir -p "$ctx" && cd "$ctx"
fetch() {  # name url sha256
  [ -f "$1" ] || curl -fsSL -o "$1" "$2"
  echo "$3  $1" | shasum -a 256 -c -
}
fetch node-v22.23.2-linux-arm64.tar.xz https://nodejs.org/dist/v22.23.2/node-v22.23.2-linux-arm64.tar.xz fff4078c5def658577f92c88db7db3bc0072924bfb93fe52c1e744a54e94abb8
fetch codex.tgz https://registry.npmjs.org/@openai/codex/-/codex-0.156.1-linux-arm64.tgz 3ca3c3a85e184594d0b665ea9028bc38c4ae89691e86edbeefd2c6f58979fcb4
fetch claude.tgz https://registry.npmjs.org/@anthropic-ai/claude-code-linux-arm64/-/claude-code-linux-arm64-2.1.281.tgz f98f689be21ef73428ccdbacba561a14c56bbf54a06905a35af6dd59817cbf7a
rm -rf codex claude && mkdir codex claude
tar -xzf codex.tgz -C codex && tar -xzf claude.tgz -C claude
docker build -q -f "$here/Dockerfile" -t devlyn-0222 "$ctx"
docker run --rm --network none devlyn-0222 bash -lc 'command -v less codex rg claude node && codex --version && claude --version && python -m pytest --version'
docker image inspect devlyn-0222 --format '{{.Id}}'
