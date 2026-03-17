# DOCX Field Detection Patterns

## Pattern 1: Placeholder Text

```xml
<!-- Text like {{name}} or <<name>> in a run -->
<w:r>
  <w:rPr>
    <w:rFonts w:ascii="Arial" w:hAnsi="Arial"/>
    <w:sz w:val="20"/>
  </w:rPr>
  <w:t>{{full_name}}</w:t>  <!-- REPLACE this text content -->
</w:r>
```

**Action**: Replace the text content of `<w:t>` while preserving `<w:rPr>`.

## Pattern 2: Empty Table Cell

```xml
<w:tr>
  <w:tc>
    <w:p><w:r><w:t>Name</w:t></w:r></w:p>  <!-- Label cell -->
  </w:tc>
  <w:tc>
    <w:p/>  <!-- Empty cell → FILL THIS -->
  </w:tc>
</w:tr>
```

**Action**: Insert `<w:r><w:t>value</w:t></w:r>` into the empty `<w:p>`. Copy `<w:rPr>` from the label cell's run to match formatting.

## Pattern 3: Underline Placeholder

```xml
<w:r>
  <w:rPr>
    <w:u w:val="single"/>
  </w:rPr>
  <w:t xml:space="preserve">          </w:t>  <!-- Spaces with underline -->
</w:r>
```

**Action**: Replace the spaces in `<w:t>` with the actual value. Keep `<w:u>` in `<w:rPr>`.

## Pattern 4: Content Control

```xml
<w:sdt>
  <w:sdtPr>
    <w:alias w:val="Company Name"/>
    <w:tag w:val="company"/>
    <w:showingPlcHdr/>  <!-- Indicates placeholder is showing -->
  </w:sdtPr>
  <w:sdtContent>
    <w:p>
      <w:r>
        <w:rPr><w:rStyle w:val="PlaceholderText"/></w:rPr>
        <w:t>Click here to enter text.</w:t>
      </w:r>
    </w:p>
  </w:sdtContent>
</w:sdt>
```

**Action**: Replace the run inside `<w:sdtContent>` with a new run containing the value. Remove `<w:showingPlcHdr/>` from `<w:sdtPr>`. Remove the placeholder style from `<w:rPr>`.

## Pattern 5: Instruction Text

```xml
<w:r>
  <w:rPr>
    <w:color w:val="808080"/>  <!-- Gray text -->
    <w:i/>                      <!-- Italic -->
  </w:rPr>
  <w:t>(enter your name)</w:t>
</w:r>
```

**Action**: Replace text content. Change `<w:rPr>` to remove gray color and italic (or copy from a nearby filled field).

## Pattern 6: Writing Tip Box (작성 팁)

Single-cell tables with dashed borders containing `※` guidance text. These are NOT fillable — they must be **deleted**.

```xml
<w:tbl>
  <w:tblPr>
    <w:tblBorders>
      <w:top w:val="dashed" w:sz="4" w:space="0" w:color="auto"/>
      <w:left w:val="dashed" w:sz="4" w:space="0" w:color="auto"/>
      <w:bottom w:val="dashed" w:sz="4" w:space="0" w:color="auto"/>
      <w:right w:val="dashed" w:sz="4" w:space="0" w:color="auto"/>
    </w:tblBorders>
  </w:tblPr>
  <w:tr>
    <w:tc>
      <w:p>
        <w:r>
          <w:rPr><w:color w:val="FF0000"/></w:rPr>
          <w:t>※ 작성 팁: 구체적인 사업 목표를 기재하세요.</w:t>
        </w:r>
      </w:p>
    </w:tc>
  </w:tr>
</w:tbl>
```

**Identifying traits**:
- Single row, single cell (`<w:tr>` has one `<w:tc>`)
- `<w:tblBorders>` with `w:val="dashed"` on all sides
- Text starts with `※` or contains `작성 팁`, `작성요령`
- Often has red `<w:color w:val="FF0000"/>` styling

**Action**: Flag as `field_type: "tip_box"`, `action: "delete"`. Delete the entire `<w:tbl>` element.

## Color Warning for Copied Formatting

When copying `<w:rPr>` from template guide text or instruction text (Patterns 2 and 5), **always check for red color**:

```xml
<!-- DANGER: This rPr has red color from guide text -->
<w:rPr>
  <w:color w:val="FF0000"/>  <!-- REMOVE THIS -->
  <w:i/>                      <!-- REMOVE THIS (from guide text) -->
  <w:sz w:val="20"/>          <!-- KEEP -->
</w:rPr>
```

**Rule**: After copying rPr from any template text, check for `<w:color>` elements. If the value is `FF0000`, `FF0000FF`, or any red shade, **remove the `<w:color>` element** (defaults to black). Also remove `<w:i/>` if it came from guide text.

## Safe Modification Template

```python
import xml.etree.ElementTree as ET

ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
ET.register_namespace("w", ns["w"])

tree = ET.parse("word/document.xml")

# Find and replace placeholder text
for t_elem in tree.iter("{%s}t" % ns["w"]):
    if t_elem.text and "{{" in t_elem.text:
        placeholder = t_elem.text  # e.g., "{{name}}"
        field_name = placeholder.strip("{}").strip("<>")
        if field_name in field_values:
            t_elem.text = field_values[field_name]

tree.write("word/document.xml", xml_declaration=True, encoding="UTF-8")
```
