# Codex adapter

## Invocation

A Codex executor runs through `_shared/codex-monitored.sh`, never a raw or piped
`codex exec`: `bash "$DEVLYN_SHARED_DIR/codex-monitored.sh" <arguments for codex exec> "<prompt>"`.
The `workspace-write` sandbox keeps `.git` read-only, so an executor that commits adds the
common Git directory (`git rev-parse --path-format=absolute --git-common-dir`) as a writable
root: `-s workspace-write -c 'sandbox_workspace_write.writable_roots=["<git dir>"]'`.
Deliver a multiline prompt as exact file bytes: set `DEVLYN_CODEX_PROMPT_FILE=<file>`
and pass the sole prompt argument `-`.
