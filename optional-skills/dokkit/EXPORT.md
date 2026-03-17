# Export Knowledge

Document compilation and format conversion for the dokkit-exporter agent.

## Compilation (Repackaging)

### DOCX Compilation
```python
import os, zipfile

def compile_docx(work_dir: str, output_path: str):
    """Repackage a DOCX from its unpacked working directory."""
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(work_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, work_dir)
                zf.write(file_path, arcname)
    return output_path
```

### HWPX Compilation
```python
import os, zipfile

def compile_hwpx(work_dir: str, output_path: str):
    """Repackage HWPX. CRITICAL: mimetype must be first and uncompressed."""
    with zipfile.ZipFile(output_path, 'w') as zf:
        mimetype_path = os.path.join(work_dir, "mimetype")
        if os.path.exists(mimetype_path):
            zf.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)
        for root, dirs, files in os.walk(work_dir):
            for file in sorted(files):
                if file == "mimetype" or file.endswith(".bak"):
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, work_dir)
                zf.write(file_path, arcname, compress_type=zipfile.ZIP_DEFLATED)
    return output_path
```

### Scripts
```bash
python .claude/skills/dokkit/scripts/compile_hwpx.py <work_dir> <output.hwpx>
python .claude/skills/dokkit/scripts/export_pdf.py <input> <output.pdf>
```

## PDF Conversion

### Using LibreOffice
```bash
soffice --headless --convert-to pdf --outdir <output_dir> <input_file>
```

### Using Python Script
```bash
python .claude/skills/dokkit/scripts/export_pdf.py <input> <output.pdf>
```

## Cross-Format Conversion

Use LibreOffice as intermediary:
```bash
soffice --headless --convert-to hwpx --outdir <dir> <input.docx>
soffice --headless --convert-to docx --outdir <dir> <input.hwpx>
```

Cross-format conversion may lose formatting fidelity. Always warn the user.

## Validation

After compilation, verify:
1. Output file is a valid ZIP archive
2. File size is reasonable (> 0 bytes)
3. For DOCX: `[Content_Types].xml` exists at root
4. For HWPX: `mimetype` is first entry and correct value

```python
import zipfile

def validate_archive(path: str, doc_type: str) -> list[str]:
    errors = []
    try:
        with zipfile.ZipFile(path, 'r') as zf:
            names = zf.namelist()
            if doc_type == "docx":
                if "[Content_Types].xml" not in names:
                    errors.append("Missing [Content_Types].xml")
            elif doc_type == "hwpx":
                if not names or names[0] != "mimetype":
                    errors.append("mimetype is not the first entry")
    except zipfile.BadZipFile:
        errors.append("Output is not a valid ZIP archive")
    return errors
```

## Rules

- Never modify filled XML during export — only repackage
- ZIP structure must match original (Content_Types.xml at root for DOCX, mimetype first for HWPX)
- Skip .bak files during HWPX compilation
- Report clear errors if conversion tools unavailable
