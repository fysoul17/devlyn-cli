# Ingestion Knowledge

Parsing strategies and format routing for converting source documents into the dual-file format (Markdown content + JSON sidecar).

## Format Routing

| Format | Parser | Command |
|--------|--------|---------|
| PDF | Docling | `python -m docling <file> --to md` |
| DOCX | Docling | `python -m docling <file> --to md` |
| PPTX | Docling | `python -m docling <file> --to md` |
| HTML | Docling | `python -m docling <file> --to md` |
| CSV | Docling | `python -m docling <file> --to md` |
| MD | Direct copy | Read and process as-is |
| XLSX | Custom | `python .claude/skills/dokkit/scripts/parse_xlsx.py` |
| HWPX | Custom | `python .claude/skills/dokkit/scripts/parse_hwpx.py` |
| JSON | Custom | Read, format as structured markdown |
| TXT | Custom | Read, wrap as markdown |
| PNG/JPG | Gemini Vision | `python .claude/skills/dokkit/scripts/parse_image_with_gemini.py` |

## Docling Usage

Primary parser for most formats:

```bash
python -m docling <input-file> --to md --output <output-dir>
```

After Docling runs:
1. Read the markdown output
2. Extract key-value pairs from the content
3. Build the JSON sidecar with metadata
4. Move files to `.dokkit/sources/`

If Docling is not installed, show an explicit error with install instructions: `pip install docling`. Do NOT silently fall back to a different parser.

## Custom Parser Output Format

All custom parsers output JSON to stdout:
```json
{
  "content_md": "# Document Title\n\nExtracted content...",
  "metadata": {
    "file_name": "original.xlsx",
    "file_type": "xlsx",
    "parse_date": "2026-02-07T12:00:00Z",
    "key_value_pairs": { "Name": "John", "Date": "2026-01-15" },
    "sections": ["Sheet1", "Sheet2"]
  }
}
```

## Key-Value Extraction

After parsing, scan content for structured data:
- Table cells with label-value patterns (e.g., "Name: John Doe")
- Form fields with values
- Metadata headers
- Labeled sections

Store in the JSON sidecar's `key_value_pairs` field for fast lookup during template filling.

## References

See `references/supported-formats.md` for detailed format specifications.
