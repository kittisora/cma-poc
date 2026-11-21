"""Report model shared by the on-screen preview and the PDF, Excel and Word exports."""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import repository as repo
from ..services import CMARequest, run_cma
from ..sources.fairfax_arcgis import TERMS_SUMMARY, TERMS_URL
from ..sources.registry import get_provider
from ..util.dates import today_local
from ..util.text import fmt_int, fmt_money
from .mapimg import render_map_png


class Branding(BaseModel):
    company: str = "Your Brokerage"
    agent_name: str = ""
    agent_title: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    license_line: str = ""
    primary_color: str = "#1F4E79"
    logo_data_url: str | None = None
    footer_note: str = ""


class ReportRequest(BaseModel):
    cma: CMARequest
    branding: Branding | None = None
    narrative: str = ""
    narrative_source: str = "agent"  # agent | ai | template
    title: str | None = None
    prepared_for: str = ""
    include_sources: bool = True
    include_map: bool = True
    # The estimate the user reviewed on screen. Export is refused if the recomputed figure differs.
    expected_estimate: float | None = None


class FiguresChanged(Exception):
    pass


DISCLAIMER = (
    "This comparative market analysis is an opinion of value prepared for marketing purposes. It is not an "
    "appraisal and should not be relied on as one. Sale prices and dates come from recorded deeds in Fairfax County "
    "public records; property characteristics come from the county assessor's current record and may differ from "
    "each property's condition at the time of sale. The county provides its data without warranty of accuracy or "
    "completeness."
)


def _decode_logo(data_url: str | None) -> bytes | None:
    if not data_url or "," not in data_url:
        return None
    try:
        return base64.b64decode(data_url.split(",", 1)[1])
    except ValueError:
        return None


def figures_fingerprint(cma: dict) -> str:
    v = cma["valuation"]
    key = {"est": round(v["estimate"] or 0, 2), "lo": round(v["range_low"] or 0, 2),
           "hi": round(v["range_high"] or 0, 2), "sel": cma["selected_sale_ids"], "date": cma["valuation_date"]}
    return hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:12]


BASIS_SHORT = {"total_finished": "Total finished sq ft", "above_grade": "Assessor above-grade sq ft"}


def price_table(cma: dict) -> list[dict]:
    """The workbook's "ESTIMATED PRICES" block (rows 24-27), one row per method with enough data.

    AVERAGE / MEDIAN / HIGH / LOW = subject sq ft x comp $/sf statistic; MEAN VALUE is the chosen
    point statistic; TOTAL = MEAN VALUE + appreciation + garage/ADU and other adjustments.
    The headline method comes first.
    """
    v, s = cma["valuation"], cma["subject"]
    order = [v["primary_basis"]] + [b for b in ("total_finished", "above_grade") if b != v["primary_basis"]]
    rows = []
    for key in order:
        b = v["bases"].get(key) if key else None
        if not b or not b["available"]:
            continue
        rows.append({
            "basis": key, "label": BASIS_SHORT[key], "primary": key == v["primary_basis"],
            "lot_sf": s.get("lot_sf"), "subject_area": b["subject_area"], "n": b["n"],
            "ppsf": b["ppsf"], "indicated": b["indicated"], "statistic": v["point_statistic"],
            "mean_value": b["base_value"], "appreciation_pct": v["appreciation_pct"],
            "appreciation_amount": b["appreciation_amount"], "adjustments_total": b["adjustments_total"],
            "total": b["estimate"], "range_low": b["range_low"], "range_high": b["range_high"],
        })
    return rows


