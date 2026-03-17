#!/usr/bin/env python3
"""Validate a modified HWPX working directory for XML well-formedness.

Usage:
    python validate_hwpx.py <work_dir>

Checks:
- All XML files are well-formed
- mimetype file exists
- Section files exist in Contents/
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".gif", ".webp"}

HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HC = "http://www.hancom.co.kr/hwpml/2011/core"
HH = "http://www.hancom.co.kr/hwpml/2011/head"
OPF = "http://www.idpf.org/2007/opf"

# Required child element local names inside <hp:pic>
REQUIRED_PIC_CHILDREN = {
    "offset", "orgSz", "curSz", "flip", "rotationInfo", "renderingInfo",
    "inMargin", "sz", "pos", "outMargin", "lineShape", "imgRect", "imgClip",
    "imgDim",
}

# Elements that should NOT appear inside <hp:pic>
SPURIOUS_PIC_ELEMENTS = {"picSz", "picOutline", "picRect", "caption", "shapeComment"}


def validate_xml_file(path: Path) -> list[str]:
    """Check if an XML file is well-formed."""
    errors = []
    try:
        ET.parse(path)
    except ET.ParseError as e:
        errors.append(f"{path}: XML parse error: {e}")
    return errors


def _check_single_pic(pic: ET.Element, prefix: str, manifest_ids: set[str]) -> tuple[list[str], list[str]]:
    """Validate a single <hp:pic> element against the 8 structural rules.

    Returns (errors, warnings) lists.
    """
    errors = []
    warnings = []

    # Rule 1: <img> must use hc: namespace
    hc_imgs = list(pic.iter(f"{{{HC}}}img"))
    hp_imgs = list(pic.iter(f"{{{HP}}}img"))
    if hp_imgs:
        errors.append(f"{prefix}: <img> uses hp: namespace (must be hc:)")
    if not hc_imgs and not hp_imgs:
        errors.append(f"{prefix}: missing <img> element entirely")

    # Rule 2: <imgRect> must have <hc:pt0..3> children
    for imgRect in pic.iter(f"{{{HP}}}imgRect"):
        pt_count = sum(1 for i in range(4) for _ in imgRect.iter(f"{{{HC}}}pt{i}"))
        if pt_count < 4:
            if imgRect.get("x1") is not None or imgRect.get("x2") is not None:
                errors.append(
                    f"{prefix}: <imgRect> uses inline attributes "
                    f"(must have <hc:pt0..3> children)"
                )
            else:
                errors.append(
                    f"{prefix}: <imgRect> has {pt_count}/4 "
                    f"required <hc:pt> children"
                )

    # Rule 3: Required child elements
    child_local_names = set()
    for child in pic:
        tag = child.tag
        local = tag.split("}")[1] if "}" in tag else tag
        child_local_names.add(local)

    missing = REQUIRED_PIC_CHILDREN - child_local_names
    if missing:
        errors.append(f"{prefix}: missing required children: {', '.join(sorted(missing))}")

    # Rule 4: No spurious elements
    spurious_found = SPURIOUS_PIC_ELEMENTS & child_local_names
    if spurious_found:
        warnings.append(f"{prefix}: spurious elements found: {', '.join(sorted(spurious_found))}")

    # Rule 5: imgClip right/bottom should not be all zeros
    for imgClip in pic.iter(f"{{{HP}}}imgClip"):
        if imgClip.get("right", "0") == "0" and imgClip.get("bottom", "0") == "0":
            warnings.append(f"{prefix}: <imgClip> right/bottom are both 0 (should be pixel dimensions)")

    # Rule 6: lineShape attributes
    for ls in pic.iter(f"{{{HP}}}lineShape"):
        if ls.get("color", "") == "#000000":
            warnings.append(f"{prefix}: <lineShape> color=\"#000000\" (should be \"none\")")
        if ls.get("width", "") == "0":
            warnings.append(f"{prefix}: <lineShape> width=\"0\" (should be \"283\")")

    # Rule 7: Check manifest registration
    for img in hc_imgs:
        ref_id = img.get("binaryItemIDRef", "")
        if ref_id and manifest_ids and ref_id not in manifest_ids:
            errors.append(f"{prefix}: binaryItemIDRef=\"{ref_id}\" not found in content.hpf manifest")

    # Rule 8: hp:pos attributes
    for pos in pic.iter(f"{{{HP}}}pos"):
        if pos.get("flowWithText", "") == "1":
            warnings.append(f"{prefix}: <pos> flowWithText=\"1\" (should be \"0\")")
        if pos.get("horzRelTo", "") == "PARA":
            warnings.append(f"{prefix}: <pos> horzRelTo=\"PARA\" (should be \"COLUMN\")")

    return errors, warnings


def validate_pic_elements(work_dir: Path) -> list[str]:
    """Validate <hp:pic> elements in section XML for correct structure."""
    errors = []
    warnings = []

    contents_dir = work_dir / "Contents"
    if not contents_dir.is_dir():
        return errors

    # Collect manifest IDs from content.hpf
    manifest_ids = set()
    content_hpf = contents_dir / "content.hpf"
    if content_hpf.exists():
        try:
            tree = ET.parse(content_hpf)
            for item in tree.getroot().iter(f"{{{OPF}}}item"):
                if "BinData/" in item.get("href", ""):
                    manifest_ids.add(item.get("id", ""))
        except ET.ParseError as e:
            errors.append(f"content.hpf: XML parse error (skipping manifest check): {e}")

    for section_file in sorted(contents_dir.glob("section*.xml")):
        try:
            tree = ET.parse(section_file)
            root = tree.getroot()
        except ET.ParseError as e:
            errors.append(f"{section_file.name}: XML parse error (skipping pic validation): {e}")
            continue

        for pic in root.iter(f"{{{HP}}}pic"):
            prefix = f"{section_file.name} pic id={pic.get('id', '?')}"
            pic_errors, pic_warnings = _check_single_pic(pic, prefix, manifest_ids)
            errors.extend(pic_errors)
            warnings.extend(pic_warnings)

    # Check header.xml for spurious binDataItems referencing images
    for header_path in work_dir.rglob("header.xml"):
        try:
            tree = ET.parse(header_path)
            for _ in tree.getroot().iter(f"{{{HH}}}binDataItem"):
                warnings.append(
                    f"{header_path.name}: found <hh:binDataItem> "
                    f"(images should be registered in content.hpf only)"
                )
        except ET.ParseError as e:
            errors.append(f"{header_path.name}: XML parse error (skipping binDataItem check): {e}")

    # Warnings are non-fatal but reported
    for w in warnings:
        errors.append(f"WARNING: {w}")

    return errors


def validate_image_references(work_dir: Path) -> list[str]:
    """Verify that BinData image files are referenced in section XML files."""
    errors = []

    # 1. Collect actual image files in BinData/
    bindata_dir = work_dir / "BinData"
    bindata_images = set()
    if bindata_dir.is_dir():
        for f in bindata_dir.iterdir():
            if f.suffix.lower() in IMAGE_EXTENSIONS:
                bindata_images.add(f"BinData/{f.name}")

    if not bindata_images:
        return errors  # No images, nothing to validate

    # 2. Scan section XML files for BinData references
    contents_dir = work_dir / "Contents"
    referenced_images = set()
    if contents_dir.is_dir():
        for section_file in contents_dir.glob("section*.xml"):
            try:
                tree = ET.parse(section_file)
                root = tree.getroot()
                # Search for binDataEmbedding elements referencing BinData/
                for elem in root.iter():
                    for attr_val in elem.attrib.values():
                        if isinstance(attr_val, str) and attr_val.startswith("BinData/"):
                            referenced_images.add(attr_val)
            except ET.ParseError:
                pass  # Already caught by validate_xml_file

    # Also check header XML files
    for xml_file in work_dir.rglob("*.xml"):
        if xml_file.name.startswith("section"):
            continue  # Already checked above
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            for elem in root.iter():
                for attr_val in elem.attrib.values():
                    if isinstance(attr_val, str) and attr_val.startswith("BinData/"):
                        referenced_images.add(attr_val)
        except ET.ParseError:
            pass

    # 3. Check BinData files have corresponding references
    for img in bindata_images:
        if img not in referenced_images:
            errors.append(f"Image file {img} has no reference in section or header XML")

    # 4. Check references point to existing files
    for ref in referenced_images:
        ref_path = work_dir / ref
        if not ref_path.exists():
            errors.append(f"XML references {ref} but file does not exist")

    return errors


def main():
    if len(sys.argv) != 2:
        print("Usage: python validate_hwpx.py <work_dir>", file=sys.stderr)
        sys.exit(1)

    work_dir = Path(sys.argv[1])
    if not work_dir.is_dir():
        print(f"Error: Not a directory: {work_dir}", file=sys.stderr)
        sys.exit(2)

    errors = []

    # Check mimetype
    mimetype_path = work_dir / "mimetype"
    if not mimetype_path.exists():
        errors.append("Missing required file: mimetype")

    # Check for section files
    contents_dir = work_dir / "Contents"
    if not contents_dir.is_dir():
        errors.append("Missing Contents/ directory")
    else:
        section_files = list(contents_dir.glob("section*.xml"))
        if not section_files:
            errors.append("No section*.xml files found in Contents/")

    # Validate all XML files
    for xml_file in work_dir.rglob("*.xml"):
        errors.extend(validate_xml_file(xml_file))

    # Validate image references
    errors.extend(validate_image_references(work_dir))

    # Validate <hp:pic> element structure
    errors.extend(validate_pic_elements(work_dir))

    if errors:
        print(f"Validation FAILED — {len(errors)} error(s):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)
    else:
        print("HWPX validation passed.", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
