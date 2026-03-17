# Dokkit Command Reference

Complete workflows for all 9 subcommands. Loaded automatically into context when `/dokkit` is invoked.

## Table of Contents

- [init](#init) — Initialize workspace
- [sources](#sources) — Source dashboard
- [preview](#preview) — PDF preview
- [ingest](#ingest) — Ingest source documents
- [fill](#fill) — End-to-end fill pipeline
- [fill-doc](#fill-doc) — Analyze and fill template
- [modify](#modify) — Targeted changes
- [review](#review) — Confidence review
- [export](#export) — Export to format

---

## init

Initialize or reset the `.dokkit/` workspace for a new document filling session.

### Arguments
- `--force` or `-f`: Skip confirmation and reset without asking
- `--keep-sources`: Reset template/output but preserve ingested sources

### Procedure

1. Check if `.dokkit/` already exists
2. If it exists and `--force` is not passed, ask the user to confirm reset
3. If `--keep-sources` is used, preserve `.dokkit/sources/` and source entries in state.json
4. Create the workspace structure:
   ```
   .dokkit/
   ├── sources/
   ├── template_work/
   ├── output/
   ├── images/
   └── state.json
   ```
5. Initialize `state.json`:
   ```json
   {
     "version": "1.0",
     "created": "<ISO timestamp>",
     "sources": [],
     "template": null,
     "analysis": null,
     "filled_document": null,
     "exports": []
   }
   ```
6. Validate the state file
7. Report success with next step guidance

### Output
```
Dokkit workspace initialized at .dokkit/
  sources/       — ready for /dokkit ingest
  template_work/ — ready for /dokkit fill
  output/        — ready for /dokkit export
  state.json     — initialized

Next: Use /dokkit ingest <file> to add source documents.
```

### Rules
- Inline command — do NOT fork to any agent
- If resetting, warn about data loss unless --force is used

---

## sources

Display all ingested source documents with their status, type, and summary.

### Procedure

1. Read `.dokkit/state.json`
2. If `.dokkit/` does not exist, show error: "No workspace found. Run `/dokkit init` first."
3. If no sources exist, show empty state with supported formats list
4. For each source, display: name, type, status, summary
5. Show total count and any errors

### Output
```
Ingested Sources (3 total)

 #  Name                Type   Status   Summary
 1  resume.pdf          PDF    ready    Personal resume with education and work history
 2  transcript.xlsx     XLSX   ready    Academic transcript with grades and courses
 3  scan.png            PNG    error    OCR failed — image too blurry

Use /dokkit ingest <file> to add more sources.
```

### Rules
- Inline command — do NOT fork to any agent
- Read-only: only reads state.json, never modifies anything

---

## preview

Generate a visual preview of the current filled document as PDF.

### Procedure

1. Read `.dokkit/state.json` to check document status
2. If no filled document exists, show error: "No filled document. Run `/dokkit fill <template>` first."
3. Compile the current `template_work/` into a temporary file
4. Convert to PDF using LibreOffice: `soffice --headless --convert-to pdf --outdir .dokkit/output/ <file>`
5. Report the preview file path

### Output
```
Preview generated: .dokkit/output/preview_<name>.pdf
Open this file to see how the filled document looks.
```

### Rules
- Inline command — do NOT fork to any agent
- If LibreOffice is not available, show error with install guidance
- Preview is temporary — `/dokkit export` creates the final output

---

## ingest

Parse one or more source documents and add them to the workspace for template filling.

### Arguments
One or more file paths (space-separated or comma-separated).

<example>
`/dokkit ingest docs/resume.pdf`
`/dokkit ingest docs/resume.pdf docs/financials.xlsx docs/photo.jpg`
</example>

### Procedure

1. Parse remaining arguments to extract file paths
2. Validate each file path exists. Show error for missing files, continue with valid ones.
3. **Auto-initialize workspace**: If `.dokkit/` does not exist, create it with initial state.json. Report: "Workspace initialized at .dokkit/"
4. **Ingest each file** sequentially by spawning the **dokkit-ingestor** agent:
   - Pass the file path as context
   - The agent parses the file, writes to `.dokkit/sources/`, updates `state.json`
   - Report progress: "Ingested 1/3: resume.pdf (ready)"
5. **Show sources dashboard** after all files complete

### Delegation
For each file, spawn the dokkit-ingestor agent:
> "Ingest the source document at `<file_path>`. Follow the dokkit-ingestor agent instructions. The workspace is at `.dokkit/`."

### Rules
- Auto-initialize workspace if `.dokkit/` does not exist — do NOT tell user to run `/dokkit init`
- Supported formats: PDF, DOCX, XLSX, CSV, PPTX, HWPX, PNG, JPG, TXT, MD, JSON, HTML
- If a format is unsupported, show error with supported formats list and skip that file
- If no valid files are provided, show error with usage example
- Always show sources dashboard after ingestion completes

---

## fill

Fully automated document filling pipeline: analyze, fill, review, auto-fix, and export in one step.

### Arguments
File path to the template document (DOCX or HWPX).

<example>
`/dokkit fill docs/template.hwpx`
`/dokkit fill form.docx`
</example>

### Procedure

**Phase 1 — Validate**:
1. Validate the template exists and is DOCX or HWPX
2. Check `.dokkit/` workspace exists — if not, show error: "No workspace found. Run `/dokkit ingest <files>` first."
3. Check at least one source has status "ready" — if not, show error: "No sources ingested."
4. Report: "Starting fill pipeline with N sources -> template_name"

**Phase 2 — Analyze**:
5. Spawn the **dokkit-analyzer** agent to detect fields, map to sources, write `analysis.json`
6. Report: "Found N fields (X mapped, Y unmapped, Z images)"

**Phase 3 — Source Images**:
7. **Cell-level images**: For each `field_type: "image"` with `image_file: null` and `image_type: "figure"`:
   - Run: `python scripts/source_images.py generate --prompt "<prompt>" --preset technical_illustration --output-dir .dokkit/images/ --project-dir . --lang ko`
   - Parse `__RESULT__` JSON, update `analysis.json`
   - Skip photo/signature types (require user-provided files)
   - Default `--lang ko` (Korean only). Override with user instruction if needed.
8. **Section content images**: For each `image_opportunities` entry with `status: "pending"`:
   - Run: `python scripts/source_images.py generate --prompt "<generation_prompt>" --preset <preset> --output-dir .dokkit/images/ --project-dir . --lang ko`
   - On failure: set `status: "skipped"`, log reason
   - Use `--lang ko+en` if the content contains technical terms that benefit from English (e.g., architecture diagrams with API names).
9. Report: "Sourced X/Y images"

**Phase 4 — Fill**:
10. Spawn the **dokkit-filler** agent in fill mode

**Phase 5 — Review and Auto-Fix Loop**:
11. Evaluate fill result: count fields by confidence, identify fixable issues
12. **Auto-fix**: For fixable issues, spawn **dokkit-filler** in modify mode
    - Re-map low-confidence fields where better data exists
    - Fix formatting issues (date formats, truncated text)
    - Do NOT auto-fix: unfilled fields, image fields without sources
13. If auto-fix made changes, re-evaluate. Maximum 2 iterations.
14. Present **final review** table (section-by-section with confidence)

**Phase 6 — Export**:
15. Export in same format as input template via **dokkit-exporter** agent
16. Report output path and file size

**Phase 7 — Next Steps**:
17. Offer: `/dokkit modify "..."`, `/dokkit export pdf`, `/dokkit review`

### Delegation

**Agent 1 — Analyzer** (dokkit-analyzer):
> "Analyze the template at `<path>`. Detect all fillable fields INCLUDING image fields. Map to sources. Write `analysis.json`."

**Agent 2 — Filler** (dokkit-filler, fill mode):
> "Fill the template using `analysis.json`. Mode: fill. Insert images where `image_file` is populated. Interleave section content images at anchor points."

**Agent 2b — Filler** (dokkit-filler, modify mode — auto-fix, if needed):
> "Modify the filled document. Mode: modify. Fix: `<list of issues>`."

**Agent 3 — Exporter** (dokkit-exporter):
> "Export the filled document. Format: `<format>`. Compile from `.dokkit/template_work/` and save to `.dokkit/output/`."

### Rules
- At least one source must be ingested before filling
- Auto-fix loop runs maximum 2 iterations
- Auto-fix does NOT fill fields with missing source data
- Always show the full review table before exporting
- If any phase fails, show the error and stop — do NOT proceed

---

## fill-doc

Analyze a template and fill its fields using ingested source data. Does NOT auto-fix or export.

### Arguments
File path to the template document (DOCX or HWPX).

<example>
`/dokkit fill-doc docs/template.docx`
</example>

### Procedure

1. Validate the template exists and is DOCX or HWPX
2. Check `.dokkit/` workspace exists with at least one ready source
3. **Analyze**: Spawn the **dokkit-analyzer** agent
4. **Source Images**: Same as `/dokkit fill` Phase 3 (cell-level + section content)
5. **Fill**: Spawn the **dokkit-filler** agent in fill mode
6. Present review summary

### Delegation

**First**: Spawn the dokkit-analyzer agent:
> "Analyze the template at `<path>`. Detect all fillable fields INCLUDING image fields. Map to sources. Write `analysis.json`."

**Image sourcing** (inline, between agents):
- **Pass A — Cell-level**: For `field_type: "image"` with `image_file: null` and `image_type: "figure"`, run `python scripts/source_images.py generate --prompt "..." --preset ... --output-dir .dokkit/images/ --project-dir . --lang ko`
- **Pass B — Section content**: For `image_opportunities` with `status: "pending"`, run `python scripts/source_images.py generate --prompt "..." --preset ... --output-dir .dokkit/images/ --project-dir . --lang ko`
- Default language is `ko` (Korean only). Use `--lang ko+en` for mixed content, or `--lang en` for English-only.

**Then**: Spawn the dokkit-filler agent in fill mode:
> "Fill the template using `analysis.json`. Mode: fill. Insert images where populated. Interleave section content images at anchor points."

### Rules
- Template must be DOCX or HWPX
- Analyzer runs FIRST, then filler
- Original template is never modified

---

## modify

Apply targeted changes to the filled document based on natural language instructions.

### Arguments
A natural language instruction describing the change.

<example>
`/dokkit modify "Change the phone number to 010-1234-5678"`
`/dokkit modify "Re-do the education section using the transcript"`
`/dokkit modify "Use YYYY-MM-DD format for all dates"`
</example>

### Procedure

1. Check `.dokkit/state.json` for an active filled document. If none, show error: "No filled document. Run `/dokkit fill <template>` first."
2. Spawn the **dokkit-filler** agent in modify mode

### Delegation
> "Modify the filled document. Mode: modify. User instruction: `<instruction>`. Read `analysis.json` for field locations and make surgical changes."

### Rules
- A filled document must exist
- Only modify targeted fields — do not re-process the entire document
- Manual overrides get confidence "high"

---

## review

Present the filled document for review with section-by-section confidence annotations.

### Arguments
Optional: section name or action.

<example>
`/dokkit review` — review all sections
`/dokkit review "Personal Information"` — review specific section
`/dokkit review approve` — mark document as finalized
</example>

### Procedure

1. Check `.dokkit/state.json` for an active filled document. If none, show error.
2. Spawn the **dokkit-filler** agent in review mode

### Delegation
> "Review the filled document. Mode: review. Read `analysis.json` and present section-by-section review with confidence annotations."

If section or action specified:
> "Focus on section: `<section>` / Action: `<action>`"

### Rules
- A filled document must exist
- Review is read-only — shows status but changes nothing
- "approve" action sets document status to "finalized"

---

## export

Compile and export the filled document in the specified format.

### Arguments
Output format: `docx`, `hwpx`, or `pdf`.

<example>
`/dokkit export docx`
`/dokkit export pdf`
</example>

### Procedure

1. Check `.dokkit/state.json` for a filled document. If none, show error.
2. Validate the requested format is supported
3. Spawn the **dokkit-exporter** agent

### Delegation
> "Export the filled document. Format: `<format>`. Compile from `.dokkit/template_work/` and save to `.dokkit/output/`."

### Rules
- Supported formats: docx, hwpx, pdf
- Cross-format exports show a warning about potential formatting differences
- Same-format exports preserve 100% formatting fidelity
