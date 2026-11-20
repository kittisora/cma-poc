"""Excel export laid out like the client's CMA workbook.

Sheet "CMA" follows the workbook: the comp table, then MEAN / MODE / MEDIAN / HIGH / LOW,
then the "ESTIMATED PRICES" block (AVERAGE, MEDIAN, HIGH, LOW, MEAN VALUE, Appreciation,
ADD For Garage/ADU, SF, TOTAL). The figures are live formulas, so the agent can change an
input cell (red text) in Excel and every total updates. Each formula also stores the value
the app computed, so viewers that do not recalculate (iPhone/iPad preview, mail previews)
still show the numbers. Unlike the workbook, $/sf is always calculated (never typed in) and
TOTAL includes appreciation.
"""

from __future__ import annotations

import base64
import io
import statistics

import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell as cell

ORANGE = "#FFC000"  # workbook header colour (Q24:U24)
YELLOW = "#FFFF00"  # workbook estimate rows (Q25:U27)
RED = "#FF0000"     # workbook input text


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _stats(values: list[float]) -> dict:
    vals = [v for v in values if v is not None]
    if not vals:
        return {}
    try:
        mode = statistics.mode(vals) if len(set(vals)) < len(vals) else "NO MODE"
    except statistics.StatisticsError:
        mode = "NO MODE"
    return {"MEAN": statistics.fmean(vals), "MODE": mode, "MEDIAN": statistics.median(vals),
            "HIGH": max(vals), "LOW": min(vals)}


