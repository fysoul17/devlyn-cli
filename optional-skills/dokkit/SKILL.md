---
name: dokkit
description: >
  Document template filling system for DOCX and HWPX formats.
  Ingests source documents, analyzes templates, detects fillable fields,
  fills them surgically using source data, reviews with confidence scoring,
  and exports completed documents. Supports Korean and English templates.
  Subcommands: init, sources, preview, ingest, fill, fill-doc, modify, review, export.
  Use when user says "fill template", "fill document", "ingest", "dokkit".
user-invocable: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent
argument-hint: "<subcommand> [arguments]"
context:
  - type: file
    path: ${CLAUDE_SKILL_DIR}/COMMANDS.md
---

# Dokkit — Document Template Filling System

Surgical document filling for DOCX and HWPX templates using ingested source data. One command with 9 subcommands covering the full document filling lifecycle.

## Subcommands

| Subcommand | Arguments | Type | Description |
|------------|-----------|------|-------------|
| `init` | `[--force] [--keep-sources]` | Inline | Initialize or reset workspace |
| `sources` | — | Inline | Display ingested sources dashboard |
| `preview` | — | Inline | Generate PDF preview via LibreOffice |
| `ingest` | `<file1> [file2] ...` | Agent | Parse source documents into workspace |
| `fill` | `<template.docx\|hwpx>` | Agent | End-to-end: analyze, fill, review, auto-fix, export |
| `fill-doc` | `<template.docx\|hwpx>` | Agent | Analyze template and fill fields only |
| `modify` | `"<instruction>"` | Agent | Apply targeted changes to filled document |
| `review` | `[section\|approve]` | Agent | Review with per-field confidence annotations |
| `export` | `<docx\|hwpx\|pdf>` | Agent | Export filled document to format |

## Routing

Parse `$ARGUMENTS` to determine the subcommand:

1. Extract `$1` as the subcommand name
2. Pass remaining arguments (`$2`, `$3`, ...) to the subcommand
3. If `$1` is empty or unrecognized, display the subcommand table above with usage examples

Full workflows for each subcommand are in COMMANDS.md (auto-loaded via context).

<example>
- `/dokkit ingest docs/resume.pdf docs/transcript.xlsx` — ingest two sources
- `/dokkit fill docs/template.hwpx` — end-to-end fill pipeline
- `/dokkit modify "Change the phone number to 010-1234-5678"` — targeted change
- `/dokkit export pdf` — export as PDF
</example>

## Architecture

### Agents

| Agent | Model | Role |
|-------|-------|------|
| **dokkit-ingestor** | opus | Parse source docs into `.dokkit/sources/` (.md + .json pairs) |
| **dokkit-analyzer** | opus | Analyze templates, detect fields, map to sources. Writes `analysis.json`. READ-ONLY on templates. |
| **dokkit-filler** | opus | Surgical XML modification using analysis.json. Three modes: fill, modify, review. |
| **dokkit-exporter** | sonnet | Repackage ZIP archives, PDF conversion via LibreOffice. |

### Workspace

All agents communicate via the `.dokkit/` filesystem:

```
.dokkit/
├── state.json          # Single source of truth for session state
├── sources/            # Ingested content (.md + .json pairs)
├── analysis.json       # Template analysis output (from analyzer)
├── images/             # Sourced images for template filling
├── template_work/      # Unpacked template XML (working copy)
└── output/             # Exported filled documents
```

### State Protocol

Read `.dokkit/state.json` before any operation. Write state changes atomically: read current → update fields → write back → validate.

```
init → state created (empty)
ingest → source added to sources[]
fill/fill-doc → template set, analysis created, filled_document created
modify → filled_document updated
review approve → filled_document.status = "finalized"
export → export entry added to exports[]
```

Validate after every write: `python ${CLAUDE_SKILL_DIR}/scripts/validate_state.py .dokkit/state.json`

### Knowledge Files

Agent-facing knowledge bases in this skill directory:

