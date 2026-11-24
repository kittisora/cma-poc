"""One code path for a CMA: the API, the report exporter and the AI agent all
call `run_cma`, so every surface shows the same figures."""

from __future__ import annotations

import datetime as dt
import time
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import repository as repo
from .comps.engine import (
    OPTIONAL_VALIDITY,
    CompCriteria,
    CompSearch,
    RankedComp,
    find_comps,
    limit_explanation,
    relaxation_hints,
)
from .domain import PropertyFacts, SaleFacts, SourceRef
from .util.dates import subtract_months, today_local
from .util.text import PROPERTY_TYPE_LABELS
from .valuation.pricing import (
    Adjustment,
    CompArea,
    ValuationInput,
    change_since_last_sale,
    compute_valuation,
)

MARKET_VALIDITY = {"valid and verified sale", "sale from lender - valid sale price", "pending verification",
                   "valid and verified multi-parcel sale"}


class SubjectPlan(BaseModel):
    """The house the agent is selling or building, when it differs from the county record
    (for example a new 5-bedroom house replacing an older one). Blank fields keep the county value.
    Planned values drive comp ranking and pricing and are labelled as agent input everywhere."""
    property_type: Literal["DETACHED", "TOWNHOUSE", "CONDO", "DUPLEX"] | None = None  # e.g. building on vacant land
    beds: int | None = Field(None, ge=0, le=20)
    full_baths: int | None = Field(None, ge=0, le=20)
    half_baths: int | None = Field(None, ge=0, le=20)
    above_grade_sf: int | None = Field(None, ge=100, le=30000)
    total_finished_sf: int | None = Field(None, ge=100, le=30000)
    year_built: int | None = Field(None, ge=1700, le=2100)
    style: str | None = Field(None, max_length=60)
    condition: str | None = Field(None, max_length=40)
    basement: str | None = Field(None, max_length=60)  # e.g. "Full" or "None"
    note: str | None = Field(None, max_length=300)


PLAN_LABELS = {"property_type": "Property type", "beds": "Bedrooms", "full_baths": "Full baths", "half_baths": "Half baths",
               "above_grade_sf": "Above-grade living area", "total_finished_sf": "Total finished area",
               "year_built": "Year built", "style": "Style", "condition": "Condition", "basement": "Basement"}
PLAN_SOURCE = "planned house (agent input)"


def apply_plan(subject: PropertyFacts, plan: SubjectPlan | None) -> dict | None:
    """Overwrite the subject's facts with the planned house. Returns the county values it replaced."""
    if plan is None:
        return None
    replaced = {}
    for f in PLAN_LABELS:
        v = getattr(plan, f)
        if isinstance(v, str):
            v = v.strip() or None
        if v is None:
            continue
        replaced[f] = getattr(subject, f)
        setattr(subject, f, v)
        subject.planned.append(f)
    if not replaced:
        return None
    if "total_finished_sf" in replaced:
        subject.total_finished_source = PLAN_SOURCE
    if "year_built" in replaced:
        subject.year_remodeled = None  # a remodel date belongs to the house on record
    changes = ", ".join(f"{PLAN_LABELS[f].lower()} {getattr(subject, f)}" for f in replaced)
    subject.notes.insert(0, f"Planned house (agent input): {changes}. Comps are ranked and priced against these "
                            "values, not the county record of the current house.")
    subject.sources.append(SourceRef("Agent input", "planned house: " + changes + (f" ({plan.note})" if plan.note else ""),
                                     None, None, kind="agent_input"))
    return replaced


class CMARequest(BaseModel):
    subject_pin: str
    valuation_date: dt.date | None = None
    criteria: CompCriteria = Field(default_factory=CompCriteria)
    selected_sale_ids: list[int] | None = None  # None = use the top-ranked comps
    subject_total_finished_sf: int | None = None
    plan: SubjectPlan | None = None  # describe a planned / new house; blank fields keep the county record
    comp_total_finished: dict[int, int] = Field(default_factory=dict)  # sale_id -> sq ft
    adjustments: list[Adjustment] = Field(default_factory=list)
    appreciation_pct: float = 0.0
    point_statistic: Literal["mean", "median"] = "mean"
    primary_basis: Literal["auto", "above_grade", "total_finished"] = "auto"
    candidate_limit: int = 40


class NotFound(Exception):
    pass


