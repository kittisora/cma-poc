"""Deterministic narrative used when no AI key is configured (and as a fallback).

Built only from the computed CMA, so it never states anything the data does not show.
"""

from __future__ import annotations

from ..util.text import fmt_money


def template_narrative(cma: dict) -> str:
    s, v = cma["subject"], cma["valuation"]
    basis = v.get("primary_basis")
    b = v["bases"].get(basis) if basis else None
    sel = [c for c in cma["comps"] if c["selected"]]
    lines: list[str] = []

    lines.append("Summary")
    if b and b["available"]:
        area_word = "assessor above-grade" if basis == "above_grade" else "total finished"
        stat = "average" if v["point_statistic"] == "mean" else "median"
        lines.append(
            f"Based on {len(sel)} recorded sale{'s' if len(sel) != 1 else ''} near {s['address']}, the estimated value "
            f"as of {cma['valuation_date']} is {fmt_money(v['estimate'])}, with an indicated range of "
            f"{fmt_money(v['range_low'])} to {fmt_money(v['range_high'])}. The estimate applies the {stat} price per "
            f"{area_word} square foot of the comparable sales to the subject's {b['subject_area']:,.0f} sq ft.")
    else:
        lines.append("There is not yet enough information to estimate a value. Select comparable sales and confirm "
                     "the subject's square footage.")

    lines.append("")
    lines.append("Comparable sales")
    for c in sel:
        sale = c["sale"]
        dist = f"{c['distance_miles']:.2f} mi away" if c["distance_miles"] is not None else "distance not mapped"
        lines.append(f"- {c['address']} sold {sale['sale_date']} for {fmt_money(sale['price'])} ({dist}). "
                     f"{c['reason']} [PARID {c['pin']} · {sale['deed_ref']}]")
    if cma["search"].get("limit_explanation"):
        lines.append(cma["search"]["limit_explanation"])

    lines.append("")
    lines.append("Method")
    if b and b["available"]:
        lines.extend(b["lines"])
    if v["adjustments"]:
        lines.append("Adjustments are agent assumptions and should be reviewed: "
                     + "; ".join(f"{a['label']} {fmt_money(a['amount'])}" for a in v["adjustments"]) + ".")
    if cma.get("change_since_last_sale"):
        ch = cma["change_since_last_sale"]
        lines.append(f"Estimated change since the last sale ({ch['last_sale_date']}, {fmt_money(ch['last_sale_price'])}): "
                     f"{fmt_money(ch['amount'])} ({ch['pct']:+.1f}%).")

    lines.append("")
    lines.append("Condition and limitations")
    ce = cma["condition_evidence"]
    if ce["recorded"]:
        lines.append("County records show: " + "; ".join(ce["recorded"]) + ".")
    lines.append(ce["note"] + " To confirm: " + "; ".join(ce["needs_inspection"]) + ".")
    lines.append("Sale prices and dates are from recorded deeds in Fairfax County public records. Property "
                 "characteristics reflect the county's current record and may differ from each home's condition at "
                 "the time it sold. This CMA is not an appraisal.")
    return "\n".join(lines)
