---
id: "1.1"
title: "Fix CLI help-text typo"
phase: 1
status: planned
priority: low
complexity: low
depends-on: []
---

# 1.1 Fix CLI help-text typo

## Context
The `--help` output contains a misspelling: "recieve" should be "receive". Minor user-visible polish.

## Customer Frame
When a user runs `devlyn --help`, they want the output to read professionally so they trust the tool.

## Objective
The help string prints "receive" (correct spelling) instead of "recieve".

## Requirements
- [ ] `bin/devlyn.js` help string contains the correct spelling
- [ ] Running `node bin/devlyn.js --help` outputs no typos in the flags section
- [ ] Unit test or snapshot test covers the help output

## Constraints
- Do not touch other strings in the help output.

## Out of Scope
- Rewriting or restructuring the help output.
- Adding new flags or examples.

## Dependencies
- **Internal**: (none)
- **External**: (none)

## Verification
- [ ] `node bin/devlyn.js --help | grep -c recieve` returns 0
- [ ] `node bin/devlyn.js --help | grep -c receive` returns 1