def serialize_comp(rc: RankedComp, selected: bool, tf: tuple[int | None, str | None]) -> dict:
    p, s = rc.prop, rc.sale
    return {
        "sale_id": s.sale_id, "rank": rc.rank, "score": round(rc.score, 1), "selected": selected,
        "address": p.address, "pin": p.pin, "zip": p.zip, "lat": p.lat, "lon": p.lon,
        "distance_miles": None if rc.distance_miles is None else round(rc.distance_miles, 3),
        "months_before": round(rc.months_before, 1),
        "sale": s.to_dict(), "property": p.to_dict(),
        "ppsf_above_grade": (s.price / p.above_grade_sf) if s.price and p.above_grade_sf else None,
        "total_finished_sf": tf[0], "total_finished_source": tf[1],
        "ppsf_total_finished": (s.price / tf[0]) if s.price and tf[0] else None,
        "factors": [f.to_dict() for f in rc.factors], "reason": rc.reason, "strengths": rc.strengths,
        "differences": rc.differences, "missing": rc.missing, "warnings": rc.warnings,
        "source": s.source_ref(repo.layer_url("sales")).to_dict(),
    }


def _comp_total_finished(req: CMARequest, sale: SaleFacts, prop: PropertyFacts) -> tuple[int | None, str | None]:
    if sale.sale_id in req.comp_total_finished and req.comp_total_finished[sale.sale_id]:
        return req.comp_total_finished[sale.sale_id], "agent input (this CMA)"
    if prop.total_finished_sf:
        return prop.total_finished_sf, prop.total_finished_source
    if sale.total_finished_sf:
        return sale.total_finished_sf, "listing data"
    return None, None


def last_sales(history: list[SaleFacts], valuation_date: dt.date) -> tuple[SaleFacts | None, SaleFacts | None]:
    """(latest recorded transfer of any kind, latest market sale) on or before the valuation date."""
    before = [s for s in history if s.sale_date <= valuation_date]
    latest_any = before[0] if before else None
    market = next((s for s in before if (s.validity or "").lower() in MARKET_VALIDITY and (s.price or 0) > 0
                   and not s.multi_parcel), None)
    return latest_any, market


