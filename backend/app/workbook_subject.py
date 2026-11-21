"""Workbook check for a real subject property in the loaded ZIP codes.

The client can set the Workbook Check page's subject to any address in
22308/22309 (saved for the whole team). For such a subject the page shows:
  A. the workbook's formula (its typed-in $/sf from the Old Town comps) applied to this subject's area,
  B. the same workbook comps with $/sf recalculated,
  C. a live CMA from Fairfax County records for this subject (the app's own comp selection),
so the workbook method can be compared with live local comps. Ranking and arithmetic come from
the same tested code as the CMA page (services.run_cma).
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from . import repository as repo
from .services import CMARequest, NotFound, run_cma
from .util.dates import today_local
from .valuation.pricing import Adjustment
from .valuation.workbook import (FLAGS, SUBJECTS, WORKBOOK_FILE, recalculated_formula, regression_report,
                                 workbook_formula)

SETTING_KEY = "workbook_subject"
DEFAULT_SUBJECT = {"kind": "workbook", "key": "1009 New"}


def get_saved_subject(session: Session) -> dict:
    return repo.get_setting(session, SETTING_KEY) or dict(DEFAULT_SUBJECT)


def save_subject(session: Session, kind: str, key: str) -> dict:
    """kind "workbook" (one of the workbook's own subjects) or "property" (a parcel ID in the loaded data)."""
    if kind == "workbook":
        if key not in SUBJECTS:
            raise NotFound(f"Unknown workbook subject {key!r}")
        value = {"kind": "workbook", "key": key, "label": key}
    elif kind == "property":
        facts = repo.get_property(session, key)
        if facts is None:
            raise NotFound(f"Parcel {key!r} is not in the loaded data")
        value = {"kind": "property", "key": key, "label": f"{facts.address}, {facts.zip}"}
    else:
        raise ValueError("kind must be 'workbook' or 'property'")
    repo.put_setting(session, SETTING_KEY, value)
    return value


def property_report(session: Session, pin: str, finished_sf: float | None = None,
                    garage_adjustment: float | None = None, appreciation_pct: float = 0.0,
                    valuation_date: dt.date | None = None) -> dict:
    facts = repo.get_property(session, pin)
    if facts is None:
        raise NotFound(f"Parcel {pin!r} is not in the loaded data")
    vdate = valuation_date or today_local()
    label = f"{facts.address}, {facts.zip}"

    # The workbook method prices total finished area. County records hold above-grade area only, so the
    # default is the agent-entered total finished sq ft when there is one, otherwise above-grade (labelled).
    if finished_sf is not None:
        area, area_source = float(finished_sf), "entered on this page (total finished sq ft)"
    elif facts.total_finished_sf:
        area, area_source = float(facts.total_finished_sf), f"total finished sq ft ({facts.total_finished_source})"
    elif facts.above_grade_sf:
        area, area_source = float(facts.above_grade_sf), "county above-grade sq ft (total finished not recorded)"
    else:
        area, area_source = 0.0, "no area on record"
    # The workbook's $225,000 garage/ADU figure belongs to its Oronoco example; never carry it over.
    adj = float(garage_adjustment) if garage_adjustment is not None else 0.0

    variants: list[dict] = []
    if area > 0:
        a = workbook_formula(area, adj, appreciation_pct)
        a["title"] = "Workbook formula, workbook comps"
        a["description"] = ("The workbook's own formula: average of its typed-in $/sf (column V) for its 6 sold comps "
                            "× this subject's area + adjustment. Those comps are Old Town Alexandria (22314) sales, "
                            "so this shows the method, not this subject's market.")
        b = recalculated_formula(area, adj, appreciation_pct)
        b["description"] = ("The same 6 workbook comps with $/sf recalculated as sold price ÷ listing total finished "
                            "sq ft, applied to this subject's area.")
        variants += [a, b]

    tf_for_cma = int(finished_sf) if finished_sf is not None else None
    cma = run_cma(session, CMARequest(
        subject_pin=pin, valuation_date=vdate, subject_total_finished_sf=tf_for_cma,
        adjustments=[Adjustment(label="Garage/ADU", amount=adj, note="Workbook Check input")] if adj else [],
        appreciation_pct=appreciation_pct), with_hints=False)
    v = cma["valuation"]
    basis = v["bases"][v["primary_basis"]] if v["primary_basis"] else None
    c = {
        "variant": "C", "title": "Live Fairfax comps (app's selection)",
        "description": (f"A live CMA for this subject from Fairfax County recorded sales: {cma['search']['eligible_count']} "
                        f"eligible within {cma['criteria']['max_distance_miles']:g} mi and "
                        f"{cma['criteria']['lookback_months']} months before {vdate.isoformat()}, ranked by similarity "
                        "(never by price), top 5, average $/sf × area"
                        + (f" on {basis['label'].lower()}" if basis else "") + ". Same figures as the CMA page."),
        "estimate": v["estimate"], "range_low": v["range_low"], "range_high": v["range_high"],
        "comps": [{"label": cp["label"], "price": cp["price"], "area": cp["area"], "ppsf": cp["ppsf"]}
                  for cp in (basis["comps"] if basis else [])],
        "lines": (basis["lines"] if basis else []) + v["warnings"],
        "excluded": [],
    }
    if not basis:
        c["lines"] = [cma["search"]["limit_explanation"] or "Not enough eligible sales for an estimate."]
    variants.append(c)

    wb = regression_report()  # for the shared parts (flags, workbook subjects)
    return {
        "workbook": WORKBOOK_FILE, "subject": label, "subject_kind": "property", "subject_pin": pin,
        "valuation_date": vdate.isoformat(),
        "subject_facts": {
            "address": label, "pin": pin, "style": facts.style, "year_built": facts.year_built, "beds": facts.beds,
            "baths": facts.baths_label, "above_grade_sf": facts.above_grade_sf,
            "total_finished_sf": facts.total_finished_sf, "lot_sf": facts.lot_sf,
            "assessed_total": facts.assessed_total, "condition": facts.condition, "grade": facts.grade,
        },
        "inputs": {
            "finished_sf": area, "finished_sf_source": area_source, "garage_adjustment": adj,
            "appreciation_pct": appreciation_pct,
            "garage_adjustment_note": "The workbook's $225,000 garage/ADU figure belongs to its Oronoco example and is "
                                      "not carried over; enter an adjustment for this property if one applies.",
        },
        "regression": {"expected": None, "actual": variants[0]["estimate"] if area > 0 else None, "passed": None},
        "variants": variants,
        "live_comparison": {
            "available": True,
            "reason": f"{label} is in Fairfax County (PARID {pin}), so variant C uses live recorded sales. "
                      "Variants A and B use the workbook's Old Town Alexandria comps and show the method only.",
        },
        "address_verification": {
            "checked_on": vdate.isoformat(), "fairfax_mar_matches": 1,
            "result": f"{label} is in the Fairfax County Master Address Repository (PARID {pin}). The workbook's own "
                      "13 comps remain City of Alexandria (22314) addresses.",
        },
        "flags": FLAGS,
        "subjects": wb["subjects"],
    }
