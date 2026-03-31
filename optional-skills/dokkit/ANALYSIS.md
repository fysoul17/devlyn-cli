# Analysis Knowledge

Template analysis patterns and field detection strategies for the dokkit-analyzer agent. Covers field identification, confidence scoring, and the analysis output schema.

## Table of Contents

- [Field Detection Strategy](#field-detection-strategy)
- [Section Detection](#section-detection)
- [Cross-Language Mapping](#cross-language-mapping)
- [Confidence Scoring](#confidence-scoring)
- [Analysis Output Format](#analysis-output-format)

---

## Field Detection Strategy

Detect ALL fillable locations in a template. Fields appear in these patterns:

### 1. Placeholder Text
- `{{field_name}}` or `<<field_name>>` — explicit placeholders
- `[field_name]` or `(field_name)` — bracket patterns
- `___` (underscores) — blank line indicators
- `...` (dots) — fill-in indicators

### 2. Empty Table Cells
In form-like documents (especially Korean templates):
- A label cell (e.g., "Name") with an adjacent empty cell = fill target
- Pattern: `[Label Cell] [Empty Cell]`

### 3. Instruction Text
Text telling the user what to enter:
- "(enter name here)", "(type your answer)"
- Korean: "(날짜를 입력하세요)", "(내용을 기재)"
- These should be REPLACED with the actual value

### 4. Form Controls (DOCX only)
- Content controls (`w:sdt`) with explicit placeholder values
- Legacy form fields (`w:fldChar`)

### 5. Underline Runs
Runs styled with underline containing only spaces or underscores:
- Indicates a blank line for handwriting
- In digital filling, replace with the value

### 6. Image Fields
Fields requiring an image rather than text:
- `{{사진}}`, `{{photo}}`, `<<signature>>` — image placeholder text
- Existing `<w:drawing>` (DOCX) or `<hp:pic>` (HWPX) in table cells
- Empty cells adjacent to cells with image keywords

**Image keywords** (Korean): 사진, 증명사진, 여권사진, 로고, 서명, 날인, 도장, 직인
**Image keywords** (English): Photo, Picture, Logo, Signature, Stamp, Seal, Image, Portrait

**Classification** (`image_type`): `photo`, `logo`, `signature`, or `figure`

### 7. Writing Tip Boxes (작성 팁)
Standalone 1x1 tables with DASH borders containing guidance text:
- HWPX: `rowCnt="1"`, `colCnt="1"` with `※` text
- DOCX: Single `<w:tr>/<w:tc>` with dashed borders
- Often styled in red (#FF0000)

Detect as `field_type: "tip_box"` with `action: "delete"`.

**Container types**:
- `"standalone"` — top-level 1x1 table between other content
- `"nested"` — inside `<hp:subList>` within a fill-target cell; include `parent_field_id`

**`has_formatting` flag**: For mapped fields where `mapped_value` is >100 chars and contains markdown syntax (`**bold**`, `## heading`, `- bullet`, `1. numbered`), set `has_formatting: true`.

### 8. Korean Template Placeholder Patterns
These patterns indicate unfilled fields that MUST be replaced with real values:
- `OO` (더블 O) — placeholder for names, organizations, fields of study (e.g., "OO학", "OO기업", "OO전자")
- `00.00` — placeholder for dates (e.g., "00.00 ~ 00.00" means "MM.YY ~ MM.YY")
- `00명` / `00개` / `00년` — placeholder for counts/durations
- `000원` / `0,000,000` — placeholder for amounts
- `'00.00` — placeholder for dates in parenthetical context (e.g., "완료('00.00)")

These are NOT empty cells — they contain placeholder text that looks like data. The analyzer MUST detect them and map real values from source context.

## Section Content Quality Standards

For `section_content` fields (the narrative body of each numbered section), the `mapped_value` must be a **complete, professional-quality narrative** — NOT raw data extracts.

### What "good" section content looks like:
- 500+ characters per section minimum
- Specific statistics from survey/research data (e.g., "83%가 사용 의향", "월 9,900원")
- Named organizations (e.g., "한국난독증협회", "웅진씽크빅")
- Concrete implementation plans with phases
- Market analysis with TAM/SAM/SOM numbers
- Sub-sections following the template's `◦` heading structure
- Evidence-based claims with source attribution

### What "bad" section content looks like:
- Just the template headings without substance
- Raw bullet points from source data without synthesis
- Generic descriptions without specific numbers
- Placeholder text remaining (OO, 00.00)
- Less than 200 characters

## Section Detection

Group fields into logical sections:
1. Use document headings (H1, H2) as section boundaries
2. In table-based forms, use spanning header rows
3. In Korean templates, look for: "인적사항", "학력", "경력", "자격증"
4. If no clear sections, use "General" as default

## Cross-Language Mapping

Common Korean-English field equivalents:

| Korean | English |
|--------|---------|
| 성명 / 이름 | Name / Full Name |
| 생년월일 | Date of Birth |
| 주소 | Address |
| 전화번호 / 연락처 | Phone / Contact |
| 이메일 | Email |
| 학력 | Education |
| 경력 | Work Experience |
| 자격증 | Certifications |
| 직위 / 직책 | Position / Title |
| 회사명 | Company Name |
| 기간 | Period / Duration |

## Confidence Scoring

### High Confidence
- Exact label match between source and template field
- Unambiguous data (one clear value in sources)
- Same language label match

### Medium Confidence
- Semantic match (different wording, same meaning)
- Cross-language match (Korean-English)
- Multiple candidate values in sources
- Partial data match

### Low Confidence
- Indirect inference (value derived from context)
- Ambiguous mapping (could match multiple fields)
- Best guess from limited data

## Analysis Output Format

Write to `.dokkit/analysis.json`:

```json
{
  "template": {
    "file_path": "...",
    "file_type": "docx|hwpx",
    "display_name": "..."
  },
  "sections": [
    {
      "name": "Section Name",
      "fields": [
        {
          "id": "field_001",
          "label": "Field Label",
          "field_type": "placeholder_text|empty_cell|underline|form_control|instruction_text|image|tip_box|section_content|table_content",
          "xml_path": {
            "file": "word/document.xml",
            "element_path": "body/tbl[0]/tr[1]/tc[2]/p[0]/r[0]",
            "namespaced_path": "w:body/w:tbl[0]/w:tr[1]/w:tc[2]/w:p[0]/w:r[0]"
          },
          "pattern": "{{name}}",
          "current_content": "{{name}}",
          "mapped_value": "John Doe",
          "source": "resume.pdf",
          "source_location": "key_value_pairs.Name",
          "confidence": "high",
          "has_formatting": false
        },
        {
          "id": "field_015",
          "label": "tip box label",
          "field_type": "tip_box",
          "action": "delete",
          "container": "standalone",
          "xml_path": { "file": "...", "element_path": "...", "namespaced_path": "..." },
          "pattern": "(tip box: 1x1 table)",
          "current_content": "※ 작성 팁: ...",
          "mapped_value": null,
          "confidence": "high"
        },
        {
          "id": "field_020",
          "label": "사진",
          "field_type": "image",
          "image_type": "photo",
          "xml_path": { "file": "...", "element_path": "...", "namespaced_path": "..." },
          "pattern": "(empty cell, image label)",
          "current_content": "",
          "image_source": "ingested",
          "image_file": ".dokkit/sources/photo.jpg",
          "dimensions": { "width_emu": 1260000, "height_emu": 1620000 },
          "confidence": "high"
        }
      ]
    }
  ],
  "summary": {
    "total_fields": 22,
    "mapped": 18,
    "unmapped": 4,
    "high_confidence": 15,
    "medium_confidence": 2,
    "low_confidence": 1,
    "image_fields": 2,
    "image_fields_sourced": 1,
    "image_fields_pending": 1,
    "tip_boxes": 3,
    "section_image_opportunities": 6
  }
}
```

### Critical Rules for Analysis Output

- For `table_content` fields that are pre-filled from source: set `mapped_value: null` with `action: "preserve"`. NEVER set `mapped_value` to a placeholder string — the filler treats any non-null `mapped_value` as literal data and will destroy the table.
- For `image` fields: search `.dokkit/sources/` for matching images first. Set `image_source: "ingested"` if found, or leave `image_file: null` (pending).
- For `section_content` fields: scan for visual enhancement opportunities (max 3 per field, max 12 total). Record with `generation_prompt`, `dimensions`, `status: "pending"`.

## References

See `references/field-detection-patterns.md` for advanced detection heuristics (9 DOCX + 6 HWPX).
See `references/image-opportunity-heuristics.md` for AI image opportunity detection in section content.
