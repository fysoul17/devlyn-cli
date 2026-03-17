# HWPX XML Knowledge

OWPML structure for surgical HWPX document editing.

## HWPX Structure

HWPX (Hancom Office Open XML) is a ZIP archive:
```
mimetype                     — "application/hwp+zip" (MUST be first entry, uncompressed)
META-INF/
  manifest.xml               — file manifest
Contents/
  content.hpf                — content manifest (OPF package)
  header.xml                 — document header (styles, fonts, charPr definitions)
  section0.xml               — first section (PRIMARY TARGET)
  section1.xml               — additional sections
BinData/                     — embedded images and binary data
Preview/
  PrvImage.png               — thumbnail preview
settings.xml                 — document settings
```

## Key XML Elements

### Namespaces
```xml
xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"
xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"
xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core"
xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head"
```

### Section Structure
```xml
<hs:sec>
  <hp:p>              <!-- paragraph -->
    <hp:run>          <!-- text run -->
      <hp:rPr>        <!-- run properties (charPrIDRef) -->
      <hp:t>          <!-- text content -->
    </hp:run>
  </hp:p>
</hs:sec>
```

### Tables
```xml
<hp:tbl rowCnt="N" colCnt="M">
  <hp:tr>             <!-- table row -->
    <hp:tc>           <!-- table cell -->
      <hp:cellAddr colAddr="0" rowAddr="0"/>
      <hp:cellSpan colSpan="1" rowSpan="1"/>
      <hp:cellSz width="W" height="H"/>
      <hp:subList>    <!-- ~65% of cells wrap content here -->
        <hp:p>        <!-- cell content -->
      </hp:subList>
    </hp:tc>
  </hp:tr>
</hp:tbl>
```

## Critical Notes

1. `mimetype` file MUST be the first ZIP entry and stored uncompressed
2. Korean text is UTF-8 encoded
3. Table cells often use complex merging (`hp:cellSpan`) for form layouts
4. Section files are independent — each is a complete XML document
5. Character properties reference IDs defined in `header.xml` (`charPrIDRef`)
6. After any `tree.write()`, must restore ALL 14 original namespace declarations on root elements

## References

See `references/hwpx-structure.md` for unpacking, namespace preservation fix, repackaging, and critical rules.
See `references/hwpx-field-patterns.md` for field detection patterns (10 patterns including subList wrapping, cellAddr addressing, charPrIDRef resolution).
