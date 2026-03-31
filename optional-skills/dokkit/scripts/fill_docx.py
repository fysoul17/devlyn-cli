"""
fill_docx.py — python-docx based document filler for Dokkit v4

Usage: python fill_docx.py <template.docx> <analysis.json> <fill_content.json> <output.docx>

Handles:
- Tip box removal (작성요령 tables)
- Instruction text removal (blue ※ paragraphs + blue text inside table cells)
- Overview table filling (수요기업 개요)
- Section content insertion with proper formatting
- Page breaks between major chapters
- All text forced to black
"""

import sys
import os
import json
import re
import copy
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


# ── Helpers ──────────────────────────────────────────────────────────────

def remove_element(el):
    p = el.getparent()
    if p is not None:
        p.remove(el)


def get_text(el):
    return ''.join(t.text or '' for t in el.iter(qn('w:t')))


def set_cell_text(cell_el, text):
    """Replace ALL text in a table cell with new text, preserving first run's formatting."""
    first_rPr = None
    for r in cell_el.iter(qn('w:r')):
        rPr = r.find(qn('w:rPr'))
        if rPr is not None and first_rPr is None:
            first_rPr = copy.deepcopy(rPr)
        break

    # Clear all existing paragraphs' runs
    for p in cell_el.findall(qn('w:p')):
        for r in list(p.findall(qn('w:r'))):
            p.remove(r)

    # Insert new run in first paragraph
    first_p = cell_el.find(qn('w:p'))
    if first_p is None:
        first_p = OxmlElement('w:p')
        cell_el.append(first_p)

    r = OxmlElement('w:r')
    if first_rPr is not None:
        rPr = copy.deepcopy(first_rPr)
        # Force black color
        for c in rPr.findall(qn('w:color')):
            c.set(qn('w:val'), '000000')
        # Remove italic
        for i in rPr.findall(qn('w:i')):
            rPr.remove(i)
        r.append(rPr)

    t = OxmlElement('w:t')
    t.set(qn('xml:space'), 'preserve')
    t.text = text
    r.append(t)
    first_p.append(r)


# ── Detection ────────────────────────────────────────────────────────────

def is_tip_box(tbl):
    text = get_text(tbl)
    return '작성요령' in text or '작성 요령' in text


def has_blue_color(el):
    for c in el.iter(qn('w:color')):
        val = c.get(qn('w:val'), '').upper()
        if val in ('0000FF', '0000FFFF'):
            return True
    return False


def is_instruction_para(p):
    text = get_text(p).strip()
    if not text:
        return False
    if text.startswith('※'):
        return True
    if has_blue_color(p):
        return True
    return False


def is_chapter_header(tbl):
    text = get_text(tbl).strip()
    return bool(re.match(r'^[ⅠⅡⅢⅣⅤ]', text))


def get_chapter_num(tbl):
    text = get_text(tbl).strip()
    for ch, n in {'Ⅰ': 1, 'Ⅱ': 2, 'Ⅲ': 3, 'Ⅳ': 4, 'Ⅴ': 5}.items():
        if text.startswith(ch):
            return n
    return 0


# ── Formatting ───────────────────────────────────────────────────────────

def extract_body_ppr(body):
    """Find the first content paragraph with left indentation → copy its pPr."""
    for child in body:
        if child.tag != qn('w:p'):
            continue
        pPr = child.find(qn('w:pPr'))
        if pPr is None:
            continue
        ind = pPr.find(qn('w:ind'))
        if ind is not None and int(ind.get(qn('w:left'), '0')) > 0:
            return copy.deepcopy(pPr)
    return None


