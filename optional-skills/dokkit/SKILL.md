---
name: dokkit
description: >
  One-command document template filling. Put source files (회사소개서, 사업자료,
  이미지 등) in a folder, provide a DOCX/HWPX template, and get a polished,
  complete document with AI-generated images. Auto-iterates until perfect.
  Supports Korean government forms: 사업계획서, 지원서, 신청서.
  Trigger on: "fill template", "사업계획서 작성", "문서 작성", "dokkit",
  "fill this form", "템플릿 채워줘", "complete this document", "fill document",
  "template automation", HWPX files, 한글 templates, document generation,
  or any task involving filling document templates with source materials.
  Also trigger when user drops files and asks to fill or complete a template.
user-invocable: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent
argument-hint: "<template_path> <sources_folder> | improve [instruction]"
context:
  - type: file
    path: ${CLAUDE_SKILL_DIR}/PIPELINE.md
---

# Dokkit — One-Command Document Filling

Source folder + template → finished document. Fully automatic, iterates until perfect.

## Usage

```
/dokkit <template_path> <sources_folder>
/dokkit improve ["instruction"]
```

- `template_path`: DOCX or HWPX template file **(required)**
- `sources_folder`: Folder with source materials **(required)**

Both arguments are mandatory. If either is missing, show this error and stop:
```
Error: template과 sources 폴더를 모두 지정해주세요.

Usage: /dokkit <template.docx|hwpx> <sources_folder>
Example: /dokkit docs/사업계획서_양식.docx docs/sources/김철수/
```

<example>
/dokkit docs/사업계획서_양식.docx docs/sources/김철수/
/dokkit docs/template.hwpx docs/자료/
/dokkit improve                              # 전체적으로 품질 향상
/dokkit improve "이미지를 더 넣어줘"          # 특정 방향으로 개선
/dokkit improve "시장분석 섹션을 더 풍부하게"  # 특정 섹션 강화
</example>

## Pipeline Overview

Six phases, fully automated. Phases 3-5 loop until quality gates pass (max 3 iterations).

| # | Phase | What Happens |
|---|-------|-------------|
| 1 | **Prepare** | Parse all source files → structured data |
| 2 | **Analyze** | Detect template fields, map structure |
| 3 | **Fill** | Generate & insert content **section-by-section** |
| 4 | **Images** | Generate via Gemini, insert with **correct aspect ratio** |
| 5 | **Review** | Quality gates → auto-fix failures → re-check |
| 6 | **Export** | Compile document + PDF preview |

Progress shown as: `Phase N/6: description`

## Core Design: Section-by-Section Generation

This is the #1 quality improvement over previous versions.

**Problem**: Generating all content at once → each section gets shallow attention, quality worse than manual AI.

**Solution**: Each template section gets dedicated AI focus with full source context, exactly like asking AI to write one section at a time manually.

For each section:
1. Read the section's template tips and writing instructions
2. Load ALL relevant source data into context
3. Generate rich, persuasive, data-driven content for THIS section only
4. Insert while preserving original formatting exactly
5. Verify quality immediately before moving to next section

The filler agent generates content AND inserts it — no lossy handoff between separate agents.

## Quality Gates

ALL must pass before final export:

| Gate | Criterion | Auto-Fix Strategy |
|------|-----------|-------------------|
| QG1 | Total text ≥ 7,500 chars | Re-enrich thin sections |
| QG2 | Each section_content ≥ 500 chars | Re-generate with more detail |
| QG3 | Zero `00.00` date placeholders | Derive from source context |
| QG4 | Zero `OO`/`○○` name placeholders (exclude schedule table `O` marks) | Derive from source context |
| QG5 | Zero `이미지 영역` text | Remove placeholder text |
| QG6 | Images aspect ratio correct (within 5%) | Re-measure with PIL |
| QG7 | No red/italic guide text in filled cells | Sanitize styles |
| QG8 | ≥ 10 images in document | Generate additional images via `source_images.py` |
| QG9 | Zero `XXXXX`/`XXXXXX` fake placeholders | Replace with real values or "해당없음" |
| QG10 | TOC page numbers not `00` | Remove or update TOC entries |

## Font & Formatting Rules

These rules prevent the font corruption issues seen in previous versions:

