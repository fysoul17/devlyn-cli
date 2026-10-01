# Phase A: candidate repositories

You are the corpus author for a code-review evaluation. The rule you follow is CORPUS-RULE.md in this directory. You work blind: do not read any file on this machine outside this directory. Nothing outside it is relevant to you, and you have no web access.

Task now: list candidate repositories from your own knowledge, before reading any code in depth.
- At least 4 Python and at least 4 JavaScript/TypeScript repositories that you believe satisfy the repository rule: real, public on GitHub, maintained, a license that allows local modification, a test suite that runs with standard tools, and no agent instruction files. Exclude click, commander, django, pytest, tkem/cachetools, hapijs/joi, python-attrs/attrs, isaacs/node-lru-cache and cthackers/adm-zip.
- Prefer libraries of moderate size whose full test suite runs in a few minutes on a laptop, with enough real behavior to host four realistic change requests (boundary semantics, ordering/precedence, failure-state preservation, cross-field consistency) outside lifecycle/installer work.
- For each: `owner/repo`, license, the test command you expect, the toolchain (Python or Node version range, package manager), and one or two sentences on why it fits.

You do not choose among them: root checks each against the rule without any model, and the eligible repository with the lowest sha256 of its GitHub `clone_url` per language is chosen.

Output: a short rationale, then exactly one fenced ```json block: {"python": [{"repo": "owner/repo", "license": "...", "test_command": "...", "toolchain": "...", "why": "..."}], "javascript": [ ... ]}.
