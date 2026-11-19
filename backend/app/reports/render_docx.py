from __future__ import annotations

import base64
import io

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


def _rgb(hex_color: str) -> RGBColor:
    h = (hex_color or "#1F4E79").lstrip("#")
    try:
        return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except (ValueError, IndexError):
        return RGBColor(0x1F, 0x4E, 0x79)


def _shade(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def _table(doc, header: list[str], rows: list[list], font_size: float = 8, widths: list[float] | None = None):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        cell = t.rows[0].cells[i]
        cell.text = ""
        run = cell.paragraphs[0].add_run(h)
        run.bold = True
        run.font.size = Pt(font_size)
        _shade(cell, "EEF2F6")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            run = cells[i].paragraphs[0].add_run("" if v is None else str(v))
            run.font.size = Pt(font_size)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Inches(w)
    return t


def render_docx(r: dict) -> bytes:
    brand = r["branding"]
    accent = _rgb(brand.get("primary_color"))
    doc = Document()
    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.PORTRAIT
    sec.left_margin = sec.right_margin = Inches(0.7)
    sec.top_margin = sec.bottom_margin = Inches(0.7)
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10)
    for name in ("Heading 1", "Heading 2"):
        doc.styles[name].font.color.rgb = accent

    # header with branding
    header = sec.header.paragraphs[0]
    logo = r.get("_logo_bytes")
    if logo:
        header.add_run().add_picture(io.BytesIO(logo), height=Inches(0.5))
        header.add_run("   ")
    hr = header.add_run(brand.get("company") or "")
    hr.bold = True
    hr.font.color.rgb = accent
    contact = " · ".join(x for x in [brand.get("agent_name"), brand.get("agent_title"), brand.get("phone"),
                                       brand.get("email"), brand.get("website")] if x)
    if contact:
        header.add_run("\n" + contact).font.size = Pt(8)
    footer = sec.footer.paragraphs[0]
    fr = footer.add_run(f"{brand.get('company') or ''} · CMA {r['fingerprint']} · Valuation date {r['valuation_date']}")
    fr.font.size = Pt(7)

    doc.add_heading(r["title"], level=1)
    meta = f"Valuation date {r['valuation_date']} · Prepared {r['prepared_on']}"
    if r.get("prepared_for"):
        meta = f"Prepared for {r['prepared_for']} · " + meta
    doc.add_paragraph(meta).runs[0].font.size = Pt(8)

    e = r["estimate"]
    p = doc.add_paragraph()
    p.add_run("Estimated value  ").font.size = Pt(10)
    run = p.add_run(e["estimate"])
    run.bold = True
    run.font.size = Pt(20)
    run.font.color.rgb = accent
    doc.add_paragraph(f"Range {e['range']}")
    doc.add_paragraph(f"Method: {e['basis']} ({e['statistic']})").runs[0].font.size = Pt(8)
    if e.get("change"):
        ch = e["change"]
        doc.add_paragraph(f"{ch['label']}: {'+' if ch['amount'] >= 0 else '-'}${abs(ch['amount']):,.0f} "
                          f"({ch['pct']:+.1f}%) vs ${ch['last_sale_price']:,.0f} on {ch['last_sale_date']}"
                          ).runs[0].font.size = Pt(8)

    doc.add_heading("Subject property", level=2)
    _table(doc, ["Item", "Value", "Source"], [[a, b, c] for a, b, c in r["subject_rows"]], 8.5, [2.2, 2.9, 1.9])

    doc.add_heading("Comparable sales", level=2)
    hdr = ["#", "Address", "Sold", "Price", "AG sf", "$/AG sf", "TF sf", "$/TF sf", "Beds / baths", "Built", "Dist.", "Score"]
    _table(doc, hdr, [[c["n"], c["address"], c["sale_date"], c["price"], c["above_grade_sf"], c["ppsf_ag"],
                       c["total_finished_sf"], c["ppsf_tf"], c["beds_baths"], c["year_built"], c["distance"],
                       c["score"]] for c in r["comps"]], 7)
    doc.add_paragraph("AG = county assessor above-grade living area. TF = total finished area (agent input or "
                      "listing). Score = similarity to the subject (0–100); ranking does not use price."
                      ).runs[0].font.size = Pt(7)
    for c in r["comps"]:
        doc.add_paragraph(f"{c['n']}. {c['address']} — {c['reason']}").runs[0].font.size = Pt(8)

    if r.get("map_png_b64"):
        doc.add_heading("Location of comparable sales", level=2)
        doc.add_picture(io.BytesIO(base64.b64decode(r["map_png_b64"])), width=Inches(6.8))

    doc.add_heading("How the estimate was calculated", level=2)
    for line in r["method_lines"]:
        doc.add_paragraph(line, style="List Bullet")
    for o in r["other_methods"]:
        txt = (f"Cross-check — {o['label']}: {o['estimate']}" if o["available"]
               else f"{o['label']}: not used — {o['reason']}")
        doc.add_paragraph(txt).runs[0].font.size = Pt(8)
    if r["adjustments"]:
        doc.add_paragraph("Adjustments are agent assumptions: " + "; ".join(
            f"{a['label']} ${a['amount']:,.0f}" + (f" ({a['note']})" if a.get("note") else "")
            for a in r["adjustments"])).runs[0].font.size = Pt(8)

    if r.get("narrative"):
        doc.add_heading("Analysis", level=2)
        for para in r["narrative"].split("\n"):
            if para.strip():
                doc.add_paragraph(para)

    doc.add_heading("Condition evidence", level=2)
    ce = r["condition_evidence"]
    for x in ce["recorded"]:
        doc.add_paragraph(x, style="List Bullet")
    doc.add_paragraph(ce["note"])
    doc.add_paragraph("To confirm: " + "; ".join(ce["needs_inspection"])).runs[0].font.size = Pt(8)

    if r["limitations"]:
        doc.add_heading("Data notes and limitations", level=2)
        for x in r["limitations"]:
            doc.add_paragraph(x, style="List Bullet").runs[0].font.size = Pt(8)

    if r["sources"]:
        doc.add_page_break()
        doc.add_heading("Sources and record identifiers", level=2)
        if r.get("data_note"):
            doc.add_paragraph(r["data_note"]).runs[0].font.size = Pt(8)
        _table(doc, ["Item", "Dataset", "Record", "Retrieved (UTC)"],
               [[s["what"], s["dataset"], s["record_id"], (s.get("retrieved_at") or "—")[:19]] for s in r["sources"]],
               7, [1.6, 1.8, 2.6, 1.0])
        for ds in r.get("datasets", []):
            doc.add_paragraph(f"{ds['title']}: {ds['url']}").runs[0].font.size = Pt(7)
        doc.add_paragraph(f"Data terms: {r['terms']['summary']} ({r['terms']['url']})").runs[0].font.size = Pt(7)

    doc.add_paragraph(r["disclaimer"]).runs[0].font.size = Pt(7)
    if brand.get("footer_note"):
        doc.add_paragraph(brand["footer_note"]).runs[0].font.size = Pt(7)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
