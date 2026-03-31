# Dokkit Pipeline Reference

Detailed step-by-step procedure for the one-command document filling pipeline.
Auto-loaded when `/dokkit` is invoked.

## Table of Contents

- [Command Parsing](#command-parsing)
- [Full Pipeline](#full-pipeline) (Phases 1-6)
- [Improve Mode](#improve-mode)
- [Error Handling](#error-handling)

---

## Command Parsing

Parse `$ARGUMENTS`:

1. If `$1` is `improve` → [Improve Mode](#improve-mode) with remaining args as instruction
2. If `$1` is a file path (ends in .docx or .hwpx) AND `$2` is a directory → [Full Pipeline](#full-pipeline)
3. If `$1` is a file path but `$2` is missing → Show error:
   ```
   Error: sources 폴더를 지정해주세요.
   Usage: /dokkit <template.docx|hwpx> <sources_folder>
   ```
4. If empty → Show error:
   ```
   Error: template과 sources 폴더를 모두 지정해주세요.
   Usage: /dokkit <template.docx|hwpx> <sources_folder>
   Example: /dokkit docs/사업계획서_양식.docx docs/sources/김철수/
   ```

---

## Full Pipeline

### Phase 1: Prepare Sources

**Goal**: Parse all source files into structured data the filler can use.

1. Validate template file (`$1`) exists and is DOCX or HWPX
2. Validate sources folder (`$2`) exists and contains files
   - If folder is empty: show error "소스 폴더에 파일이 없습니다: `<folder>`"
   - If folder doesn't exist: show error "소스 폴더를 찾을 수 없습니다: `<folder>`"
3. If `.dokkit/` doesn't exist, create workspace:
   ```
   .dokkit/
   ├── sources/
   ├── template_work/
   ├── output/
   ├── images/
   └── state.json (initialized)
   ```
4. List all files in sources folder (recursively)
5. For each source file, spawn **dokkit-ingestor** agent:
   > "Ingest the source document at `<file_path>`. Follow dokkit-ingestor agent instructions. Write to `.dokkit/sources/`."

   Supported formats: PDF, DOCX, XLSX, CSV, PPTX, HWPX, HWP, PNG, JPG, TXT, MD, JSON, HTML
6. Report: `Phase 1/6: Prepared N source files from <folder>`

### Phase 2: Analyze Template

**Goal**: Detect all fillable fields, map template structure, prepare content plans for sections.

Spawn **dokkit-analyzer** agent with these modified instructions:

> "Analyze template at `<path>`. Detect ALL fillable fields including images, Korean placeholders (OO, 00.00), section content areas, and tip boxes.
>
> **IMPORTANT — Changed approach for section_content fields:**
> For `section_content` fields, do NOT generate the full content (mapped_value). Instead:
> - Set `mapped_value: null`
> - Add a `content_plan` object with:
>   - `section_heading`: The section's title/heading from the template
>   - `template_tips`: Writing guidance from the template (작성 팁, ※ instructions)
>   - `relevant_sources`: List of source filenames most relevant to this section
>   - `key_data_points`: Specific statistics, names, dates found in sources
>   - `target_structure`: Expected sub-headings and outline (◦, -, 1. patterns)
>   - `min_chars`: Minimum character target (500-1200 depending on section size)
>
> For all OTHER field types (placeholder_text, empty_cell, table_content, image, etc.): map values normally.
>
> Write `analysis.json`."

Report: `Phase 2/6: Found N fields (X sections, Y tables, Z images)`

### Phase 3: Generate Content (Section by Section)

**Goal**: Generate high-quality content for every field and save to `fill_content.json`.

This is the critical quality phase. The filler generates content with dedicated attention for each section, then saves it to a JSON file. A separate python-docx script handles formatting and insertion.

Spawn **dokkit-filler** agent in **content-generation** mode:

> "Generate content for ALL fields. Read ALL source files from `.dokkit/sources/*.md` and `analysis.json`.
>
> For each `section_content` field:
> 1. Read the `content_plan` from analysis.json
> 2. Generate the BEST possible content for this section:
>    - Write like a professional 사업계획서 consultant
>    - Include specific statistics with exact numbers from source data
>    - Name real organizations, partners, competitors
>    - Use persuasive language backed by evidence
>    - Use `[Bold Heading]` for sub-section titles, `- ` for bullets
>    - Meet min_chars target (800-1200 chars for substantial sections)
>
> For overview table fields: generate concise values.
>
> Save ALL content to `.dokkit/fill_content.json`:
> ```json
> { "field_001": "사업명 값", "field_017": "섹션 내용...", ... }
> ```

Report: `Phase 3/6: Generated content for N fields`

### Phase 3b: Assemble Document (python-docx)

**Goal**: Apply content to template with perfect formatting using `fill_docx.py`.

Run the python-docx assembly script (NOT raw XML surgery):

```bash
python .claude/skills/dokkit/scripts/fill_docx.py \
  <template.docx> \
  .dokkit/analysis.json \
  .dokkit/fill_content.json \
  .dokkit/output/<output_name>.docx
```

The script handles:
- Tip box removal (작성요령 tables + nested tables in cells)
- Instruction text removal (※ paragraphs + blue text)
- Overview table filling (label-matching)
- Section content insertion (with proper pPr/rPr from template)
- Page breaks between chapters
- Color sanitization (all text → black)
- Data table filling (budget, schedule, employee count)

Report: `Phase 3b/6: Document assembled — N sections, M tables, K tip boxes removed`

### Phase 4: Generate & Insert Images

**Goal**: Generate AI images via Gemini and insert into the assembled document using python-docx.

#### Step 4a: Generate Images (parallel)

**YOU MUST use `source_images.py` for ALL image generation.** Do NOT write inline Gemini API calls — the script handles model selection (`gemini-3-pro-image-preview`), Korean text enforcement, aspect ratios, and error handling. Bypassing it will produce wrong-model, wrong-language, wrong-aspect images.

For each image field and image opportunity in `analysis.json`, run in parallel.

**CRITICAL: Always pass `--field-id` and `--purpose`** so the image manifest tracks which image was generated for which slot. Without this, images get randomly assigned to the wrong slots.

```bash
python .claude/skills/dokkit/scripts/source_images.py generate \
  --prompt "<prompt>" \
  --preset <preset> \
  --output-dir .dokkit/images/ \
  --project-dir . \
  --lang ko \
  --field-id <field_id> \
  --purpose "<caption or purpose description>"
```

The script writes each result to `.dokkit/image_manifest.json` — an array of `{image_id, file_path, field_id, purpose, prompt, ...}`. This manifest is the source of truth for which image goes where during insertion.

**Preset selection guide:**
- `infographic` (16:9) — data visualization, market charts, process flows
- `technical_illustration` (16:9) — system architecture, tech diagrams
- `photorealistic` (4:3) — product photos, office scenes
- `concept` (1:1) — abstract business concepts
- `chart` (16:9) — charts and graphs

**Prompt quality rules:**
- Include company/product-specific details in every prompt (not generic descriptions)
- For org charts: use actual team members' names and roles from source data
- For market charts: mention specific numbers from source data
- Korean language by default (`--lang ko`), use `--lang ko+en` only when mixing is intentional
- Skip photo/signature types (require user-provided files)
- On failure: log warning, continue with other images

#### Step 4b: Insert Images (python-docx)

Read `.dokkit/image_manifest.json` to determine which image goes where. Match images to slots by `field_id` and `purpose`.

Insert generated images into the assembled DOCX using python-docx's `run.add_picture()`:

- **Overview table images**: Match by `field_id` (e.g., field_014, field_015). Find the image row, insert the specific image for each field into the correct cell using `cell.paragraphs[0].add_run().add_picture(path, width=Cm(7))`
- **Section content images**: Match by `purpose` keyword to the section heading. Use `doc.add_picture()` then move the paragraph to the correct position (after the section's last content paragraph)
- All images are centered and sized proportionally
- **Never assign images by filename sort order** — always use the manifest mapping
- **Aspect ratio**: Always measure actual dimensions with PIL, scale to fit while preserving ratio

Report: `Phase 4/6: Generated X images, inserted Y`

### Phase 5: Quality Review & Auto-Fix

**Goal**: Verify document quality and automatically fix issues.

#### Step 5a: Run Quality Gates

Check the filled document XML in `.dokkit/template_work/`:

```
QG1: Total text character count ≥ 7,500
QG2: Each section_content field ≥ 500 chars with specific data
QG3: Zero remaining "00.00" date placeholders
QG4: Zero remaining "OO" name placeholders (OO학, OO기업, OO전자, etc.)
QG5: Zero remaining "이미지 영역" text
QG6: All images sized correctly (aspect ratio within 5% tolerance)
QG7: No red (#FF0000) or italic text in filled cells
QG8: ≥ 10 images in document
```

#### Step 5b: Auto-Fix Failures

For each failed gate, spawn **dokkit-filler** in modify mode with specific fix instructions:

| Failed Gate | Fix Instruction |
|-------------|-----------------|
| QG1/QG2 | "Enrich these sections with more specific data: [list sections with char counts]. Add statistics, market analysis, named competitors, financial projections." |
| QG3 | "Replace these date placeholders with appropriate dates: [list locations]. Derive from project timeline in sources." |
| QG4 | "Replace these name placeholders with real names: [list locations]. Derive from source data context." |
| QG5 | "Remove '이미지 영역' placeholder text at: [list locations]." |
| QG6 | "Re-size these images to preserve aspect ratio: [list images with current vs. correct dimensions]." |
| QG7 | "Sanitize text styles at: [list locations]. Change red to black, remove italic." |
| QG8 | "Generate additional images for sections: [list sections without images]." |

#### Step 5c: Re-Check

After auto-fix, re-run ALL quality gates. Maximum 3 total iterations.

Report: `Phase 5/6: Quality gates — X/8 passed (iteration N/3)`

If all gates pass OR max iterations reached:
- All passed → proceed to export
- Some failed after 3 iterations → proceed to export with warnings about remaining issues

### Phase 6: Export

**Goal**: Produce final document and PDF preview.

1. Spawn **dokkit-exporter** agent:
   > "Export filled document. Format: `<same as input template>`. Compile from `.dokkit/template_work/`, save to `.dokkit/output/`."

2. Generate PDF preview (if LibreOffice available):
   ```bash
   soffice --headless --convert-to pdf --outdir .dokkit/output/ <output_file>
   ```

3. Report final results:
   ```
   ✓ Phase 6/6: Complete

   Output: .dokkit/output/<filename>.<ext>
   Preview: .dokkit/output/<filename>.pdf
   Size: XX MB

   Quality: X/8 gates passed
   Sections: N filled (avg Y chars each)
   Images: M inserted
   Iterations: K

   Next: /dokkit improve to enhance quality further
   ```

---

## Improve Mode

For enhancing the filled document after initial generation: `/dokkit improve ["instruction"]`

The improve command makes the document **better** — richer content, more images, better formatting, stronger persuasiveness. It's not just "modify a field" — it's "make this document more compelling."

1. Check `.dokkit/state.json` for an active filled document
2. If none exists: show error "완성된 문서가 없습니다. 먼저 `/dokkit <template> <sources>` 를 실행하세요."
3. Determine improvement scope:
   - **No instruction**: Full document improvement — enrich all sections, add more images, strengthen weak areas
   - **With instruction**: Targeted improvement in the specified direction
4. Spawn **dokkit-filler** in improve mode:

   **No instruction (full improvement):**
   > "Improve the filled document. Mode: improve.
   > Read ALL source data and the current filled XML. Find areas to strengthen:
   > - Sections with fewer than 800 chars → add more specific data and analysis
   > - Sections without images → identify image opportunities and generate
   > - Weak arguments → add supporting evidence from sources
   > - Generic language → replace with specific statistics, names, organizations
   > - Missing market data → add competitive landscape, market size, growth rates
   > Make the document more persuasive, data-rich, and visually compelling."

   **With instruction (targeted improvement):**
   > "Improve the filled document. Mode: improve. Direction: `<instruction>`.
   > Focus on making the document better in the specified direction.
   > Read source data for additional supporting evidence."

5. Re-run quality gates and auto-fix if needed (max 2 iterations)
6. Re-export the improved document
7. Report what was improved:
   ```
   ✓ Improvement complete

   Changes:
   - 시장분석 섹션: 450자 → 920자 (통계 5개 추가)
   - 이미지 3개 추가 (서비스 구조도, 시장 규모 차트, 팀 조직도)
   - 기술 섹션: 경쟁사 비교 테이블 보강

   Output: .dokkit/output/<filename>.<ext>
   ```

<example>
/dokkit improve                              # 전체적으로 품질 향상
/dokkit improve "이미지를 더 넣어줘"          # 이미지 보강
/dokkit improve "시장분석 섹션을 더 풍부하게"  # 특정 섹션 강화
/dokkit improve "더 설득력 있게"              # 전체 논조 강화
/dokkit improve "예산 테이블을 더 상세하게"    # 특정 테이블 보강
</example>

---

## Error Handling

| Scenario | Action |
|----------|--------|
| Template path missing | Show error with usage: "template과 sources 폴더를 모두 지정해주세요." |
| Sources folder missing | Show error with usage: "sources 폴더를 지정해주세요." |
| Sources folder empty | Show error: "소스 폴더에 파일이 없습니다: `<folder>`" |
| Source file not found | Skip with warning, continue with valid files |
| Template not DOCX/HWPX | Show error: "지원 형식: .docx, .hwpx" |
| Gemini API not configured | Warn, skip image generation, fill text only |
| LibreOffice not available | Skip PDF preview, export in template format only |
| Quality gate stuck after 3 iterations | Export with warnings about remaining issues |
| Agent spawn failure | Show error with agent name and context |

---

## State Management

Read `.dokkit/state.json` before any operation. Update atomically after each phase:

```
Phase 1 → sources[] populated
Phase 2 → template set, analysis created
Phase 3 → filled_document created, sections_filled, fields_filled counts
Phase 4 → images_generated, images_inserted counts
Phase 5 → quality_gates results, iterations_count
Phase 6 → exports[] entry added
```

Validate after every write: `python ${CLAUDE_SKILL_DIR}/scripts/validate_state.py .dokkit/state.json`
