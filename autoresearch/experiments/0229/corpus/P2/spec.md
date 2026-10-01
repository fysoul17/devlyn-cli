---
id: "P2"
title: "Support offset-specific entries in parser timezone mappings"
kind: feature
status: planned
complexity: high
depends_on: []
---

# Support offset-specific entries in parser timezone mappings

## Context

Timezone abbreviations can refer to different zones, and some input strings contain both an abbreviation and a numeric offset. A `tzinfos` callable can already use both values, while a mapping can currently distinguish only names. Allow mappings to express the same common disambiguation without requiring a callback.

## Requirements

- [ ] `dateutil.parser.parse` and `parser.parse` accept `tzinfos` mappings with `(tzname, tzoffset)` tuple keys, using the name and offset in seconds produced by the existing parser. Either component may be `None` when that information is absent.
- [ ] When both an exact tuple key and a name-only key match, select the tuple entry by key presence, including when its value is `None` or zero.
- [ ] When the tuple key is absent, use the existing name-only mapping lookup; if neither key is present, retain the existing built-in timezone resolution and warning behavior.
- [ ] Tuple-key values support the same conversions as name-key values: `tzinfo` objects, timezone strings, integer offsets, and `None`. A selected `None` produces a naive result, and an unsupported selected value raises the existing `TypeError`.
- [ ] Callable `tzinfos` behavior remains unchanged: call it once with the parsed name and offset, and apply its returned value using the existing conversion rules.
- [ ] `ignoretz=True` bypasses timezone mapping and callback resolution, including tuple entries, and retains its existing output behavior.
- [ ] Update the `tzinfos` parameter documentation in the parser source to describe tuple matching and fallback, without changing token parsing or timezone-name normalization.

## Constraints

- Change only `src/dateutil/parser/_parser.py` and `tests/test_parser.py`, because the existing timezone construction path and parser tests own this behavior.
- Add no dependencies, because ordinary mapping operations and the current timezone constructors provide the feature.
- Keep the existing test, coverage, and tooling configuration unchanged, so these checks continue to cover compatibility.
- Preserve the project's existing Python compatibility conventions, because this extends the shared parser API.

## Out of Scope

- New timezone token syntax or changes to numeric-offset sign interpretation.
- Changes to `isoparse`, `parserinfo`, or timezone database lookup.
- Validating that a returned timezone's offset equals the offset written in the input.
- New callback protocols or warning categories.

<!-- devlyn:verification -->
## Verification

- `PYTHONPATH=src COVERAGE_FILE=.tox/.coverage /Users/Shared/devlyn-vr-0228-dev/screen-0229/toolchains/dateutil/venv/bin/python -m pytest tests docs --cov-config=tox.ini --cov=dateutil --cov-fail-under=80` exits 0. This runs the repository's test command, including an added sequence that reuses a mapping for exact-tuple resolution, name fallback, and `ignoretz`, plus conversion and callback regressions; it enforces the project coverage target from `codecov.yml` locally.

- `XDG_CACHE_HOME=.cache BLACK_CACHE_DIR=.cache/black /Users/Shared/devlyn-vr-0228-dev/screen-0229/toolchains/dateutil/venv/bin/python -m darker --check --diff --color --isort --revision "$(git rev-list --max-parents=0 HEAD)" .` exits 0. This is the read-only Darker/isort check from the validation workflow, comparing changes with the pinned base at the root commit; formatter caches are directed to ignored output paths.
- `/Users/Shared/devlyn-vr-0228-dev/screen-0229/toolchains/dateutil/venv/bin/python -m pre_commit_hooks.debug_statement_hook src/dateutil/parser/_parser.py tests/test_parser.py` exits 0. This runs the configured debug-statement hook on the two authorized Python files.
- `git diff --check "$(git rev-list --max-parents=0 HEAD)" -- src/dateutil/parser/_parser.py tests/test_parser.py` exits 0. This checks changed-line whitespace against the pinned base at the root commit without invoking the configured whitespace fixer.

The automated checks provide baseline and selected regression coverage. Requirements and constraints not exercised by them remain source-review obligations. No type-check command is configured in this repository.