def make_clean_rpr(font_name='맑은 고딕', font_size='20'):
    """Create a clean black rPr with specified font. No gray, no blue."""
    rPr = OxmlElement('w:rPr')
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:ascii'), font_name)
    rFonts.set(qn('w:eastAsia'), font_name)
    rFonts.set(qn('w:hAnsi'), font_name)
    rPr.append(rFonts)
    color = OxmlElement('w:color')
    color.set(qn('w:val'), '000000')
    rPr.append(color)
    sz = OxmlElement('w:sz')
    sz.set(qn('w:val'), font_size)
    rPr.append(sz)
    szCs = OxmlElement('w:szCs')
    szCs.set(qn('w:val'), font_size)
    rPr.append(szCs)
    return rPr


def create_para(text, pPr_tpl, rPr_tpl, bold=False):
    """Create a <w:p> with given text, copying pPr and rPr templates."""
    p = OxmlElement('w:p')

    if pPr_tpl is not None:
        pPr = copy.deepcopy(pPr_tpl)
        for inner in pPr.findall(qn('w:rPr')):
            pPr.remove(inner)
        p.append(pPr)

    r = OxmlElement('w:r')
    rPr = copy.deepcopy(rPr_tpl)
    # Force black
    for c in rPr.findall(qn('w:color')):
        c.set(qn('w:val'), '000000')
    for i in rPr.findall(qn('w:i')):
        rPr.remove(i)
    if bold:
        if rPr.find(qn('w:b')) is None:
            rPr.insert(0, OxmlElement('w:b'))
    else:
        b = rPr.find(qn('w:b'))
        if b is not None:
            rPr.remove(b)
    r.append(rPr)

    t = OxmlElement('w:t')
    t.set(qn('xml:space'), 'preserve')
    t.text = text
    r.append(t)
    p.append(r)
    return p


def content_to_paras(text, pPr_tpl, rPr_tpl):
    """Convert content string to list of <w:p> elements."""
    paras = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            paras.append(create_para('', pPr_tpl, rPr_tpl))
            continue
        bold = False
        if line.startswith('[') and line.endswith(']'):
            line = line[1:-1]
            bold = True
        elif line.startswith('**') and line.endswith('**'):
            line = line[2:-2]
            bold = True
        if line.startswith('- ') or line.startswith('• '):
            line = '• ' + line[2:]
        paras.append(create_para(line, pPr_tpl, rPr_tpl, bold=bold))
    return paras


# ── Field ID lookup ──────────────────────────────────────────────────────

def _get_fid(field):
    """Get field ID from either 'id' or 'field_id' key."""
    return field.get('id') or field.get('field_id', '')


def _find_field_id(analysis, field_type, label_keyword):
    """Search analysis.json for a field matching type and label keyword.

    Returns the field ID, or None if not found.
    Supports both flat fields[] array and nested sections[].fields[] formats.
    """
    # Flat format: analysis.fields[]
    for field in analysis.get('fields', []):
        ft = field.get('type') or field.get('field_type', '')
        if ft != field_type:
            continue
        label = field.get('label', '')
        if label_keyword in label:
            return _get_fid(field)
    # Nested format: analysis.sections[].fields[]
    for section in analysis.get('sections', []):
        for field in section.get('fields', []):
            ft = field.get('type') or field.get('field_type', '')
            if ft != field_type:
                continue
            label = field.get('label', '')
            if label_keyword in label:
                return _get_fid(field)
    return None


# ── Staff/schedule table filling from fill_content.json ─────────────────