def run_cma(session: Session, req: CMARequest, with_hints: bool = True) -> dict:
    t0 = time.perf_counter()
    vdate = req.valuation_date or today_local()
    subject = repo.get_property(session, req.subject_pin)
    if subject is None:
        raise NotFound(f"Parcel {req.subject_pin!r} is not in the loaded data.")
    if req.subject_total_finished_sf:
        subject.total_finished_sf = req.subject_total_finished_sf
        subject.total_finished_source = "agent input (this CMA)"
    county_values = apply_plan(subject, req.plan)
    c = req.criteria

    start = subtract_months(vdate, c.lookback_months * 2)
    candidates: list = []
    if subject.lat is not None:
        candidates = repo.get_candidate_sales(session, subject.lat, subject.lon, c.max_distance_miles * 2, start)
    if c.area_scope != "radius" and (subject.subdivision or "").strip():
        # the subdivision can reach beyond the radius; add its sales (once each)
        seen = {s.sale_id for s, _ in candidates}
        candidates += [x for x in repo.get_candidate_sales_in_subdivision(session, subject.subdivision, start)
                       if x[0].sale_id not in seen]
    search: CompSearch = find_comps(subject, candidates, vdate, c)
    hints = relaxation_hints(subject, candidates, vdate, c) if (with_hints and search.limited) else []

    eligible_ids = {rc.sale.sale_id for rc in search.eligible}
    if req.selected_sale_ids is None:
        selected_ids = [rc.sale.sale_id for rc in search.top]
        selection_mode = "auto"
    else:
        selected_ids = [i for i in req.selected_sale_ids if i in eligible_ids]
        selection_mode = "manual"
    dropped = [i for i in (req.selected_sale_ids or []) if i not in eligible_ids]
    by_id = {rc.sale.sale_id: rc for rc in search.eligible}
    selected = [by_id[i] for i in selected_ids]

    comp_areas = []
    for rc in selected:
        tf, tf_src = _comp_total_finished(req, rc.sale, rc.prop)
        comp_areas.append(CompArea(
            sale_id=rc.sale.sale_id, label=rc.prop.address or rc.prop.pin, price=rc.sale.price or 0,
            sale_date=rc.sale.sale_date.isoformat(), above_grade_sf=rc.prop.above_grade_sf,
            total_finished_sf=tf, total_finished_source=tf_src,
            record_id=rc.sale.source_ref().record_id))
    valuation = compute_valuation(ValuationInput(
        subject_label=subject.address or subject.pin, subject_above_grade_sf=subject.above_grade_sf,
        subject_total_finished_sf=subject.total_finished_sf,
        subject_total_finished_source=subject.total_finished_source, comps=comp_areas,
        adjustments=req.adjustments, appreciation_pct=req.appreciation_pct,
        point_statistic=req.point_statistic, primary_basis=req.primary_basis, min_comps=c.min_comps,
    ))

    history = repo.get_sale_history(session, subject.pin)
    latest_any, last_market = last_sales(history, vdate)
    # the last sale was of the house on record; it says nothing about a planned / new house
    change = None if county_values else change_since_last_sale(
        valuation.estimate, last_market.price if last_market else None,
        last_market.sale_date.isoformat() if last_market else None)

    shown = search.eligible[: max(req.candidate_limit, len(selected_ids))]
    shown_ids = {rc.sale.sale_id for rc in shown}
    shown += [rc for rc in selected if rc.sale.sale_id not in shown_ids]

    warnings = list(search.warnings) + list(valuation.warnings)
    if dropped:
        warnings.append(f"{len(dropped)} previously selected comp(s) no longer meet the rules and were removed.")
    if subject.property_type not in PROPERTY_TYPE_LABELS or subject.property_type == "OTHER":
        warnings.append(f"The subject's land use is '{subject.land_use}', which is not a residential sale type "
                        "this tool is designed for.")
    if not subject.total_finished_sf:
        warnings.append("Total finished sq ft is not in county records. Enter it (from the listing or a "
                        "measurement) to use the workbook's total-finished method; until then the estimate uses "
                        "assessor above-grade area.")
    condition_gaps = condition_evidence_gaps(subject)

    return {
        "subject": subject.to_dict(),
        "plan": req.plan.model_dump() if county_values else None,
        "county_values": county_values,  # what the planned house replaced, field -> county value
        "subject_label": PROPERTY_TYPE_LABELS.get(subject.property_type, subject.property_type),
        "valuation_date": vdate.isoformat(),
        "criteria": c.model_dump(),
        "validity_options": {"default": c.allowed_validity, "optional": OPTIONAL_VALIDITY},
        "search": {
            "window_start": search.window_start.isoformat(), "pool_count": search.pool_count,
            "scope": search.scope, "scope_label": search.scope_label,
            "funnel": [f.__dict__ for f in search.funnel], "eligible_count": len(search.eligible),
            "later_sales_excluded": search.later_sales_excluded, "limited": search.limited,
            "insufficient": search.insufficient, "limit_explanation": limit_explanation(search),
            "hints": hints,
        },
        "selection_mode": selection_mode,
        "selected_sale_ids": selected_ids,
        "comps": [serialize_comp(rc, rc.sale.sale_id in selected_ids, _comp_total_finished(req, rc.sale, rc.prop))
                  for rc in shown],
        "valuation": valuation.model_dump(),
        "adjustments": [a.model_dump() for a in req.adjustments],
        "appreciation_pct": req.appreciation_pct,
        "sale_history": [s.to_dict() for s in history],
        "latest_transfer": latest_any.to_dict() if latest_any else None,
        "last_market_sale": last_market.to_dict() if last_market else None,
        "change_since_last_sale": change,
        "condition_evidence": condition_gaps,
        "warnings": warnings,
        "sources": [s.to_dict() for s in subject.sources],
        "timing_ms": round((time.perf_counter() - t0) * 1000, 1),
    }


def condition_evidence_gaps(p: PropertyFacts) -> dict:
    """What the records do and do not establish about condition. Year built alone never implies a repair."""
    have = []
    if p.condition:
        have.append(f"Assessor condition rating: {p.condition} (a mass-appraisal rating, not an inspection)")
    if p.grade:
        have.append(f"Assessor construction grade: {p.grade}")
    if p.year_remodeled:
        have.append(f"County records a remodel in {p.year_remodeled}")
    if p.effective_year:
        have.append(f"Effective year built {p.effective_year}")
    need = [
        "Interior condition and finishes (kitchen, baths, flooring) — walkthrough or listing photos",
        "Age and condition of roof, HVAC, water heater and windows — seller disclosure or inspection",
        "Basement finish quality and any water intrusion — inspection",
        "Detached garage, ADU or other outbuildings — not in county dwelling data; confirm on site",
    ]
    return {"recorded": have, "needs_inspection": need,
            "note": "County records do not show repair needs. Year built by itself does not establish that any "
                    "repair is necessary."}
