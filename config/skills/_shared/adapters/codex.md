# Codex adapter

## Invocation

A Codex executor runs through `_shared/codex-monitored.sh`, never a raw or piped
`codex exec`: `bash "$DEVLYN_SHARED_DIR/codex-monitored.sh" <arguments for codex exec> "<prompt>"`.
Deliver a multiline prompt as exact file bytes: set `DEVLYN_CODEX_PROMPT_FILE=<file>`
and pass the sole prompt argument `-`.
