# Filling Knowledge

Field detection, matching strategies, and surgical XML editing rules for the dokkit-filler (and shared with dokkit-analyzer).

## Table of Contents

- [Field Detection Scripts](#field-detection-scripts)
- [Matching Strategy](#matching-strategy)
- [XML Surgery Rules](#xml-surgery-rules)
- [Image Insertion Surgery](#image-insertion-surgery)

---

## Field Detection Scripts

### DOCX Field Detection
```bash
python .claude/skills/dokkit/scripts/detect_fields.py <document.xml>
```
Outputs JSON array of detected fields with labels, types, and XML paths.

### HWPX Field Detection
```bash
python .claude/skills/dokkit/scripts/detect_fields_hwpx.py <section.xml>
```
Same output format, adapted for HWPX XML structure.

### DOCX Validation
```bash
python .claude/skills/dokkit/scripts/validate_docx.py <work_dir>
```

### HWPX Validation
```bash
python .claude/skills/dokkit/scripts/validate_hwpx.py <work_dir>
```

## Matching Strategy

### Step 1: Exact Match
`field.label == source.key` — confidence: high

### Step 2: Normalized Match
Lowercase, strip whitespace, remove punctuation — confidence: high

### Step 3: Semantic Match
"Full Name" matches "Name" — confidence: high
"Phone Number" matches "Contact" — confidence: medium

### Step 4: Cross-Language Match
"성명" matches "Name" — confidence: medium
"주소" matches "Address" — confidence: medium

### Step 5: Context Inference
If field is in "Education" section and source has education data — confidence: low
Generic fields like "비고" (Remarks) — skip or flag

## XML Surgery Rules

### Rule 1: Preserve Run Properties
```xml
<!-- BEFORE -->
<w:r><w:rPr><w:b/><w:sz w:val="24"/></w:rPr><w:t>{{name}}</w:t></w:r>
<!-- AFTER — rPr is IDENTICAL -->
<w:r><w:rPr><w:b/><w:sz w:val="24"/></w:rPr><w:t>John Doe</w:t></w:r>
```

### Rule 2: Handle xml:space
When inserting text with leading/trailing spaces:
```xml
<w:t xml:space="preserve"> John Doe </w:t>
```

### Rule 3: Copy Formatting for Empty Cells
Copy run properties from the label cell. Always sanitize:
```python
label_rPr = label_run.find("w:rPr", ns)
new_run = ET.SubElement(empty_p, "w:r")
if label_rPr is not None:
    new_rPr = copy.deepcopy(label_rPr)
    # Remove red color from guide text
    color_elem = new_rPr.find("w:color", ns)
    if color_elem is not None:
        val = (color_elem.get("{%s}val" % ns["w"]) or "").upper()
        if val in ("FF0000", "FF0000FF", "RED"):
            new_rPr.remove(color_elem)
    # Remove italic from guide text
    italic_elem = new_rPr.find("w:i", ns)
    if italic_elem is not None:
        new_rPr.remove(italic_elem)
    new_run.append(new_rPr)
new_t = ET.SubElement(new_run, "w:t")
new_t.text = value
```

HWPX equivalent: Verify `charPrIDRef` in header.xml does NOT have `textColor="#FF0000"`. If it does, use a black charPr instead (see Rule 6).

### Rule 4: Never Break Table Structure
- Do not add or remove `<w:tc>` elements
- Do not change `<w:gridSpan>` or `<w:vMerge>`
- Only modify content within existing cells

### Rule 5: Tip Box Removal

Before filling fields, remove all `field_type: "tip_box"` entries.

**HWPX standalone** — delete entire `<hp:tbl>`:
```python
ns = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}
tip_pattern = re.compile(r"^※|작성\s?팁|작성\s?요령")

def remove_tip_boxes_hwpx(root):
    to_remove = []
    for tbl in root.iter("{%s}tbl" % ns["hp"]):
        if tbl.get("rowCnt") == "1" and tbl.get("colCnt") == "1":
            text = "".join(t.text or "" for t in tbl.iter("{%s}t" % ns["hp"]))
            if tip_pattern.search(text.strip()):
                to_remove.append(tbl)
    parent_map = {c: p for p in root.iter() for c in p}
    root_children = set(root)
    for tbl in to_remove:
        if tbl in root_children:
            root.remove(tbl)
        else:
            parent = parent_map.get(tbl)
            if parent is not None:
                parent.remove(tbl)
    return len(to_remove)
```

**HWPX nested** — delete only the `<hp:p>` containing the tip (preserve subList):
```python
def remove_nested_tips_hwpx(cell_elem):
    removed = 0
    for sub_list in list(cell_elem.iter("{%s}subList" % ns["hp"])):
        for p_elem in list(sub_list.findall("{%s}p" % ns["hp"])):
            for tbl in p_elem.iter("{%s}tbl" % ns["hp"]):
                if tbl.get("rowCnt") == "1" and tbl.get("colCnt") == "1":
                    text = "".join(t.text or "" for t in tbl.iter("{%s}t" % ns["hp"]))
                    if tip_pattern.search(text.strip()):
                        sub_list.remove(p_elem)
                        removed += 1
                        break
    return removed
```

**DOCX** — delete 1x1 dashed-border tip tables:
```python
def remove_tip_boxes_docx(root):
    ns_w = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    to_remove = []
    for tbl in root.iter("{%s}tbl" % ns_w["w"]):
        rows = list(tbl.iter("{%s}tr" % ns_w["w"]))
        if len(rows) != 1:
            continue
        cells = list(rows[0].iter("{%s}tc" % ns_w["w"]))
        if len(cells) != 1:
            continue
        text = "".join(t.text or "" for t in tbl.iter("{%s}t" % ns_w["w"]))
        if tip_pattern.search(text.strip()):
            to_remove.append(tbl)
    parent_map = {c: p for p in root.iter() for c in p}
    for tbl in to_remove:
        parent = parent_map.get(tbl)
        if parent is not None:
            parent.remove(tbl)
    return len(to_remove)
```

**Post-removal cleanup**: Clear remaining `※`-prefixed runs in fill-target cells:
```python
def clear_residual_tips(cell_elem, ns_prefix):
    for t_elem in cell_elem.iter("{%s}t" % ns_prefix):
        if t_elem.text and t_elem.text.strip().startswith("※"):
            t_elem.text = ""
```

### Rule 6: Color Sanitization

Filled text must always be black. Never inherit red/colored styles from guide text.

**HWPX — find black charPrIDRef**:
```python
def find_black_charpr(header_path):
    hns = {"hh": "http://www.hancom.co.kr/hwpml/2011/head"}
    tree = ET.parse(header_path)
    normal_id = None
    bold_id = None
    for cp in tree.getroot().iter("{%s}charPr" % hns["hh"]):
        color = cp.get("textColor", "#000000").upper()
        if color not in ("#000000", "#000000FF", "BLACK"):
            continue
        italic = cp.get("italic", "false")
        spacing = int(cp.get("spacing", "0"))
        if italic != "false" or spacing < 0:
            continue
        bold = cp.get("bold", "false")
        if bold == "false" and normal_id is None:
            normal_id = cp.get("id")
        elif bold == "true" and bold_id is None:
            bold_id = cp.get("id")
    return {"normal": normal_id, "bold": bold_id}
```

Before inserting any `<hp:run>`, check if the `charPrIDRef` has `textColor="#FF0000"`. If so, use `normal` ID from `find_black_charpr()`.

**DOCX — sanitize copied rPr**:
```python
def sanitize_rpr(rpr_elem, ns):
    if rpr_elem is None:
        return
    color = rpr_elem.find("{%s}color" % ns["w"])
    if color is not None:
        val = color.get("{%s}val" % ns["w"], "").upper()
        if val in ("FF0000", "FF0000FF", "RED"):
            rpr_elem.remove(color)
    italic = rpr_elem.find("{%s}i" % ns["w"])
    if italic is not None:
        rpr_elem.remove(italic)
```

Avoid charPrIDRef with negative `spacing` — causes character overlap.

### Rule 7: Table Template Row Selection (HWPX)

For `table_content` fields, select the right template row for cloning:

**Normal row** — all rowSpan=1, full column count:
```python
def find_normal_template_row(tbl, tr_start, tr_end):
    HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
    rows = tbl.findall(f"{{{HP}}}tr")
    col_cnt = int(tbl.get("colCnt", "3"))
    for i in range(tr_start, min(tr_end + 1, len(rows))):
        row = rows[i]
        text = "".join(t.text or "" for t in row.iter(f"{{{HP}}}t")).strip()
        normalized = text.replace(" ", "").replace("\u3000", "")
        if "합계" in normalized or "소계" in normalized:
            continue
        stripped = text.replace(".", "").replace("…", "").replace(" ", "")
        if not stripped:
            continue
        cells = row.findall(f"{{{HP}}}tc")
        if len(cells) != col_cnt:
            continue
        all_span1 = all(
            int((tc.find(f"{{{HP}}}cellSpan") or {}).get("rowSpan", "1")) == 1
            for tc in cells
            if tc.find(f"{{{HP}}}cellSpan") is not None
        )
        if all_span1:
            return copy.deepcopy(row)
    return None
```

**Fallback with rowSpan stripping**:
```python
def strip_rowspan_from_template(tpl_row):
    HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
    for tc in tpl_row.findall(f"{{{HP}}}tc"):
        cs = tc.find(f"{{{HP}}}cellSpan")
        if cs is not None:
            rs = int(cs.get("rowSpan", "1"))
            if rs > 1:
                cs.set("rowSpan", "1")
                csz = tc.find(f"{{{HP}}}cellSz")
                if csz is not None:
                    old_h = int(csz.get("height", "2129"))
                    csz.set("height", str(old_h // rs))
```

**Summary row detection** — separate 합계/소계 from data rows:
```python
def separate_summary_rows(data_rows):
    regular, summary = [], None
    for row in data_rows:
        label = row[0].strip().replace(" ", "").replace("\u3000", "")
        if label in ("합계", "소계"):
            summary = row
        else:
            regular.append(row)
    return regular, summary
```

Deep-copy original summary row template to preserve colSpan structure.

### Rule 8: SubList Recreation (HWPX)

When writing to a cell with no `<hp:subList>`, recreate one:
```python
def ensure_sublist(tc):
    HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
    for child in tc:
        if child.tag == f"{{{HP}}}subList":
            return child
    sl = ET.SubElement(tc, f"{{{HP}}}subList", {
        "id": "", "textDirection": "HORIZONTAL", "lineWrap": "BREAK",
        "vertAlign": "CENTER", "linkListIDRef": "0", "linkListNextIDRef": "0",
        "textWidth": "0", "textHeight": "0", "hasTextRef": "0", "hasNumRef": "0"
    })
    tc.insert(0, sl)
    return sl
```

Use `ensure_sublist(tc)` when writing to a cell. Append new `<hp:p>` to the returned container.

### Rule 9: cellAddr Re-indexing (HWPX)

After inserting or deleting rows, ALL `<hp:cellAddr rowAddr="N"/>` must equal the 0-based row index:
```python
def fix_celladdr(tbl):
    HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
    for row_idx, tr in enumerate(tbl.findall(f"{{{HP}}}tr")):
        for tc in tr.findall(f"{{{HP}}}tc"):
            addr = tc.find(f"{{{HP}}}cellAddr")
            if addr is not None:
                addr.set("rowAddr", str(row_idx))
    tbl.set("rowCnt", str(len(tbl.findall(f"{{{HP}}}tr"))))
```

Always call after row insertion/deletion. Duplicate rowAddr causes Polaris to silently hide rows.

## Image Insertion Surgery

### DOCX Image Insertion
1. Copy image to `word/media/imageN.ext` (next available number)
2. Add relationship in `word/_rels/document.xml.rels`:
   ```xml
   <Relationship Id="rIdN" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/imageN.png"/>
   ```
3. Add Content_Types entry if extension not registered:
   ```xml
   <Default Extension="png" ContentType="image/png"/>
   ```
4. Insert drawing element in target paragraph:
   ```xml
   <w:r><w:drawing>
     <wp:inline distT="0" distB="0" distL="0" distR="0">
       <wp:extent cx="{width_emu}" cy="{height_emu}"/>
       <wp:docPr id="{uid}" name="Picture {uid}"/>
       <a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
         <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
           <pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
             <pic:blipFill><a:blip r:embed="rIdN"/></pic:blipFill>
             <pic:spPr><a:xfrm><a:ext cx="{width_emu}" cy="{height_emu}"/></a:xfrm></pic:spPr>
           </pic:pic>
         </a:graphicData>
       </a:graphic>
     </wp:inline>
   </w:drawing></w:r>
   ```

### HWPX Image Insertion
1. Copy image to `BinData/imageN.ext` (next available N)
2. Register in `content.hpf` manifest only:
   ```xml
   <opf:item id="imageN" href="BinData/imageN.ext" media-type="image/png" isEmbeded="1"/>
   ```
   Do NOT add `<hh:binDataItems>` to `header.xml`.
3. Insert complete `<hp:pic>` in target cell — see `references/image-xml-patterns.md` for the full element structure.

**Critical HWPX image rules** (all 8 must be followed):
- `<img>` uses `hc:` namespace (NOT `hp:img`)
- `<imgRect>` has 4 `<hc:pt0..3>` children (NOT inline attributes)
- All children required: offset, orgSz, curSz, flip, rotationInfo, renderingInfo, inMargin
- No spurious elements (picSz, picOutline, caption, shapeComment, picRect)
- `imgClip` right/bottom = actual pixel dimensions from PIL (NOT zeros)
- Do NOT add `<hp:lineShape>`
- `hp:pos`: `flowWithText="0"` `horzRelTo="COLUMN"`
- Sequential IDs: find max existing `id` in section XML + 1

### Rule 10: Section Content Table Preservation (DOCX + HWPX)

When filling `section_content` fields, the content range often contains embedded `<w:tbl>` (DOCX) or `<hp:tbl>` (HWPX) elements — schedule tables, budget tables, team rosters. These are handled separately as `table_content` fields.

**NEVER remove or replace table elements during section content filling.** Only operate on paragraph elements (`<w:p>` / `<hp:p>`).

```python
# DOCX: Only remove paragraphs within range, skip tables
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
children = list(body)
for i in range(start_idx, end_idx + 1):
    child = children[i]
    tag = child.tag.split('}')[-1]
    if tag == 'p':
        body.remove(child)  # Replace with new content
    # else: skip — tables, bookmarks, sectPr are preserved
```

## References

See `references/field-detection-patterns.md` for advanced detection heuristics.
See `references/section-range-detection.md` for dynamic section content range detection (HWPX).
See `references/docx-section-range-detection.md` for dynamic section content range detection (DOCX).
See `references/section-image-interleaving.md` for image interleaving algorithm in section content.
See `references/image-xml-patterns.md` for complete image element structures and `build_hwpx_pic_element()`.