def render_xlsx(r: dict) -> bytes:
    cma, sel = r["_cma"], r["_selected"]
    s = cma["subject"]
    brand = r["branding"]
    accent = brand.get("primary_color") or "#1F4E79"

    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    wb.set_properties({"title": r["title"], "author": brand.get("company") or "", "comments": f"CMA {r['fingerprint']}"})
    wb.set_calc_mode("auto")

    F = lambda **kw: wb.add_format({"font_name": "Times New Roman", "font_size": 11, "valign": "vcenter", **kw})  # noqa: E731
    border = {"border": 1}
    f_company = F(bold=True, font_size=14, font_color=accent)
    f_title = F(bold=True, font_size=16)
    f_meta = F(font_color="#444444")
    f_head = F(bold=True, text_wrap=True, align="center", bg_color="#D9E1F2", **border)
    f_text = F(text_wrap=True, **border)
    f_center = F(align="center", **border)
    f_int = F(num_format="#,##0", **border)
    f_money = F(num_format="$#,##0", **border)
    f_ppsf = F(num_format="$#,##0.00", **border)
    f_date = F(num_format="yyyy-mm-dd", align="center", **border)
    f_dec = F(num_format="0.00", align="center", **border)
    f_subject = F(bold=True, bg_color="#DDEBF7", text_wrap=True, **border)
    f_subject_int = F(bold=True, bg_color="#DDEBF7", num_format="#,##0", **border)
    f_stat_label = F(bold=True, **border)
    f_stat_int = F(num_format="#,##0.0", **border)
    f_stat_money = F(num_format="$#,##0", **border)
    f_stat_ppsf = F(num_format="$#,##0.00", **border)
    f_blank = F(**border)
    f_est_title = F(bold=True, font_size=12)
    f_est_head = F(bold=True, text_wrap=True, align="center", bg_color=ORANGE, **border)
    f_est_label = F(bold=True, bg_color=YELLOW, text_wrap=True, **border)
    f_est_int = F(bold=True, bg_color=YELLOW, num_format="#,##0", **border)
    f_est_money = F(bold=True, bg_color=YELLOW, num_format="$#,##0.00", **border)
    f_est_in_int = F(bold=True, bg_color=YELLOW, font_color=RED, num_format="#,##0", **border)
    f_est_in_pct = F(bold=True, bg_color=YELLOW, font_color=RED, num_format="0.00%", **border)
    f_est_in_money = F(bold=True, bg_color=YELLOW, font_color=RED, num_format="#,##0", **border)
    f_total = F(bold=True, bg_color=ORANGE, num_format="$#,##0.00", **border)
    f_headline_label = F(bold=True, font_size=12)
    f_headline = F(bold=True, font_size=16, num_format="$#,##0", font_color=accent)
    f_note_head = F(bold=True, font_color=RED)
    f_note = F(text_wrap=True, valign="top")
    f_small = F(font_size=9, font_color="#555555", text_wrap=True, valign="top")
    f_link = F(font_size=9, font_color="#0563C1", underline=1)

    ws = wb.add_worksheet("CMA")
    ws.hide_gridlines(0)
    ws.set_landscape()
    ws.set_paper(1)  # US Letter
    ws.fit_to_pages(1, 0)
    ws.set_margins(left=0.3, right=0.3, top=0.5, bottom=0.5)
    ws.set_zoom(90)
    ws.set_footer(f"&L&8{brand.get('company') or ''} · CMA {r['fingerprint']}&R&8Page &P of &N")

    # ------------------------------------------------------------ header
    contact = " · ".join(x for x in [brand.get("agent_name"), brand.get("agent_title"), brand.get("phone"),
                                       brand.get("email"), brand.get("website")] if x)
    ws.write(0, 0, brand.get("company") or "", f_company)
    if contact:
        ws.write(0, 6, contact, f_meta)
    ws.write(1, 0, r["title"], f_title)
    where = f"{s['address']}, {s.get('city') or ''} VA {s.get('zip') or ''}".replace(" ,", ",")
    legal = " · ".join(x for x in [
        f"Parcel {s['pin']}",
        f"Subdivision {s['subdivision']}" if s.get("subdivision") else None,
        s.get("legal_description")] if x)
    ws.write(2, 0, f"Subject: {where}   ({legal})", f_meta)
    meta = f"Valuation date {r['valuation_date']} · Prepared {r['prepared_on']}"
    if r.get("prepared_for"):
        meta = f"Prepared for {r['prepared_for']} · {meta}"
    ws.write(3, 0, meta, f_meta)
    logo = r.get("_logo_bytes")
    if logo:
        try:
            ws.insert_image(0, 22, "logo.png", {"image_data": io.BytesIO(logo), "x_scale": 0.5, "y_scale": 0.5,
                                                 "object_position": 3})
        except Exception:  # an unreadable logo never blocks the export
            pass

    # --------------------------------------------------------- comp table
    cols = [
        ("COMP", 6, None), ("ADDRESS", 30, None), ("PARCEL ID", 16, None), ("SUBDIVISION", 22, None),
        ("LOT AREA (sf)", 13, None), ("YEAR BUILT", 10, None), ("STYLE", 14, None), ("BEDS", 7, None),
        ("BATHS (full/half)", 9, None), ("FIRE-PLACE", 8, None), ("BASEMENT", 13, None),
        ("TOTAL FINISHED SQFT", 13, None), ("ASSESSOR ABOVE GRADE SQFT", 13, None), ("EXTERIOR", 13, None),
        ("GARAGE", 18, None), ("CONDITION", 13, None), ("SOLD PRICE", 15, None), ("SOLD DATE", 12, None),
        ("PRICE per SQFT\n(based on Assessor SQFT)", 15, None),
        ("PRICE per SQFT\n(based on Total Finished SQFT)", 15, None),
        ("DISTANCE (mi)", 10, None), ("SALE VALIDITY", 22, None), ("DEED BOOK / PAGE", 14, None),
        ("SIMILARITY SCORE", 11, None),
    ]
    A, ADDR, PIN, SUB, LOT, YEAR, STYLE, BEDS, BATHS, FP, BSMT, TF, AG, EXT, GAR, COND, PRICE, DATE, PPSF_AG, \
        PPSF_TF, DIST, VALID, DEED, SCORE = range(len(cols))
    for i, (_, w, _) in enumerate(cols):
        ws.set_column(i, i, w)
    head_row = 5
    ws.set_row(head_row, 45)
    for i, (h, _, _) in enumerate(cols):
        ws.write(head_row, i, h, f_head)

    def property_cells(row: int, p: dict, fmt_text, fmt_int):
        ws.write(row, PIN, p.get("pin") or "", fmt_text)
        ws.write(row, SUB, p.get("subdivision") or "", fmt_text)
        ws.write(row, LOT, _num(p.get("lot_sf")) if p.get("lot_sf") else "", fmt_int)
        ws.write(row, YEAR, p.get("year_built") or "", fmt_text if fmt_text is f_subject else f_center)
        ws.write(row, STYLE, p.get("style") or "", fmt_text)
        ws.write(row, BEDS, p["beds"] if p.get("beds") is not None else "", fmt_text if fmt_text is f_subject else f_center)
        ws.write(row, BATHS, p.get("baths_label") or "", fmt_text if fmt_text is f_subject else f_center)
        ws.write(row, FP, p["fireplaces"] if p.get("fireplaces") is not None else "",
                 fmt_text if fmt_text is f_subject else f_center)
        ws.write(row, BSMT, p.get("basement") or "", fmt_text)
        ws.write(row, AG, _num(p.get("above_grade_sf")) or "", fmt_int)
        ws.write(row, EXT, p.get("exterior_wall") or "", fmt_text)
        ws.write(row, GAR, p.get("garage_evidence") or "Not recorded", fmt_text)
        ws.write(row, COND, " / ".join(x for x in [p.get("condition"), p.get("grade")] if x), fmt_text)

    # subject row (for comparison; not part of the statistics)
    srow = head_row + 1
    ws.write(srow, A, "SUBJ", f_subject)
    ws.write(srow, ADDR, s["address"], f_subject)
    property_cells(srow, s, f_subject, f_subject_int)
    ws.write(srow, TF, _num(s.get("total_finished_sf")) or "", f_subject_int)
    for c in (PRICE, DATE, PPSF_AG, PPSF_TF, DIST, VALID, DEED, SCORE):
        ws.write_blank(srow, c, None, f_subject)

    first = srow + 1
    for i, c in enumerate(sel):
        row = first + i
        p, sale = c["property"], c["sale"]
        ws.write(row, A, i + 1, f_center)
        ws.write(row, ADDR, c["address"], f_text)
        property_cells(row, p, f_text, f_int)
        tf = _num(c.get("total_finished_sf"))
        ws.write(row, TF, tf if tf else "", f_int)
        ws.write(row, PRICE, _num(sale.get("price")) or "", f_money)
        ws.write(row, DATE, sale.get("sale_date") or "", f_date)
        price, ag = cell(row, PRICE), cell(row, AG)
        ws.write_formula(row, PPSF_AG, f'=IF(AND(N({ag})>0,N({price})>0),{price}/{ag},"")', f_ppsf,
                         c["ppsf_above_grade"] if c.get("ppsf_above_grade") else "")
        tfc = cell(row, TF)
        ws.write_formula(row, PPSF_TF, f'=IF(AND(N({tfc})>0,N({price})>0),{price}/{tfc},"")', f_ppsf,
                         c["ppsf_total_finished"] if c.get("ppsf_total_finished") else "")
        ws.write(row, DIST, c["distance_miles"] if c.get("distance_miles") is not None else "", f_dec)
        ws.write(row, VALID, sale.get("validity") or "", f_text)
        ws.write(row, DEED, f"{sale.get('deed_book') or ''} / {sale.get('deed_page') or ''}", f_center)
        ws.write(row, SCORE, round(c["score"]), f_center)
    last = first + max(len(sel), 1) - 1
    if not sel:
        ws.write(first, ADDR, "No comparable sales selected", f_text)

    # ------------------------------------------------- MEAN / MODE / ...
    stat_cols = {
        LOT: ([_num(c["property"].get("lot_sf")) for c in sel], f_stat_int),
        TF: ([_num(c.get("total_finished_sf")) for c in sel], f_stat_int),
        AG: ([_num(c["property"].get("above_grade_sf")) for c in sel], f_stat_int),
        PRICE: ([_num(c["sale"].get("price")) for c in sel], f_stat_money),
        PPSF_AG: ([c.get("ppsf_above_grade") for c in sel], f_stat_ppsf),
        PPSF_TF: ([c.get("ppsf_total_finished") for c in sel], f_stat_ppsf),
    }
    funcs = {"MEAN": "AVERAGE", "MODE": "MODE", "MEDIAN": "MEDIAN", "HIGH": "MAX", "LOW": "MIN"}
    stat_row: dict[str, int] = {}
    row = last + 2
    for name, fn in funcs.items():
        stat_row[name] = row
        ws.write(row, ADDR, name, f_stat_label)
        for col, (vals, fmt) in stat_cols.items():
            rng = f"{cell(first, col)}:{cell(last, col)}"
            cached = _stats(vals).get(name, "")
            fallback = '"NO MODE"' if name == "MODE" else '""'
            ws.write_formula(row, col, f'=IF(COUNT({rng})=0,"",IFERROR({fn}({rng}),{fallback}))', fmt, cached)
        row += 1

    # ---------------------------------------------- ESTIMATED PRICES block
    pt = r["price_table"]
    row += 1
    ws.write(row, ADDR, "Appreciation", F(bold=True, font_color=RED))
    ws.write(row, PIN, f"at {r['appreciation_pct']:g}%", F(bold=True, font_color=RED, bg_color=YELLOW))
    row += 1
    est_head = row
    ws.set_row(est_head, 33)
    # columns used by the block (B..N), with headers as in the workbook
    E_LABEL, E_LOT, E_SF, E_AVG, E_MED, E_HIGH, E_LOW, E_MEAN, E_APP_PCT, E_APP, E_ADD, E_ADD_SF, E_TOTAL = \
        ADDR, PIN, SUB, LOT, YEAR, STYLE, BEDS, BATHS, FP, BSMT, TF, AG, EXT
    heads = {E_LABEL: "ESTIMATED PRICES", E_LOT: "LOT (sf)", E_SF: "FIN SF (subject)", E_AVG: "AVERAGE",
             E_MED: "MEDIAN", E_HIGH: "HIGH", E_LOW: "LOW",
             E_MEAN: "MEAN VALUE" if (pt and pt[0]["statistic"] == "mean") else "MEAN VALUE (median $/sf)",
             E_APP_PCT: "Appreciation %", E_APP: "Appreciation", E_ADD: "ADD For Garage/ADU",
             E_ADD_SF: "SF", E_TOTAL: "TOTAL"}
    for col, h in heads.items():
        ws.write(row, col, h, f_est_head)
    # the narrow beds/baths/fireplace columns carry dollar figures here; widen them
    for col in (E_HIGH, E_LOW, E_MEAN, E_APP_PCT, E_APP, E_ADD, E_TOTAL):
        ws.set_column(col, col, 16)

    adds = r["adjustments"]
    add_total = sum(a["amount"] for a in adds)
    add_sf = sum(a.get("sf") or 0 for a in adds) or None
    est_rows: dict[str, int] = {}
    ppsf_col = {"total_finished": PPSF_TF, "above_grade": PPSF_AG}
    for t in pt:
        row += 1
        est_rows[t["basis"]] = row
        pc = ppsf_col[t["basis"]]
        sf = cell(row, E_SF)
        label = f"{s['address']} — {t['label']}" + (" (headline)" if t["primary"] else " (cross-check)")
        ws.set_row(row, 30)
        ws.write(row, E_LABEL, label, f_est_label)
        ws.write(row, E_LOT, _num(t["lot_sf"]) or "", f_est_int)
        ws.write(row, E_SF, t["subject_area"], f_est_in_int)
        for col, stat, key in ((E_AVG, "MEAN", "mean"), (E_MED, "MEDIAN", "median"), (E_HIGH, "HIGH", "high"),
                               (E_LOW, "LOW", "low")):
            ws.write_formula(row, col, f'=IFERROR({sf}*{cell(stat_row[stat], pc)},"")', f_est_money,
                             t["indicated"][key])
        point = cell(row, E_AVG if t["statistic"] == "mean" else E_MED)
        ws.write_formula(row, E_MEAN, f"={point}", f_est_money, t["mean_value"])
        ws.write(row, E_APP_PCT, t["appreciation_pct"] / 100.0, f_est_in_pct)
        ws.write_formula(row, E_APP, f"={cell(row, E_MEAN)}*{cell(row, E_APP_PCT)}", f_est_money,
                         t["appreciation_amount"])
        ws.write(row, E_ADD, add_total, f_est_in_money)
        if add_sf:
            ws.write(row, E_ADD_SF, add_sf, f_est_in_int)
        else:
            ws.write_blank(row, E_ADD_SF, None, f_est_in_int)
        ws.write_formula(row, E_TOTAL, f"={cell(row, E_MEAN)}+{cell(row, E_APP)}+{cell(row, E_ADD)}", f_total,
                         t["total"])
    if not pt:
        row += 1
        ws.write(row, E_LABEL, "No method has enough data for an estimate.", f_est_label)

    # headline + range
    if pt:
        t = pt[0]
        er = est_rows[t["basis"]]
        row += 2
        ws.write(row, E_LABEL, "Estimated value (headline)", f_headline_label)
        ws.write_formula(row, E_LOT, f"={cell(er, E_TOTAL)}", f_headline, t["total"])
        row += 1
        ws.write(row, E_LABEL, "Range (low–high comp $/sf, same appreciation and adjustments)", f_note)
        lo = f"={cell(er, E_LOW)}*(1+{cell(er, E_APP_PCT)})+{cell(er, E_ADD)}"
        hi = f"={cell(er, E_HIGH)}*(1+{cell(er, E_APP_PCT)})+{cell(er, E_ADD)}"
        ws.write_formula(row, E_LOT, lo, F(num_format="$#,##0"), t["range_low"])
        ws.write(row, E_SF, "to", F(align="center"))
        ws.write_formula(row, E_AVG, hi, F(num_format="$#,##0"), t["range_high"])
        row += 1
        ws.write(row, E_LABEL, f"Method: {r['estimate']['basis']} ({r['estimate']['statistic']} $/sf)", f_small)

    # adjustments detail
    if adds:
        row += 2
        ws.write(row, E_LABEL, "ADD For Garage/ADU and other adjustments (agent assumptions)", f_stat_label)
        ws.write(row, E_LOT, "Amount", f_head)
        ws.write(row, E_SF, "SF", f_head)
        ws.merge_range(row, E_AVG, row, E_LOW, "Basis / note", f_head)
        for a in adds:
            row += 1
            ws.write(row, E_LABEL, a["label"], f_text)
            ws.write(row, E_LOT, a["amount"], f_money)
            ws.write(row, E_SF, a.get("sf") or "", f_int)
            ws.merge_range(row, E_AVG, row, E_LOW, a.get("note") or "", f_text)

    # notes
    row += 2
    ws.write(row, E_LABEL, "NOTES:", f_note_head)
    notes = [
        "Red figures are inputs: change FIN SF, Appreciation % or ADD For Garage/ADU and the totals update.",
        "$/sf = sold price ÷ area for each comp. AVERAGE/MEDIAN/HIGH/LOW = subject FIN SF × comp $/sf statistic. "
        "TOTAL = MEAN VALUE + Appreciation + ADD For Garage/ADU.",
        "Assessor above-grade sq ft is the county SFLA. Total finished sq ft includes finished basement and comes "
        "from the listing or agent input. The two are never mixed in one calculation.",
    ] + list(r.get("limitations") or [])
    for i, n in enumerate(notes, 1):
        row += 1
        ws.merge_range(row, E_LABEL, row, PRICE, f"{i})  {n}", f_note)
        ws.set_row(row, 15 * max(1, len(n) // 160 + 1))
    row += 2
    ws.merge_range(row, E_LABEL, row, PRICE, r["disclaimer"], f_small)
    ws.set_row(row, 42)
    if brand.get("footer_note"):
        row += 1
        ws.merge_range(row, E_LABEL, row, PRICE, brand["footer_note"], f_small)

    ws.freeze_panes(head_row + 1, ADDR + 1)
    ws.repeat_rows(head_row)
    ws.print_area(0, 0, row, len(cols) - 1)
    ws.activate()

    # ------------------------------------------------------- Subject sheet
    ss = wb.add_worksheet("Subject")
    ss.set_column(0, 0, 32)
    ss.set_column(1, 1, 48)
    ss.set_column(2, 2, 26)
    ss.write(0, 0, "Subject property", f_title)
    ss.write(2, 0, "Item", f_head)
    ss.write(2, 1, "Value", f_head)
    ss.write(2, 2, "Source", f_head)
    srows = list(r["subject_rows"])
    srows.insert(2, ("Subdivision", s.get("subdivision") or "—", "MAR"))
    srows.insert(3, ("Legal description", s.get("legal_description") or "—", "County legal"))
    for i, (a, b, c) in enumerate(srows, 3):
        ss.write(i, 0, a, f_text)
        ss.write(i, 1, str(b), f_text)
        ss.write(i, 2, c, f_text)
    row = 3 + len(srows) + 1
    if r.get("narrative"):
        ss.write(row, 0, "Analysis", f_est_title)
        for para in [p for p in r["narrative"].split("\n") if p.strip()]:
            row += 1
            ss.merge_range(row, 0, row, 2, para, f_note)
            ss.set_row(row, 15 * max(1, len(para) // 110 + 1))
        row += 2
    if r.get("map_png_b64"):
        ss.write(row, 0, "Location of comparable sales", f_est_title)
        ss.insert_image(row + 1, 0, "map.png", {"image_data": io.BytesIO(base64.b64decode(r["map_png_b64"])),
                                                "x_scale": 0.75, "y_scale": 0.75})

    # ------------------------------------------------------- Sources sheet
    so = wb.add_worksheet("Sources")
    for i, w in enumerate((30, 34, 46, 22)):
        so.set_column(i, i, w)
    so.write(0, 0, "Sources and record identifiers", f_title)
    if r.get("data_note"):
        so.write(1, 0, r["data_note"], f_meta)
    for i, h in enumerate(("Item", "Dataset", "Record", "Retrieved (UTC)")):
        so.write(3, i, h, f_head)
    row = 3
    for src in r["sources"]:
        row += 1
        so.write(row, 0, src["what"], f_text)
        so.write(row, 1, src["dataset"], f_text)
        so.write(row, 2, src["record_id"], f_text)
        so.write(row, 3, (src.get("retrieved_at") or "—")[:19], f_text)
    row += 2
    for ds in r.get("datasets", []):
        so.write_url(row, 0, ds["url"], f_link, ds["title"])
        row += 1
    row += 1
    so.merge_range(row, 0, row, 3, f"Data terms: {r['terms']['summary']}", f_small)
    so.set_row(row, 60)
    so.write_url(row + 1, 0, r["terms"]["url"], f_link)

    wb.close()
    return buf.getvalue()