def _fill_staff_table(tbl, staff_data, fill_content):
    """Fill staff (참여인력) table from fill_content.json data.

    staff_data is a dict with 'rows' key containing a list of row arrays.
    """
    if not staff_data or not isinstance(staff_data, dict):
        return 0
    rows_data = staff_data.get('rows', [])
    rows = tbl.findall(qn('w:tr'))
    filled = 0
    for ri, row_data in enumerate(rows_data):
        target_ri = ri + 1  # skip header
        if target_ri >= len(rows):
            break
        cells = rows[target_ri].findall(qn('w:tc'))
        if isinstance(row_data, list):
            for ci, val in enumerate(row_data):
                if ci < len(cells):
                    set_cell_text(cells[ci], str(val))
        filled += 1
    # Clear remaining rows
    for ri in range(len(rows_data) + 1, len(rows)):
        cells = rows[ri].findall(qn('w:tc'))
        for cell in cells:
            set_cell_text(cell, '')
    return filled


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 5:
        print("Usage: python fill_docx.py <template> <analysis.json> <fill_content.json> <output>")
        sys.exit(1)

    template_path, analysis_path, content_path, output_path = sys.argv[1:5]

    print(f"Loading: {template_path}")
    doc = Document(template_path)
    body = doc.element.body

    with open(analysis_path, 'r', encoding='utf-8') as f:
        analysis = json.load(f)
    with open(content_path, 'r', encoding='utf-8') as f:
        fill_content = json.load(f)

    # ── Extract formatting templates ──
    body_pPr = extract_body_ppr(body)
    body_rPr = make_clean_rpr()  # Always use clean black rPr — no gray leaks

    if body_pPr:
        ind = body_pPr.find(qn('w:ind'))
        print(f"  pPr indent: {ind.get(qn('w:left'), '?') if ind is not None else 'none'}")
    print(f"  rPr: 맑은 고딕 sz=20 color=000000 (clean)")

    # ── Step 1: Remove tip boxes ──
    tip_count = 0
    for tbl in list(body.findall(qn('w:tbl'))):
        if is_tip_box(tbl):
            remove_element(tbl)
            tip_count += 1
    print(f"Step 1: Removed {tip_count} tip boxes")

    # ── Step 2: Remove instruction text (standalone blue/※ paragraphs) ──
    instr_count = 0
    for p in list(body.findall(qn('w:p'))):
        if is_instruction_para(p):
            remove_element(p)
            instr_count += 1
    print(f"Step 2: Removed {instr_count} instruction paragraphs")

    # ── Step 3: Clean ALL nested tables and instruction text inside table cells ──
    cell_clean_count = 0
    nested_tbl_count = 0
    overview_tbl = None

    # Find all top-level tables and clean their cells
    for tbl in body.findall(qn('w:tbl')):
        text = get_text(tbl)
        if '구분' in text and '상세 내용' in text:
            overview_tbl = tbl

        # Collect ALL nested tables across all cells first, then remove
        nested_to_remove = []
        rows = tbl.findall(qn('w:tr'))
        for row in rows:
            for tc in row.findall(qn('w:tc')):
                for nested in tc.findall(qn('w:tbl')):
                    nested_to_remove.append((tc, nested))
                # Also clean ※ text in cell paragraphs
                for p in list(tc.findall(qn('w:p'))):
                    pt = get_text(p).strip()
                    if pt.startswith('※') or pt.startswith('·※') or pt.startswith('* '):
                        for r in list(p.findall(qn('w:r'))):
                            p.remove(r)
                        cell_clean_count += 1

        # Remove nested tables (safe — separate loop)
        for tc, nested in nested_to_remove:
            tc.remove(nested)
            nested_tbl_count += 1

    print(f"Step 3: Cleaned {cell_clean_count} instruction texts + {nested_tbl_count} nested tables")

    # ── Step 4: Fill overview table — keyword matching ──
    if overview_tbl is not None:
        rows = overview_tbl.findall(qn('w:tr'))
        overview_filled = 0

        # Map cell label keywords → fill_content key
        keyword_map = {
            '사업(과제)명': 'overview_사업명',
            '사업(과제)개요': 'overview_사업개요',
            '핵심역량': 'overview_핵심역량',
            '시장현황': 'overview_시장현황',
            '데이터': 'overview_데이터필요성',
        }
        caption_map = {
            '사진(이미지) 또는 설계도 제목': None,  # handled separately
        }

        for ri, row in enumerate(rows):
            cells = row.findall(qn('w:tc'))
            if len(cells) < 3:
                continue
            # Check cell[1] (label column) for keyword matches
            label_text = get_text(cells[1]).strip().replace(' ', '')
            for keyword, content_key in keyword_map.items():
                kw_clean = keyword.replace(' ', '')
                if kw_clean in label_text:
                    content = fill_content.get(content_key, '')
                    if content and isinstance(content, str):
                        set_cell_text(cells[2], content)
                        overview_filled += 1
                    break

        # Fill image captions (row 7, cells 2 and 3)
        if len(rows) > 7:
            cells7 = rows[7].findall(qn('w:tc'))
            cap_l = fill_content.get('overview_이미지_caption_left', '')
            cap_r = fill_content.get('overview_이미지_caption_right', '')
            if cap_l and len(cells7) > 2:
                set_cell_text(cells7[2], cap_l)
                overview_filled += 1
            if cap_r and len(cells7) > 3:
                set_cell_text(cells7[3], cap_r)
                overview_filled += 1

        print(f"Step 4: Filled {overview_filled} overview table cells")
    else:
        print("Step 4: Overview table not found")

    # ── Step 5: Force ALL colors to black ──
    color_count = 0
    for color in body.iter(qn('w:color')):
        val = color.get(qn('w:val'), '').upper()
        if val not in ('000000', 'AUTO', ''):
            color.set(qn('w:val'), '000000')
            color_count += 1
    print(f"Step 5: Forced {color_count} non-black colors to black")

    # ── Step 6: Page breaks before Ⅱ, Ⅲ, Ⅳ, Ⅴ ──
    pb_count = 0
    for tbl in body.findall(qn('w:tbl')):
        if is_chapter_header(tbl) and get_chapter_num(tbl) >= 1:  # Include Ⅰ (page break after 목차)
            add_page_break_before = OxmlElement('w:p')
            pPr = OxmlElement('w:pPr')
            r = OxmlElement('w:r')
            br = OxmlElement('w:br')
            br.set(qn('w:type'), 'page')
            r.append(br)
            add_page_break_before.append(pPr)
            add_page_break_before.append(r)
            tbl.addprevious(add_page_break_before)
            pb_count += 1
    print(f"Step 6: Added {pb_count} page breaks")

    # ── Step 7: Fill section content ──
    # Build multiple matching keys for each section_content field.
    # Analysis headings may use prefixed names like "Ⅱ.1.가 사업(과제) 목적"
    # but the document paragraphs just have "가. 사업(과제) 목적".
    # Strategy: extract the Korean sub-heading part and match flexibly.
    heading_entries = []  # list of (match_keys, field_id)
    # Support flat fields[] format
    all_fields = analysis.get('fields', [])
    # Also gather from nested sections[].fields[] if present
    for section in analysis.get('sections', []):
        all_fields.extend(section.get('fields', []))
        # Also treat the section itself as a field if it has field_type
        if section.get('field_type') in ('section_content', 'fill_conditional', 'fill_optional'):
            # Use section_id as the field id
            if 'id' not in section and 'field_id' not in section:
                section['id'] = section.get('section_id', '')
            all_fields.append(section)
    for field in all_fields:
        ft = field.get('type') or field.get('field_type', '')
        if ft != 'section_content':
            continue
        fid = _get_fid(field)
        cp = field.get('content_plan', {})
        heading = cp.get('section_heading', field.get('label', ''))
        label = field.get('label', '')

        # Generate multiple match keys from the heading
        keys = set()
        keys.add(heading)
        keys.add(label)
        # Strip common prefixes: "Ⅱ.1.가 " → "가 사업..." or "Ⅳ.가 " → "가 ..."
        stripped = re.sub(r'^[ⅠⅡⅢⅣⅤ]\.\d*\.?', '', heading).strip()
        if stripped:
            keys.add(stripped)
        # Extract "가. XXX" or "가 XXX" pattern from the heading
        m = re.search(r'([가-힣])[.\s]\s*(.+)', heading)
        if m:
            desc = m.group(2).strip()
            keys.add(f'{m.group(1)}. {desc}')    # "가. 사업(...)"
            keys.add(f'{m.group(1)} {desc}')     # "가 사업(...)"
            keys.add(desc)                        # just "사업(...)"
            # Also add versions with parenthetical suffix stripped
            desc_short = re.sub(r'\s*\(.*$', '', desc).strip()
            if desc_short and desc_short != desc:
                keys.add(f'{m.group(1)}. {desc_short}')
                keys.add(desc_short)
        # Also extract content after all prefixes (numbers, roman, Korean letters)
        content_only = re.sub(r'^[ⅠⅡⅢⅣⅤ\.\d\s]*[가-힣][\.\s]\s*', '', heading).strip()
        if content_only and len(content_only) >= 3:
            keys.add(content_only)
            # Strip parenthetical suffix here too
            co_short = re.sub(r'\s*\(.*$', '', content_only).strip()
            if co_short and len(co_short) >= 3:
                keys.add(co_short)
        # Clean up empty keys
        keys = {k.strip() for k in keys if k.strip() and len(k.strip()) >= 3}
        heading_entries.append((keys, fid))

    children = list(body)
    filled = 0
    filled_fids = set()

    # Also match chapter tables (Ⅴ 기타, etc.) — collect them for fallback
    chapter_positions = {}  # chapter_num → body index of first paragraph after chapter table
    for i, child in enumerate(children):
        if child.tag == qn('w:tbl') and is_chapter_header(child):
            ch_num = get_chapter_num(child)
            # The first paragraph after the chapter table is where content goes
            for j in range(i + 1, min(i + 5, len(children))):
                if children[j].tag == qn('w:p'):
                    chapter_positions[ch_num] = j
                    break

    for i, child in enumerate(children):
        if child.tag != qn('w:p'):
            continue
        text = get_text(child).strip()
        if not text:
            continue

        # Skip numbered parent headings (e.g. "1. 사업(과제) 개요", "4. 기대효과")
        # These are parent-level, not sub-section headings where content goes
        if re.match(r'^\d+\.\s', text):
            continue

        # Match heading to field using multiple strategies
        matched_fid = None
        best_key_len = 0
        for keys, fid in heading_entries:
            if fid in filled_fids:
                continue
            for key in keys:
                kl = len(key)
                # Exact substring match (most reliable)
                if key in text and kl > best_key_len:
                    matched_fid = fid
                    best_key_len = kl
                # Normalized match (ignore spaces)
                elif key.replace(' ', '') in text.replace(' ', '') and kl > best_key_len:
                    matched_fid = fid
                    best_key_len = kl
        if not matched_fid:
            continue

        content = fill_content.get(matched_fid, '')
        if not content or not isinstance(content, str):
            continue

        # Find empty/content paragraphs after heading (these get replaced)
        empties = []
        for j in range(i + 1, min(i + 80, len(children))):
            nxt = children[j]
            if nxt.tag == qn('w:tbl'):
                break
            if nxt.tag == qn('w:p'):
                nt = get_text(nxt).strip()
                # Stop at next heading (가., 나., 다., 라., 마., 1., 2., etc.)
                if nt and (re.match(r'^[가-힣]\.\s', nt) or re.match(r'^\d+\.\s', nt)):
                    break
                empties.append(nxt)
            else:
                break

        for old in empties:
            remove_element(old)

        # Insert content
        new_paras = content_to_paras(content, body_pPr, body_rPr)
        ref = child
        for np in new_paras:
            ref.addnext(np)
            ref = np

        filled += 1
        filled_fids.add(matched_fid)
        print(f"  Filled {matched_fid}: {len(content)}c after '{text[:40]}'")

    print(f"Step 7: Filled {filled} sections")

    # ── Step 7b: Fallback for unfilled sections (combined sub-fields, chapter sections) ──
    # Re-scan body for headings that have unfilled fields
    children = list(body)  # refresh after modifications
    fallback_count = 0

    # Combine sub-fields for "나. 데이터 상품 및 활용 서비스 필요성"
    combined_data_fids = ['field_030', 'field_031', 'field_032', 'field_033', 'field_034']
    if not any(f in filled_fids for f in combined_data_fids):
        combined_content = '\n\n'.join(
            fill_content.get(fid, '') for fid in combined_data_fids
            if fill_content.get(fid, '') and isinstance(fill_content.get(fid, ''), str)
        )
        if combined_content:
            for i, child in enumerate(children):
                if child.tag != qn('w:p'):
                    continue
                text = get_text(child).strip()
                if '데이터 상품' in text and '필요성' in text:
                    empties = []
                    for j in range(i + 1, min(i + 80, len(children))):
                        nxt = children[j]
                        if nxt.tag == qn('w:tbl'):
                            break
                        if nxt.tag == qn('w:p'):
                            nt = get_text(nxt).strip()
                            if nt and (re.match(r'^[가-힣]\.\s', nt) or re.match(r'^\d+\.\s', nt)):
                                break
                            empties.append(nxt)
                        else:
                            break
                    for old in empties:
                        remove_element(old)
                    new_paras = content_to_paras(combined_content, body_pPr, body_rPr)
                    ref = child
                    for np in new_paras:
                        ref.addnext(np)
                        ref = np
                    fallback_count += 1
                    filled_fids.update(combined_data_fids)
                    print(f"  Filled combined data fields: {len(combined_content)}c after '{text[:40]}'")
                    break

    # Fill Ⅴ. 기타 section — content goes after chapter header table
    # Find field ID for 기타 section (could be field_067, section_Ⅴ_기타, etc.)
    kita_fid = None
    for fid_candidate in fill_content:
        if '기타' in fid_candidate or 'Ⅴ' in fid_candidate:
            if fid_candidate not in filled_fids and isinstance(fill_content[fid_candidate], str):
                kita_fid = fid_candidate
                break
    if kita_fid:
        children = list(body)  # refresh
        for i, child in enumerate(children):
            if child.tag == qn('w:tbl') and is_chapter_header(child) and get_chapter_num(child) == 5:
                # Find empty paragraphs after the Ⅴ table
                empties = []
                for j in range(i + 1, min(i + 20, len(children))):
                    nxt = children[j]
                    if nxt.tag == qn('w:tbl'):
                        break
                    if nxt.tag == qn('w:p'):
                        nt = get_text(nxt).strip()
                        if nt and len(nt) > 20:
                            break
                        empties.append(nxt)
                    else:
                        break
                for old in empties:
                    remove_element(old)
                content = fill_content[kita_fid]
                new_paras = content_to_paras(content, body_pPr, body_rPr)
                ref = child
                for np in new_paras:
                    ref.addnext(np)
                    ref = np
                fallback_count += 1
                filled_fids.add(kita_fid)
                print(f"  Filled {kita_fid}: {len(content)}c after Ⅴ chapter header")
                break

    if fallback_count:
        print(f"Step 7b: Filled {fallback_count} fallback sections")

    # ── Step 8: Fill budget table (사업비 편성비중) — from fill_content.json ──
    for tbl in body.findall(qn('w:tbl')):
        text = get_text(tbl)
        if '기획' in text and '설계' in text and '구매' in text and '분석' in text:
            rows = tbl.findall(qn('w:tr'))
            if len(rows) >= 3:
                # Try individual field keys from fill_content
                cb_keys = ['budget_기획설계_check', 'budget_구매_check', 'budget_수집생성_check', 'budget_가공_check', 'budget_분석_check']
                amt_keys = ['budget_기획설계_amount', 'budget_구매_amount', 'budget_수집생성_amount', 'budget_가공_amount', 'budget_분석_amount', 'budget_계_amount']

                # Row 1: checkboxes (skip first label column)
                r1_cells = rows[1].findall(qn('w:tc'))
                for ci, key in enumerate(cb_keys):
                    target_ci = ci + 1  # skip label cell
                    val = fill_content.get(key, '')
                    if val and target_ci < len(r1_cells):
                        set_cell_text(r1_cells[target_ci], val)

                # Row 2: amounts (skip first label cell)
                r2_cells = rows[2].findall(qn('w:tc'))
                for ci, key in enumerate(amt_keys):
                    target_ci = ci + 1  # skip label cell
                    val = fill_content.get(key, '')
                    if val and target_ci < len(r2_cells):
                        set_cell_text(r2_cells[target_ci], val)

                print(f"Step 8a: Filled budget table ({len(cb_keys)} checks + {len(amt_keys)} amounts)")
            break

    # ── Step 8b: Fill schedule table (추진일정) — from fill_content.json ──
    # Try named key first, then analysis field ID
    sched_data = fill_content.get('schedule_table')
    if sched_data is None:
        sched_field_id = _find_field_id(analysis, 'table_content', '추진일정') or _find_field_id(analysis, 'table_content', '일정')
        sched_data = fill_content.get(sched_field_id) if sched_field_id else None
    # Normalize: if it's a list, wrap in dict
    if isinstance(sched_data, list):
        sched_data = {'rows': sched_data}
    for tbl in body.findall(qn('w:tbl')):
        text = get_text(tbl)
        if '세부 업무' in text and '수행내용' in text:
            rows = tbl.findall(qn('w:tr'))
            if sched_data and isinstance(sched_data, dict):
                sched_rows = sched_data.get('rows', [])
                # Determine where data rows start (skip header rows)
                data_start = 1
                for ri, row in enumerate(rows):
                    rt = get_text(row)
                    if 'M' in rt or 'M+1' in rt:
                        data_start = ri + 1
                        break
                for si, row_data in enumerate(sched_rows):
                    ri = data_start + si
                    if ri >= len(rows):
                        break
                    cells = rows[ri].findall(qn('w:tc'))
                    task = row_data.get('세부업무', '')
                    desc = row_data.get('수행내용', '')
                    # Support both 'marks' (string array) and 'schedule' (bool array) formats
                    marks = row_data.get('marks', [])
                    if not marks:
                        schedule = row_data.get('schedule', [])
                        marks = ['●' if m else '' for m in schedule]
                    weight = row_data.get('비중', '')
                    if len(cells) >= 2:
                        set_cell_text(cells[0], task)
                        set_cell_text(cells[1], desc)
                    # Month mark columns start at index 2
                    for mi, mark in enumerate(marks):
                        ci = 2 + mi
                        if ci < len(cells) - 1:  # -1 to not overwrite weight col
                            set_cell_text(cells[ci], mark)
                    # Weight (last cell)
                    if len(cells) > 0 and weight:
                        set_cell_text(cells[-1], weight)
                # Clear remaining data rows
                for ri in range(data_start + len(sched_rows), len(rows)):
                    cells = rows[ri].findall(qn('w:tc'))
                    for cell in cells:
                        set_cell_text(cell, '')
                print(f"Step 8b: Filled schedule table ({len(sched_rows)} rows)")
            else:
                print("Step 8b: Schedule field not found in fill_content — skipped")
            break

    # ── Step 8c: Fill employee count table — find field IDs dynamically ──
    # Search analysis.json for empty_cell fields related to 재직인원/고용계획
    # Try named keys first, then analysis field IDs
    emp_fid = 'headcount_재직인원'
    hire_fid = 'headcount_추가고용'
    if emp_fid not in fill_content:
        emp_fid = _find_field_id(analysis, 'empty_cell', '재직') or ''
    if hire_fid not in fill_content:
        hire_fid = _find_field_id(analysis, 'empty_cell', '고용') or ''
    for tbl in body.findall(qn('w:tbl')):
        text = get_text(tbl)
        if '재직(소속)인원' in text and '추가 고용계획' in text:
            rows = tbl.findall(qn('w:tr'))
            if rows:
                cells = rows[0].findall(qn('w:tc'))
                if len(cells) >= 4:
                    v1_raw = fill_content.get(emp_fid, '') if emp_fid else ''
                    v2_raw = fill_content.get(hire_fid, '') if hire_fid else ''
                    # Handle dict or string values
                    if isinstance(v1_raw, dict):
                        v1 = v1_raw.get('재직인원', v1_raw.get('value', ''))
                    else:
                        v1 = str(v1_raw) if v1_raw else ''
                    if isinstance(v2_raw, dict):
                        v2 = v2_raw.get('추가고용계획', v2_raw.get('value', ''))
                    else:
                        v2 = str(v2_raw) if v2_raw else ''
                    # Add '명' suffix if not already present
                    if v1 and not v1.endswith('명'):
                        v1 = f'{v1} 명'
                    if v2 and not v2.endswith('명'):
                        v2 = f'{v2} 명'
                    if v1:
                        set_cell_text(cells[1], v1)
                    if v2:
                        set_cell_text(cells[3], v2)
                    print(f"Step 8c: Filled employee count ({emp_fid}={v1}, {hire_fid}={v2})")

    # ── Step 8d: Fill staff table (참여인력) — from fill_content.json ──
    # Try named key first, then analysis field ID
    staff_data = fill_content.get('team_table')
    if staff_data is None:
        staff_fid = _find_field_id(analysis, 'table_content', '참여인력') or _find_field_id(analysis, 'table_content', '팀구성')
        staff_data = fill_content.get(staff_fid) if staff_fid else None
    # Normalize: list → dict with 'rows' of arrays
    if isinstance(staff_data, list):
        if staff_data and isinstance(staff_data[0], dict):
            col_order = ['순번', '직급', '성명', '주요_담당업무', '경력_및_학력', '채용연월', '참여율']
            rows = [[d.get(k, d.get(k.replace('_', ' '), '')) for k in col_order] for d in staff_data]
        else:
            rows = staff_data  # already list of lists
        staff_data = {'rows': rows}
    for tbl in body.findall(qn('w:tbl')):
        text = get_text(tbl)
        if '순번' in text and '직급' in text and '성명' in text and '참여율' in text:
            count = _fill_staff_table(tbl, staff_data, fill_content)
            if count:
                print(f"Step 8d: Filled staff table ({count} members)")
            else:
                print("Step 8d: Staff field not found in fill_content — skipped")
            break

    # ── Step 8e: Fill additional hiring table (추가 고용) — from fill_content.json ──
    hire_tbl_data = fill_content.get('hiring_table')
    if hire_tbl_data is None:
        hire_tbl_fid = _find_field_id(analysis, 'table_content', '추가') or _find_field_id(analysis, 'table_content', '고용계획')
        hire_tbl_data = fill_content.get(hire_tbl_fid) if hire_tbl_fid else None
    # Normalize: list → dict with 'rows' of arrays
    if isinstance(hire_tbl_data, list):
        if hire_tbl_data and isinstance(hire_tbl_data[0], dict):
            col_order = ['순번', '주요_담당업무', '요구_경력_학력', '채용시기']
            rows = [[d.get(k, d.get(k.replace('_', ' '), '')) for k in col_order] for d in hire_tbl_data]
        else:
            rows = hire_tbl_data  # already list of lists
        hire_tbl_data = {'rows': rows}
    for tbl in body.findall(qn('w:tbl')):
        text = get_text(tbl)
        if '주요 담당업무' in text and '요구되는' in text and '채용시기' in text:
            count = _fill_staff_table(tbl, hire_tbl_data, fill_content)
            if count:
                print(f"Step 8e: Filled hiring table ({count} positions)")
            else:
                print("Step 8e: Hiring field not found in fill_content — skipped")
            break

    # ── Save ──
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    doc.save(output_path)
    size = os.path.getsize(output_path)
    print(f"\nOutput: {output_path} ({size:,} bytes)")


if __name__ == '__main__':
    main()
