#!/usr/bin/env bash
# build.sh <absent context directory>; prints the image .Id to register, never launches a model.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
ctx=${1:?supply an absent build context directory}
mkdir "$ctx"
cd "$ctx"
fetch() {  # name url sha256
  curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' -o "$1" "$2"
  echo "$3  $1" | shasum -a 256 -c -
  echo "$3  $1" >> artifacts.sha256
}
fetch node.tar.xz https://nodejs.org/dist/v22.23.2/node-v22.23.2-linux-arm64.tar.xz fff4078c5def658577f92c88db7db3bc0072924bfb93fe52c1e744a54e94abb8
fetch claude.tgz https://registry.npmjs.org/@anthropic-ai/claude-code-linux-arm64/-/claude-code-linux-arm64-2.1.296.tgz 56abbe1cfc85e5b37afeef5ae8b4856ddc32bbe443b82689a3b5f99992045cd1
fetch codex.tgz https://registry.npmjs.org/@openai/codex/-/codex-0.162.1-linux-arm64.tgz a355051d0c296ed50e42e55aceabf74f017f2f96e223fc7ee2199ea8a60cad4b
fetch gh.tgz https://github.com/cli/cli/releases/download/v2.83.2/gh_2.83.2_linux_arm64.tar.gz b1a0c0a0fcf18524e36996caddc92a062355ed014defc836203fe20fba75a38e
docker build --platform linux/arm64 --iidfile image.id -f "$here/Dockerfile" .
image_id=$(cat image.id)
docker run --rm --network none "$image_id" sh -c 'node --version && claude --version && codex --version && gh --version && python -m pytest --version'
docker image inspect "$image_id" --format '{{.Id}}'