| File | Purpose | Agents |
|------|---------|--------|
| `STATE.md` | State schema and management protocol | All |
| `INGESTION.md` | Format routing and parsing strategies | dokkit-ingestor |
| `ANALYSIS.md` | Field detection, confidence scoring, output schema | dokkit-analyzer |
| `FILLING.md` | XML surgery rules, matching strategy, image insertion | dokkit-analyzer, dokkit-filler |
| `DOCX-XML.md` | Open XML structure for DOCX documents | dokkit-analyzer, dokkit-filler |
| `HWPX-XML.md` | OWPML structure for HWPX documents | dokkit-analyzer, dokkit-filler |
| `IMAGE-SOURCING.md` | Image generation, search, and insertion patterns | dokkit-filler |
| `EXPORT.md` | Document compilation and format conversion | dokkit-exporter |

Deep reference material in `references/`:
- `state-schema.md` — Complete state.json schema
- `supported-formats.md` — Detailed format specifications
- `docx-structure.md`, `docx-field-patterns.md` — DOCX patterns
- `hwpx-structure.md`, `hwpx-field-patterns.md` — HWPX patterns (10 detection patterns)
- `field-detection-patterns.md` — Advanced heuristics (9 DOCX + 6 HWPX)
- `section-range-detection.md` — Dynamic range detection for section_content
- `section-image-interleaving.md` — Image interleaving algorithm
- `image-opportunity-heuristics.md` — AI image opportunity detection
- `image-xml-patterns.md` — Image element structures (DOCX + HWPX)

Scripts in `scripts/`:
- `validate_state.py` — State validation
- `parse_xlsx.py`, `parse_hwpx.py`, `parse_image_with_gemini.py` — Custom parsers
- `detect_fields.py`, `detect_fields_hwpx.py` — Field detection
- `validate_docx.py`, `validate_hwpx.py` — Document validation
- `compile_hwpx.py` — HWPX repackaging
- `export_pdf.py` — PDF conversion

## Rules

<rules>
- Display errors clearly with actionable guidance. Never silently fall back to defaults.
- Original template is never modified — copies go to `.dokkit/template_work/`.
- Analyzer is read-only on templates. Only the filler modifies XML.
- Confidence levels: high, medium, low (not numeric scores).
- Signatures must be user-provided — never auto-generate them.
- Validate state after every write with `scripts/validate_state.py`.
- Inline commands (init, sources, preview) execute directly — do NOT spawn agents.
- Agent-delegated commands spawn the appropriate agent(s) sequentially.
</rules>

## Known Pitfalls

Critical issues discovered through production use:

1. **HWPX namespace stripping**: Python ET strips unused namespace declarations. Restore ALL 14 original xmlns on EVERY root element after any `tree.write()`. Applies to section0.xml, content.hpf, header.xml.
2. **HWPX subList cell wrapping**: ~65% of cells wrap content in `<hp:subList>/<hp:p>`. Check for subList before writing content.
3. **table_content "Pre-filled" bug**: Never set `mapped_value` to placeholder strings for `table_content` fields. Use `mapped_value: null` with `action: "preserve"`.
4. **HWPX cellAddr rowAddr corruption**: After row insert/delete, re-index ALL `rowAddr` values. Duplicate rowAddr causes silent data loss.
5. **HWPX `<hp:pic>` inside `<hp:run>`**: Pic as sibling of run renders invisible. Must be `<hp:run><hp:pic>...<hp:t/></hp:run>`.
6. **HWPML units**: 1/7200 inch, NOT hundredths of mm. 1mm ~ 283.46 units. A4 text width ~ 46,648 units.
7. **rowSpan stripping**: When cloning rows with rowSpan>1, divide cellSz height by rowSpan.
8. **HWPX pic element order**: offset, orgSz, curSz, flip, rotationInfo, renderingInfo, imgRect, imgClip, inMargin, imgDim, hc:img, sz, pos, outMargin.
9. **HWPX post-write safety**: After ET write: (a) restore namespaces, (b) fix XML declaration to double quotes with `standalone="yes"`, (c) remove newline between `?>` and `<root>`.
10. **compile_hwpx.py skip .bak**: Backup files must be excluded from ZIP repackaging.
