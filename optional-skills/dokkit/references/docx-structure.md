# DOCX XML Structure Reference

## Unpacking a DOCX

```bash
# Unzip to inspect
mkdir -p .dokkit/template_work
cd .dokkit/template_work
unzip -o /path/to/template.docx
```

## Reading document.xml

The main content is in `word/document.xml`. Parse with any XML parser.

### Python Example
```python
import xml.etree.ElementTree as ET

ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
tree = ET.parse("word/document.xml")
root = tree.getroot()

# Find all paragraphs
for p in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
    texts = []
    for t in p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"):
        if t.text:
            texts.append(t.text)
    print("".join(texts))
```

## Repackaging a DOCX

After modifying XML, repackage as a valid DOCX:

```python
import zipfile
import os

def repackage_docx(work_dir, output_path):
    """Repackage modified XML files into a valid DOCX."""
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(work_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, work_dir)
                zf.write(file_path, arcname)
```

## Critical Rules for DOCX Surgery

1. **Never remove `<w:rPr>` elements** — they contain all formatting
2. **Preserve `xml:space="preserve"`** on `<w:t>` elements with leading/trailing spaces
3. **Keep `<w:pPr>` intact** — paragraph formatting must not change
4. **Maintain bookmark pairs** — `<w:bookmarkStart>` must have matching `<w:bookmarkEnd>`
5. **Don't modify `<w:sectPr>`** — section properties control page layout
6. **Preserve table cell merge attributes** — `<w:vMerge>` and `<w:gridSpan>`
