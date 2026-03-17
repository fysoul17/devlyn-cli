# DOCX XML Knowledge

Open XML structure for surgical DOCX document editing.

## DOCX Structure

A DOCX file is a ZIP archive:
```
[Content_Types].xml          — MIME type mappings
_rels/.rels                  — root relationships
word/
  document.xml               — main document body (PRIMARY TARGET)
  styles.xml                 — style definitions
  numbering.xml              — list numbering definitions
  settings.xml               — document settings
  fontTable.xml              — font declarations
  theme/theme1.xml           — theme colors/fonts
  media/                     — embedded images
  _rels/document.xml.rels    — document relationships
docProps/
  app.xml                    — application metadata
  core.xml                   — document metadata
```

## Key XML Elements

### Namespace
```xml
xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
```

### Document Body
```xml
<w:body>
  <w:p>           <!-- paragraph -->
    <w:pPr>       <!-- paragraph properties -->
    <w:r>         <!-- run (text with formatting) -->
      <w:rPr>     <!-- run properties (font, size, bold, etc.) -->
      <w:t>       <!-- text content -->
    </w:r>
  </w:p>
</w:body>
```

### Tables
```xml
<w:tbl>
  <w:tblPr>       <!-- table properties -->
  <w:tblGrid>     <!-- column widths -->
  <w:tr>           <!-- table row -->
    <w:trPr>       <!-- row properties -->
    <w:tc>         <!-- table cell -->
      <w:tcPr>     <!-- cell properties (width, merge, borders) -->
      <w:p>        <!-- cell content (paragraph) -->
    </w:tc>
  </w:tr>
</w:tbl>
```

### Content Controls (Structured Document Tags)
```xml
<w:sdt>
  <w:sdtPr>
    <w:alias w:val="FieldName"/>
    <w:tag w:val="field_tag"/>
  </w:sdtPr>
  <w:sdtContent>
    <w:p><w:r><w:t>Placeholder</w:t></w:r></w:p>
  </w:sdtContent>
</w:sdt>
```

## References

See `references/docx-structure.md` for unpacking, repackaging, and critical rules.
See `references/docx-field-patterns.md` for field detection patterns (placeholders, empty cells, underline, content controls, instruction text, tip boxes).
