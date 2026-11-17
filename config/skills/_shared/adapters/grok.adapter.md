# Grok adapter

executor: no

Engine `grok`, the Grok CLI: it reviews and never implements.

## Review

A fresh read-only run in the checkout that holds the change (a headless session works only in its current directory), given the requirement and the change, never the working conversation:
`GROK_CLAUDE_MCPS_ENABLED=false grok -p "<prompt>" --tools "read_file,grep,list_dir" --disallowed-tools "Agent,run_terminal_cmd,search_replace,web_search,web_fetch"`,
plus `-m <model>` and `--reasoning-effort <effort>` when pinned; a long prompt goes as `--prompt-file <file>` in place of `-p "<prompt>"`. The run cannot change the checkout, and the user's own configuration (hooks, connected tools) still applies.
