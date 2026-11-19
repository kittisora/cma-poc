from __future__ import annotations

import base64
import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    CondPageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from xml.sax.saxutils import escape


def _hex(c: str) -> colors.Color:
    try:
        return colors.HexColor(c)
    except (ValueError, TypeError):
        return colors.HexColor("#1F4E79")


def render_pdf(r: dict) -> bytes:
    brand = r["branding"]
    accent = _hex(brand.get("primary_color") or "#1F4E79")
    ss = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=ss["BodyText"], fontName="Helvetica", fontSize=9.5, leading=13)
    small = ParagraphStyle("small", parent=body, fontSize=7.5, leading=9.5, textColor=colors.HexColor("#444444"))
    tiny = ParagraphStyle("tiny", parent=small, fontSize=6.8, leading=8.5)
    h1 = ParagraphStyle("h1", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=17, leading=21,
                        textColor=accent, alignment=0, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15,
                        textColor=accent, spaceBefore=10, spaceAfter=4)
    big = ParagraphStyle("big", parent=body, fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=accent)
    right = ParagraphStyle("right", parent=small, alignment=TA_RIGHT)

    def P(text, style=body):
        # keep runs of spaces: parcel IDs such as "1022 03  0082A" must stay exact
        return Paragraph(escape(str(text)).replace("  ", "&nbsp; ").replace("\n", "<br/>"), style)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER, leftMargin=0.6 * inch, rightMargin=0.6 * inch,
                            topMargin=0.6 * inch, bottomMargin=0.7 * inch, title=r["title"],
                            author=brand.get("company") or "")
    width = LETTER[0] - 1.2 * inch
    story = []

    # header
    contact = " · ".join(x for x in [brand.get("agent_name"), brand.get("agent_title"), brand.get("phone"),
                                       brand.get("email"), brand.get("website")] if x)
    left = [P(brand.get("company") or "", ParagraphStyle("co", parent=body, fontName="Helvetica-Bold",
                                                         fontSize=12, textColor=accent)), P(contact, small)]
    if brand.get("license_line"):
        left.append(P(brand["license_line"], small))
    logo = r.get("_logo_bytes")
    head = [[left, Image(io.BytesIO(logo), width=1.4 * inch, height=0.7 * inch, kind="proportional") if logo else ""]]
    t = Table(head, colWidths=[width - 1.6 * inch, 1.6 * inch])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                           ("LINEBELOW", (0, 0), (-1, 0), 1.2, accent), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story += [t, Spacer(1, 8), P(r["title"], h1)]
    meta = f"Valuation date {r['valuation_date']} · Prepared {r['prepared_on']}"
    if r.get("prepared_for"):
        meta = f"Prepared for {r['prepared_for']} · " + meta
    story.append(P(meta, small))
    story.append(Spacer(1, 8))

    # estimate box
    e = r["estimate"]
    est_lines = [P("Estimated value", small), P(e["estimate"], big), P(f"Range {e['range']}", body),
                 P(f"Method: {e['basis']} ({e['statistic']})", small)]
    if e.get("change"):
        ch = e["change"]
        est_lines.append(P(f"{ch['label']}: {'+' if ch['amount'] >= 0 else '-'}${abs(ch['amount']):,.0f} "
                           f"({ch['pct']:+.1f}%) vs ${ch['last_sale_price']:,.0f} on {ch['last_sale_date']}", small))
    box = Table([[est_lines]], colWidths=[width])
    box.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1, accent), ("BACKGROUND", (0, 0), (-1, -1),
                                                                     colors.HexColor("#F5F8FB")),
                             ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 8),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story += [box, Spacer(1, 6)]

    # subject
    story.append(P("Subject property", h2))
    rows = [[P("Item", small), P("Value", small), P("Source", small)]] + \
           [[P(a, body), P(b, body), P(c, small)] for a, b, c in r["subject_rows"]]
    st = Table(rows, colWidths=[width * 0.32, width * 0.43, width * 0.25], repeatRows=1)
    st.setStyle(_grid(accent))
    story.append(st)

    # comps
    story.append(P("Comparable sales", h2))
    hdr = ["#", "Address", "Sold", "Price", "AG sf", "$/AG sf", "TF sf", "$/TF sf", "Beds / baths", "Built", "Dist.", "Score"]
    data = [[P(h, tiny) for h in hdr]]
    for c in r["comps"]:
        data.append([P(c["n"], tiny), P(c["address"], tiny), P(c["sale_date"], tiny), P(c["price"], tiny),
                     P(c["above_grade_sf"], tiny), P(c["ppsf_ag"], tiny), P(c["total_finished_sf"], tiny),
                     P(c["ppsf_tf"], tiny), P(c["beds_baths"], tiny), P(c["year_built"], tiny),
                     P(c["distance"], tiny), P(c["score"], tiny)])
    cw = [0.25, 1.55, 0.68, 0.72, 0.48, 0.52, 0.48, 0.52, 0.5, 0.42, 0.45, 0.4]
    scale = width / (sum(cw) * inch)
    ct = Table(data, colWidths=[w * inch * scale for w in cw], repeatRows=1)
    ct.setStyle(_grid(accent))
    story.append(ct)
    story.append(P("AG = county assessor above-grade living area. TF = total finished area (agent input or listing). "
                   "Score = similarity to the subject (0–100); ranking does not use price.", tiny))
    for c in r["comps"]:
        story.append(P(f"{c['n']}. {c['address']} — {c['reason']}", small))

    if r.get("map_png_b64"):
        img = Image(io.BytesIO(base64.b64decode(r["map_png_b64"])), width=width, height=width * 0.56)
        story.append(KeepTogether([P("Location of comparable sales", h2), img]))

    # method
    story.append(P("How the estimate was calculated", h2))
    for line in r["method_lines"]:
        story.append(P("• " + line, body))
    for o in r["other_methods"]:
        if o["available"]:
            story.append(P(f"Cross-check — {o['label']}: {o['estimate']}", small))
        else:
            story.append(P(f"{o['label']}: not used — {o['reason']}", small))
    if r["adjustments"]:
        story.append(P("Adjustments are agent assumptions: " + "; ".join(
            f"{a['label']} ${a['amount']:,.0f}" + (f" ({a['note']})" if a.get("note") else "") for a in r["adjustments"]),
            small))

    if r.get("narrative"):
        story.append(P("Analysis", h2))
        for para in r["narrative"].split("\n"):
            story.append(P(para, body) if para.strip() else Spacer(1, 4))

    story.append(P("Condition evidence", h2))
    ce = r["condition_evidence"]
    for x in ce["recorded"]:
        story.append(P("• " + x, body))
    story.append(P(ce["note"], body))
    story.append(P("To confirm: " + "; ".join(ce["needs_inspection"]), small))

    if r["limitations"]:
        story.append(P("Data notes and limitations", h2))
        for x in r["limitations"]:
            story.append(P("• " + x, small))

    if r["sources"]:
        story.append(CondPageBreak(2.5 * inch))
        story.append(P("Sources and record identifiers", h2))
        if r.get("data_note"):
            story.append(P(r["data_note"], small))
        srows = [[P("Item", tiny), P("Dataset", tiny), P("Record", tiny), P("Retrieved (UTC)", tiny)]]
        for s in r["sources"]:
            srows.append([P(s["what"], tiny), P(s["dataset"], tiny), P(s["record_id"], tiny),
                          P((s.get("retrieved_at") or "—")[:19], tiny)])
        stt = Table(srows, colWidths=[width * 0.22, width * 0.26, width * 0.37, width * 0.15], repeatRows=1)
        stt.setStyle(_grid(accent))
        story.append(stt)
        story.append(Spacer(1, 6))
        for ds in r.get("datasets", []):
            story.append(P(f"{ds['title']}: {ds['url']}", tiny))
        story.append(P(f"Data terms: {r['terms']['summary']} ({r['terms']['url']})", tiny))

    story.append(Spacer(1, 8))
    story.append(P(r["disclaimer"], tiny))
    if r["branding"].get("footer_note"):
        story.append(P(r["branding"]["footer_note"], tiny))

    def on_page(canvas, d):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(0.6 * inch, 0.4 * inch, f"{brand.get('company') or ''} · CMA {r['fingerprint']} · "
                                                  f"Valuation date {r['valuation_date']}")
        canvas.drawRightString(LETTER[0] - 0.6 * inch, 0.4 * inch, f"Page {d.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()


def _grid(accent) -> TableStyle:
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2F6")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, accent),
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#D0D7DE")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ])
