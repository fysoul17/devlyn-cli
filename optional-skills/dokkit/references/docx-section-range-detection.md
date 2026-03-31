# Section Content Range Detection (DOCX)

## Problem

Same as HWPX: after deleting instruction text (※ paragraphs) and tip boxes, the child indices from `analysis.json` become stale. Using stale indices destroys tables and other structural elements.

**Additionally**, DOCX section content ranges may contain embedded `<w:tbl>` elements (schedule tables, budget tables) that must NEVER be replaced during section content filling. Unlike HWPX where tables are children of the section root, DOCX tables are direct children of `<w:body>` interspersed with paragraphs.

## Solution: Dynamic Range Detection + Table Preservation

### Step 1: Recompute ranges after cleanup

After deleting instruction text and tip boxes, scan `<w:body>` children for section title markers:

```python
def find_docx_section_ranges(body, w_ns):
    """Find section content ranges by locating title markers in w:body.

    Must run AFTER tip/instruction deletion so indices are stable.
    Returns dict mapping approximate field labels to (start, end) inclusive child index ranges.
    """
    children = list(body)
    markers = {}

    for i, child in enumerate(children):
        text = ''.join(
            t.text or '' for t in child.iter(f'{{{w_ns}}}t')
        ).strip()

        # Section title markers (numbered headings)
        if '1.' in text and '문제' in text and ('Problem' in text or '필요성' in text):
            markers['sec1_title'] = i
        elif '2.' in text and '실현' in text and ('Solution' in text or '개발' in text):
            markers['sec2_title'] = i
        elif '3.' in text and '성장' in text and ('Scale' in text or '사업화' in text):
            markers['sec3_title'] = i
        elif '4.' in text and '팀' in text and ('Team' in text or '대표자' in text):
            markers['sec4_title'] = i

        # End markers
        elif '사업추진' in text and '일정' in text and '협약기간' in text:
            markers['schedule1'] = i
        elif '사업추진' in text and '일정' in text and '전체' in text:
            markers['schedule2'] = i
        elif '팀 구성' in text and ('구분' in text or '직위' in text or '안' in text):
            markers['team_table'] = i
        elif '협력' in text and '기관' in text:
            markers['partnership'] = i

    # Build ranges: content starts after title + instruction text, ends before next structural element
    ranges = {}
    if 'sec1_title' in markers and 'sec2_title' in markers:
        ranges['sec1'] = (markers['sec1_title'] + 1, markers['sec2_title'] - 1)
    if 'sec2_title' in markers and 'schedule1' in markers:
        ranges['sec2'] = (markers['sec2_title'] + 1, markers['schedule1'] - 1)
    if 'sec3_title' in markers and 'schedule2' in markers:
        ranges['sec3'] = (markers['sec3_title'] + 1, markers['schedule2'] - 1)
    if 'sec4_title' in markers and 'team_table' in markers:
        ranges['sec4'] = (markers['sec4_title'] + 1, markers['team_table'] - 1)

    return ranges
```

### Step 2: CRITICAL — Only replace paragraphs, never tables

When filling section content within the detected range, ONLY operate on `<w:p>` elements. **Skip all other element types**:

```python
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

def fill_docx_section_content(body, start_idx, end_idx, new_paragraphs):
    """Replace paragraph content within a section range, preserving tables.

    RULE: Only remove/replace <w:p> elements. NEVER touch <w:tbl>, <w:bookmarkStart>,
    <w:bookmarkEnd>, <w:sectPr>, or any non-paragraph elements.
    """
    children = list(body)

    # Phase 1: Identify which children to remove (paragraphs only)
    to_remove = []
    preserved_elements = []  # (index, element) pairs for tables etc.

    for i in range(start_idx, min(end_idx + 1, len(children))):
        child = children[i]
        tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag

        if tag == 'p':
            to_remove.append(child)
        else:
            # Tables, bookmarks, sectPr — preserve in their position
            preserved_elements.append((i, child))

    # Phase 2: Remove old paragraphs
    for elem in to_remove:
        body.remove(elem)

    # Phase 3: Insert new paragraphs at the start of the range
    # (preserved tables remain in place)
    insert_point = start_idx
    for new_p in new_paragraphs:
        body.insert(insert_point, new_p)
        insert_point += 1
```

### Why Tables Must Be Preserved

The 예비창업패키지 사업계획서 template has this structure within `<w:body>`:

```
[19] p: "1. 문제 인식 (Problem)..." — section title
[20] p: "※ 개발하고자 하는..." — instruction text (delete)
[21-60] p: section content paragraphs (replace)
[61] p: "2. 실현 가능성 (Solution)..." — section title
[62] p: "※ 아이디어를..." — instruction text (delete)
[63-82] p: section content paragraphs (replace)
[83] p: "< 사업추진 일정(협약기간 내) >" — schedule heading
[85] tbl: schedule table ← MUST PRESERVE
[91] tbl: budget table 1 ← MUST PRESERVE
[96] tbl: budget table 2 ← MUST PRESERVE
```

If the filler replaces the entire range including tables, the schedule and budget data is destroyed. The tables are handled separately as `table_content` fields.

### Form Tables vs Section Content

The following tables are NOT section content — they are form-filling tables with individual cell fields:

| Body index | Content | Field type |
|-----------|---------|------------|
| 13 | 일반현황 table (창업아이템명, 산출물) | `empty_cell` per cell |
| 17 | 개요(요약) table (명칭, 범주, etc.) | `empty_cell` per cell |
| 85 | 사업추진 일정 (협약기간) | `table_content` |
| 91 | 1단계 정부지원사업비 | `table_content` |
| 96 | 2단계 정부지원사업비 | `table_content` |
| 140 | 사업추진 일정 (전체) | `table_content` |
| 160 | 팀 구성 table | `table_content` |
| 164 | 협력 기관 table | `table_content` |

The analyzer must classify these as their specific field types. They should NEVER be included in a `section_content` field's range.

## Adapting for Different Templates

Same as the HWPX version — identify section title markers, match by text content, map to field IDs. The key difference for DOCX:

1. Body children are direct `<w:p>` and `<w:tbl>` elements (flat structure)
2. Tables are interspersed with paragraphs at the same level
3. The "only replace `<w:p>`" rule is universal and template-independent