1. **Never copy guide text styling** — Template placeholders often use red (#FF0000) and italic. Strip these unconditionally when creating filled runs.
2. **Use template default body style** — Find the document's standard body text formatting (black, regular weight) and apply it to all filled content.
3. **HWPX charPr spacing** — Before ANY text insertion, scan ALL `<hh:charPr>` in `header.xml` and set negative `spacing` values to `"0"`. Negative spacing causes character overlap.
4. **DOCX rPr sanitization** — When copying run properties from label cells, always remove `<w:color>` if red and `<w:i/>` (italic).
5. **Preserve structural formatting** — Keep paragraph alignment (pPr), indentation, spacing, and table cell properties unchanged. Only modify text content and run-level styles.

## Image Rules

### Generation — use `source_images.py` exclusively

**Never write inline Gemini API calls for image generation.** Always use the provided script:
```bash
python ${CLAUDE_SKILL_DIR}/scripts/source_images.py generate \
  --prompt "<prompt>" --preset <preset> --output-dir .dokkit/images/ \
  --project-dir . --lang ko
```
The script uses `gemini-3-pro-image-preview` (high quality), enforces Korean text, and applies correct aspect ratios per preset. Bypassing it results in wrong model, wrong language, wrong dimensions.

### Prompt quality

- Include company/product-specific details — never use generic prompts
- For org charts: use actual names and roles from source data
- For market charts: include specific numbers from sources
- For tech diagrams: name the actual technologies and systems

### Sizing — prevent distortion

1. **Always measure actual dimensions** — After generating any image, use PIL/Pillow to get true pixel dimensions.
2. **Preserve aspect ratio** — Calculate display size that fits within the target cell while maintaining the image's original width:height ratio.
3. **HWPX imgDim** — Must reflect actual pixel dimensions from PIL, NOT layout constants.
4. **DOCX EMU** — Calculate from actual pixels: `EMU = pixels × 914400 / 96`.
5. **Never stretch** — If the image doesn't fit the cell exactly, scale down to fit within bounds (letterbox, don't fill).

```python
# Correct image sizing
from PIL import Image
img = Image.open(path)
actual_w, actual_h = img.size
aspect = actual_w / actual_h

# Scale to fit within target bounds
scale = min(target_w / actual_w, target_h / actual_h)
display_w = int(actual_w * scale)
display_h = int(actual_h * scale)
```

## Architecture

### Workspace
```
.dokkit/
├── state.json          # Pipeline state and progress
├── sources/            # Parsed source data (.md + .json pairs)
├── analysis.json       # Template field map (from analyzer)
├── images/             # Generated/sourced images
├── template_work/      # Unpacked template XML (working copy)
└── output/             # Final completed documents
```

### Agents

| Agent | Model | Role |
|-------|-------|------|
| **dokkit-ingestor** | opus | Parse source files → `.dokkit/sources/` |
| **dokkit-analyzer** | opus | Detect fields & structure → `analysis.json` (NO content generation for sections) |
| **dokkit-filler** | opus | Generate content section-by-section + fill XML + insert images + quality review |
| **dokkit-exporter** | sonnet | Compile ZIP archives, convert to PDF |

### Knowledge Files

| File | Purpose | Used By |
|------|---------|---------|
| `PIPELINE.md` | Detailed pipeline steps (auto-loaded) | Orchestrator |
| `STATE.md` | State schema and management | All agents |
| `INGESTION.md` | Source file parsing | Ingestor |
| `ANALYSIS.md` | Field detection, structure mapping | Analyzer |
| `FILLING.md` | XML surgery rules, image insertion | Filler |
| `DOCX-XML.md` / `HWPX-XML.md` | XML format structures | Analyzer, Filler |
| `IMAGE-SOURCING.md` | Image generation patterns | Filler |
| `EXPORT.md` | Compilation and conversion | Exporter |

## Rules

1. **One command does everything** — no manual subcommands needed (except `improve` for post-fill enhancement)
2. **Never modify the original template** — work on copies in `.dokkit/template_work/`
3. **Section-by-section generation** — each section gets full AI attention with all source data
4. **Aspect ratio preservation** — images never stretched or squashed
5. **Black text only** — never inherit colored/italic guide text styles
6. **Auto-loop** — iterate until ALL quality gates pass (max 3 iterations)
7. **Progress reporting** — show `Phase N/6: description` at each step
8. **Clear errors** — if something fails, show what went wrong with actionable guidance
9. **Gemini API** — if not configured, warn and skip image generation (don't block text filling)

## Known Pitfalls

Critical issues from production experience — these MUST be handled:

1. **HWPX namespace stripping**: Python ET strips unused namespace declarations. Restore ALL 14 original xmlns on EVERY root element after `tree.write()`.
2. **HWPX subList cell wrapping**: ~65% of cells use `<hp:subList>/<hp:p>`. Always check before writing.
3. **table_content "Pre-filled" bug**: Never set `mapped_value` to placeholder strings. Use `null` with `action: "preserve"`.
4. **HWPX cellAddr rowAddr corruption**: After row insert/delete, re-index ALL `rowAddr` values.
5. **HWPX `<hp:pic>` placement**: Must be `<hp:run><hp:pic>...<hp:t/></hp:run>`, not pic as sibling.
6. **HWPML units**: 1/7200 inch. 1mm ~ 283.46 units. A4 text width ~ 46,648 units.
7. **rowSpan stripping**: Divide cellSz height by rowSpan when cloning.
8. **HWPX pic element order**: offset, orgSz, curSz, flip, rotationInfo, renderingInfo, imgRect, imgClip, inMargin, imgDim, hc:img, sz, pos, outMargin.
9. **Section content table preservation**: ONLY replace `<w:p>`/`<hp:p>` elements. NEVER remove `<w:tbl>`/`<hp:tbl>`.
10. **Section range detection**: After deleting tips/instructions, ranges are STALE. Recompute dynamically.
11. **HWPX post-write safety**: Restore namespaces → fix XML declaration → remove newline between `?>` and root.