def build_report(session: Session, req: ReportRequest, default_branding: Branding) -> dict:
    cma = run_cma(session, req.cma, with_hints=False)
    v = cma["valuation"]
    if req.expected_estimate is not None and v["estimate"] is not None \
            and abs(req.expected_estimate - v["estimate"]) > 0.5:
        raise FiguresChanged(
            f"The recomputed estimate {fmt_money(v['estimate'])} differs from the reviewed figure "
            f"{fmt_money(req.expected_estimate)}. The data or inputs changed; review the CMA again before exporting.")
    b = req.branding or default_branding
    s = cma["subject"]
    sel = [c for c in cma["comps"] if c["selected"]]
    basis = v["primary_basis"]
    pb = v["bases"].get(basis) if basis else None
    other = [x for k, x in v["bases"].items() if k != basis]

    subject_rows = [
        ("Address", f"{s['address']}, {s.get('city') or ''} VA {s['zip'] or ''}".replace(" ,", ","), "MAR"),
        ("Parcel ID (PARID)", s["pin"], "County"),
        ("Property type", cma["subject_label"], "County land use"),
        ("Style", s["style"] or "—", "County dwelling"),
        ("Year built", s["year_built"] or "—", "County dwelling"),
        ("Bedrooms", s["beds"] if s["beds"] is not None else "—", "County dwelling"),
        ("Baths (full/half)", s["baths_label"] or "—", "County dwelling"),
        ("Above-grade living area", f"{fmt_int(s['above_grade_sf'])} sf" if s["above_grade_sf"] else "—",
         "County assessor (SFLA)"),
        ("Basement rec room", f"{fmt_int(s['rec_room_sf'])} sf" if s["rec_room_sf"] else "—", "County dwelling"),
        ("Total finished area", f"{fmt_int(s['total_finished_sf'])} sf" if s["total_finished_sf"] else "Not recorded",
         s["total_finished_source"] or "—"),
        ("Lot size", f"{fmt_int(s['lot_sf'])} sf ({s['lot_acres']} ac)" if s["lot_sf"] else "—", "County land"),
        ("Assessor condition / grade", f"{s['condition'] or '—'} / {s['grade'] or '—'}", "County dwelling"),
        ("Garage (recorded)", s["garage_evidence"] or "Not recorded", "County additions"),
        (f"Assessed value ({s['assessed_tax_year']})", fmt_money(s["assessed_total"]), "County assessment"),
    ]
    comp_rows = []
    for i, c in enumerate(sel, 1):
        p, sale = c["property"], c["sale"]
        comp_rows.append({
            "n": i, "rank": c["rank"], "address": c["address"], "sale_date": sale["sale_date"],
            "price": fmt_money(sale["price"]), "above_grade_sf": fmt_int(p["above_grade_sf"]),
            "ppsf_ag": f"${c['ppsf_above_grade']:,.0f}" if c["ppsf_above_grade"] else "—",
            "total_finished_sf": fmt_int(c["total_finished_sf"]) if c["total_finished_sf"] else "—",
            "ppsf_tf": f"${c['ppsf_total_finished']:,.0f}" if c["ppsf_total_finished"] else "—",
            "beds_baths": f"{p['beds'] if p['beds'] is not None else '—'} bd, {p['baths_label'] or '—'} ba",
            "year_built": p["year_built"] or "—", "lot_sf": fmt_int(p["lot_sf"]),
            "distance": f"{c['distance_miles']:.2f} mi" if c["distance_miles"] is not None else "—",
            "score": f"{c['score']:.0f}", "reason": c["reason"], "record_id": c["source"]["record_id"],
            "retrieved_at": c["source"]["retrieved_at"],
        })

    map_png = None
    if req.include_map and s["lat"] is not None:
        map_png = render_map_png((s["lat"], s["lon"]), [(c["lat"], c["lon"]) for c in sel if c["lat"] is not None],
                                 b.primary_color)

    sources = []
    if req.include_sources:
        for src in cma["sources"]:
            sources.append({"what": "Subject", **src})
        for i, c in enumerate(sel, 1):
            sources.append({"what": f"Comp {i}: {c['address']}", **c["source"]})
        for a in v["adjustments"]:
            sources.append({"what": f"Adjustment: {a['label']}", "dataset": "Agent assumption",
                            "record_id": a.get("note") or "entered in the CMA", "retrieved_at": None, "url": None,
                            "kind": "agent_input"})
    status = repo.data_status(session)
    estimate_block = {
        "estimate": fmt_money(v["estimate"]), "range": f"{fmt_money(v['range_low'])} – {fmt_money(v['range_high'])}",
        "basis": pb["label"] if pb else "No method available",
        "statistic": "average" if v["point_statistic"] == "mean" else "median",
        "change": cma["change_since_last_sale"],
        "raw": {"estimate": v["estimate"], "range_low": v["range_low"], "range_high": v["range_high"]},
    }
    return {
        "title": req.title or f"Comparative Market Analysis — {s['address']}",
        "prepared_for": req.prepared_for, "prepared_on": today_local().isoformat(),
        "valuation_date": cma["valuation_date"], "branding": b.model_dump(), "subject_rows": subject_rows,
        "estimate": estimate_block, "method_lines": pb["lines"] if pb else [],
        "other_methods": [{"label": o["label"], "available": o["available"],
                           "estimate": fmt_money(o["estimate"]) if o["available"] else None,
                           "reason": o["reason_unavailable"], "lines": o["lines"]} for o in other],
        "adjustments": v["adjustments"], "appreciation_pct": v["appreciation_pct"], "comps": comp_rows,
        "price_table": price_table(cma),
        "map_png_b64": base64.b64encode(map_png).decode() if map_png else None,
        "narrative": req.narrative.strip(), "narrative_source": req.narrative_source,
        "condition_evidence": cma["condition_evidence"], "limitations": cma["warnings"]
        + ([cma["search"]["limit_explanation"]] if cma["search"]["limit_explanation"] else []),
        "sources": sources,
        "data_note": (f"Fairfax County records retrieved {status['last_refresh']['finished_at'][:10]}; latest recorded "
                      f"sale in the database {status['latest_sale_date']}.") if status["last_refresh"] else "",
        "terms": {"summary": TERMS_SUMMARY, "url": TERMS_URL},
        "datasets": [{"title": d.title, "url": d.url} for d in get_provider().static_info().datasets
                     if d.key in ("mar", "sales", "dwelling", "parcels", "land", "values")]
        if req.include_sources else [], "disclaimer": DISCLAIMER,
        "fingerprint": figures_fingerprint(cma), "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "_logo_bytes": _decode_logo(b.logo_data_url),
        "_cma": cma, "_selected": sel,
    }


def public_model(report: dict) -> dict:
    return {k: v for k, v in report.items() if not k.startswith("_")}
