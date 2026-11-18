# Cursor adapter

executor: no
command: cursor-agent

Engine `cursor`, the Cursor CLI (`cursor-agent`): it reviews and never implements.

## Review

A fresh read-only run in the checkout that holds the change, given the requirement and the change, never the working conversation:
`cursor-agent -p "<prompt>" --mode ask --sandbox enabled`.
`<prompt>` is passed as one literal argument: the shell must not evaluate anything in it. Cursor must already trust the folder: otherwise it refuses and says so, and this reviewer could not start. The trust flag its refusal suggests is never added, because trusting a folder is the user's decision. No model or effort is passed: Cursor keeps a model given on the command line as the user's own default, so the review runs on the model Cursor is set to. In a folder Cursor trusts, that folder's hooks run as in the user's own Cursor sessions, and the user's own configuration still applies.
