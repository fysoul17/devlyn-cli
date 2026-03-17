# Supported Source Formats

## Docling-Supported Formats

### PDF
- Text PDFs: direct text extraction
- Scanned PDFs: OCR via Docling's built-in OCR
- Mixed PDFs: handles both text and image regions
- Tables: extracted as markdown tables

### DOCX (Microsoft Word)
- Paragraphs, headings, lists
- Tables with merged cells
- Embedded images (extracted as descriptions)
- Headers/footers

### PPTX (PowerPoint)
- Slide content as sections
- Speaker notes included
- Tables and charts (text content)

### HTML
- Semantic structure preserved
- Tables converted to markdown
- Links and formatting extracted

### CSV
- Converted to markdown table
- Headers auto-detected

### MD (Markdown)
- Passed through with minimal processing
- Metadata extracted from frontmatter if present

## Custom-Parsed Formats

### XLSX (Excel)
- Multiple sheets → separate sections
- Tables preserved with formatting
- Formulas shown as computed values
- Named ranges and cell references

### HWPX (Hancom Office)
- Korean document format (XML-based, ZIP archive)
- Structure: Contents/section*.xml
- Tables with complex merging patterns
- Korean text preserved with UTF-8 encoding

### JSON
- Formatted as structured markdown
- Nested objects → indented sections
- Arrays → lists or tables

### TXT
- Wrapped as markdown
- Auto-detect structure (lists, paragraphs)

## Image Formats (PNG, JPG, JPEG)
- OCR via Google Gemini Vision API
- Text extraction with layout preservation
- Table detection in scanned documents
- Handwriting recognition (best effort)

## Unsupported Formats
- HWP (legacy Hancom binary format — convert to HWPX first)
- Password-protected files
- DRM-protected documents
