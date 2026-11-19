"""Comparable-sale eligibility and ranking.

The engine is a pure function of (subject, candidate sales, valuation date,
criteria) so it can be unit-tested without a database.

Principles
- Only sales recorded on or before the valuation date are eligible.
- Ranking never looks at the sale price. Comps are chosen by how similar the
  property and the sale are to the subject, so a price cannot be cherry-picked
  to support a desired estimate.
- Every rule is explainable: the funnel says how many sales each eligibility
  rule removed, and every comp carries per-factor scores and a plain-language
  reason.
- Missing data is never silently filled in. A factor that cannot be compared
  is dropped from that comp's score and listed as missing.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from ..domain import PropertyFacts, SaleFacts
from ..util.dates import months_between, subtract_months
from ..util.geo import haversine_miles
from ..util.text import PROPERTY_TYPE_LABELS

DEFAULT_VALIDITY = ["Valid and verified sale"]
# Validity codes the user may opt into. Everything else in the county list
# (no consideration, related parties, foreclosure, etc.) is never market value.
OPTIONAL_VALIDITY = ["Pending verification", "Sale from lender - valid sale price",
                     "Valid and verified multi-parcel sale"]


class CompWeights(BaseModel):
    distance: float = 20
    recency: float = 15
    living_area: float = 20
    beds: float = 6
    baths: float = 7
    lot_size: float = 7
    age: float = 8
    style: float = 5
    condition: float = 7
    features: float = 5


class CompCriteria(BaseModel):
    max_distance_miles: float = Field(1.0, gt=0, le=10)
    lookback_months: int = Field(12, ge=1, le=60)
    max_results: int = Field(5, ge=1, le=25)
    min_comps: int = Field(3, ge=1, le=10)
    allowed_validity: list[str] = Field(default_factory=lambda: list(DEFAULT_VALIDITY))
    min_price: int = 10_000
    same_property_type: bool = True
    exclude_multi_parcel: bool = True
    living_area_tolerance_pct: float | None = Field(35, ge=5, le=200)
    weights: CompWeights = Field(default_factory=CompWeights)


FACTOR_LABELS = {
    "distance": "Distance", "recency": "Sale recency", "living_area": "Above-grade living area",
    "beds": "Bedrooms", "baths": "Bathrooms", "lot_size": "Lot size", "age": "Year built",
    "style": "Style", "condition": "Assessor condition & grade", "features": "Basement / fireplace / garage",
}


@dataclass
class Factor:
    key: str
    label: str
    weight: float
    score: float | None  # 0..1, None when it could not be compared
    subject_value: str | None
    comp_value: str | None
    detail: str

    def to_dict(self) -> dict:
        return {"key": self.key, "label": self.label, "weight": self.weight,
                "score": None if self.score is None else round(self.score, 3),
                "subject_value": self.subject_value, "comp_value": self.comp_value, "detail": self.detail}


@dataclass
class RankedComp:
    sale: SaleFacts
    prop: PropertyFacts
    distance_miles: float | None
    months_before: float
    score: float
    factors: list[Factor]
    rank: int = 0
    reason: str = ""
    strengths: list[str] = field(default_factory=list)
    differences: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class FunnelStep:
    key: str
    label: str
    removed: int
    remaining: int
    detail: str | None = None


@dataclass
class CompSearch:
    subject: PropertyFacts
    valuation_date: dt.date
    criteria: CompCriteria
    window_start: dt.date
    pool_count: int
    funnel: list[FunnelStep]
    eligible: list[RankedComp]
    later_sales_excluded: int
    hints: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def top(self) -> list[RankedComp]:
        return self.eligible[: self.criteria.max_results]

    @property
    def limited(self) -> bool:
        return len(self.eligible) < self.criteria.max_results

    @property
    def insufficient(self) -> bool:
        return len(self.eligible) < self.criteria.min_comps


# ----------------------------------------------------------------- helpers
def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


_CDU = {"poor": 0.0, "fair": 1.0, "average": 2.0, "average plus": 2.5, "good": 3.0,
        "very good": 4.0, "excellent": 5.0}
_GRADE = {"low": 0.0, "fair": 1.0, "average": 2.0, "good": 3.0, "excellent": 4.0, "luxury": 5.0}


def condition_rank(cdu: str | None) -> float | None:
    if not cdu:
        return None
    return _CDU.get(cdu.strip().lower())


def grade_rank(grade: str | None) -> float | None:
    """County grades look like "Good", "Good 10", "Excellent 30"; the suffix steps within a grade."""
    if not grade:
        return None
    parts = grade.strip().lower().rsplit(" ", 1)
    base, step = (parts[0], parts[1]) if len(parts) == 2 and parts[1].isdigit() else (grade.strip().lower(), "0")
    if base not in _GRADE:
        return None
    return _GRADE[base] + int(step) / 30.0


def _style_family(style: str | None) -> str | None:
    if not style:
        return None
    s = style.lower()
    if "split" in s or "bi-level" in s:
        return "split"
    if s.startswith("1 1/2"):
        return "1.5"
    if s.startswith("1 story"):
        return "1"
    if s.startswith("2 1/2") or s.startswith("3"):
        return "2.5+"
    if s.startswith("2"):
        return "2"
    return s


def _pct(a: float, b: float) -> float:
    return (a - b) / b


def _fmt_pct(p: float) -> str:
    return f"{p * 100:+.0f}%"


# ---------------------------------------------------------------- scoring
def score_factors(subject: PropertyFacts, comp: PropertyFacts, sale: SaleFacts, valuation_date: dt.date,
                  distance: float | None, c: CompCriteria, area_attr: str = "above_grade_sf") -> list[Factor]:
    w = c.weights
    out: list[Factor] = []

    # distance
    if distance is None:
        out.append(Factor("distance", FACTOR_LABELS["distance"], w.distance, None, None, None,
                          "Location not mapped"))
    else:
        out.append(Factor("distance", FACTOR_LABELS["distance"], w.distance,
                          _clamp(1 - distance / c.max_distance_miles), None, f"{distance:.2f} mi",
                          f"{distance:.2f} mi away"))

    # recency
    months = months_between(sale.sale_date, valuation_date)
    out.append(Factor("recency", FACTOR_LABELS["recency"], w.recency, _clamp(1 - months / c.lookback_months),
                      valuation_date.isoformat(), sale.sale_date.isoformat(),
                      f"sold {months:.1f} months before the valuation date"))

    # living area
    sa, ca = getattr(subject, area_attr), getattr(comp, area_attr)
    area_name = "above-grade" if area_attr == "above_grade_sf" else "total finished"
    if sa and ca:
        p = _pct(ca, sa)
        tol = (c.living_area_tolerance_pct or 50) / 100
        out.append(Factor("living_area", FACTOR_LABELS["living_area"] if area_attr == "above_grade_sf"
                          else "Total finished living area", w.living_area, _clamp(1 - abs(p) / tol),
                          f"{sa:,} sf", f"{ca:,} sf", f"{ca:,} vs {sa:,} sf ({_fmt_pct(p)})"))
    else:
        out.append(Factor("living_area", FACTOR_LABELS["living_area"], w.living_area, None,
                          f"{sa:,} sf" if sa else None, f"{ca:,} sf" if ca else None,
                          f"{area_name} living area not recorded"))

    # beds
    if subject.beds is not None and comp.beds is not None and (subject.beds or comp.beds):
        d = comp.beds - subject.beds
        out.append(Factor("beds", FACTOR_LABELS["beds"], w.beds, _clamp(1 - abs(d) / 3), str(subject.beds),
                          str(comp.beds), (f"same ({comp.beds})" if d == 0 else f"{comp.beds} vs {subject.beds} ({d:+d})")))
    else:
        out.append(Factor("beds", FACTOR_LABELS["beds"], w.beds, None, None, None, "bedroom count not recorded"))

    # baths
    if subject.baths and comp.baths:
        d = comp.baths - subject.baths
        out.append(Factor("baths", FACTOR_LABELS["baths"], w.baths, _clamp(1 - abs(d) / 2.5),
                          subject.baths_label, comp.baths_label,
                          (f"same ({comp.baths_label} full/half)" if d == 0
                           else f"{comp.baths_label} vs {subject.baths_label} full/half ({d:+g})")))
    else:
        out.append(Factor("baths", FACTOR_LABELS["baths"], w.baths, None, None, None, "bath count not recorded"))

    # lot size (not meaningful for condominiums)
    if subject.property_type == "CONDO" or comp.property_type == "CONDO":
        out.append(Factor("lot_size", FACTOR_LABELS["lot_size"], w.lot_size, None, None, None,
                          "lot size not compared for condominiums"))
    elif subject.lot_sf and comp.lot_sf:
        p = _pct(comp.lot_sf, subject.lot_sf)
        out.append(Factor("lot_size", FACTOR_LABELS["lot_size"], w.lot_size, _clamp(1 - abs(p) / 1.0),
                          f"{subject.lot_sf:,} sf", f"{comp.lot_sf:,} sf",
                          f"{comp.lot_sf:,} vs {subject.lot_sf:,} sf ({_fmt_pct(p)})"))
    else:
        out.append(Factor("lot_size", FACTOR_LABELS["lot_size"], w.lot_size, None, None, None,
                          "lot size not recorded"))

    # year built
    if subject.year_built and comp.year_built:
        d = comp.year_built - subject.year_built
        out.append(Factor("age", FACTOR_LABELS["age"], w.age, _clamp(1 - abs(d) / 40), str(subject.year_built),
                          str(comp.year_built), (f"same ({comp.year_built})" if d == 0
                           else f"{comp.year_built} vs {subject.year_built} ({d:+d} yrs)")))
    else:
        out.append(Factor("age", FACTOR_LABELS["age"], w.age, None, None, None, "year built not recorded"))

    # style
    sf, cf = _style_family(subject.style), _style_family(comp.style)
    if sf and cf:
        s = 1.0 if subject.style == comp.style else (0.75 if sf == cf else 0.3)
        out.append(Factor("style", FACTOR_LABELS["style"], w.style, s, subject.style, comp.style,
                          f"same ({comp.style})" if comp.style == subject.style else f"{comp.style} vs {subject.style}"))
    else:
        out.append(Factor("style", FACTOR_LABELS["style"], w.style, None, subject.style, comp.style,
                          "style not recorded"))

    # assessor condition (CDU) and construction grade
    parts, details = [], []
    sc, cc = condition_rank(subject.condition), condition_rank(comp.condition)
    if sc is not None and cc is not None:
        parts.append(_clamp(1 - abs(cc - sc) / 2))
        details.append(f"condition {comp.condition} vs {subject.condition}")
    sg, cg = grade_rank(subject.grade), grade_rank(comp.grade)
    if sg is not None and cg is not None:
        parts.append(_clamp(1 - abs(cg - sg) / 2))
        details.append(f"grade {comp.grade} vs {subject.grade}")
    out.append(Factor("condition", FACTOR_LABELS["condition"], w.condition,
                      sum(parts) / len(parts) if parts else None,
                      f"{subject.condition or '—'} / {subject.grade or '—'}",
                      f"{comp.condition or '—'} / {comp.grade or '—'}",
                      "; ".join(details) if details else "assessor condition/grade not recorded"))

    # features: basement, fireplace, garage (garage only when both are recorded)
    parts, details = [], []
    if subject.has_basement is not None and comp.has_basement is not None:
        parts.append(1.0 if subject.has_basement == comp.has_basement else 0.0)
        details.append(f"basement {comp.basement} vs {subject.basement}")
    if subject.fireplaces is not None and comp.fireplaces is not None:
        parts.append(1.0 if (subject.fireplaces > 0) == (comp.fireplaces > 0) else 0.5)
        details.append(f"{comp.fireplaces} vs {subject.fireplaces} fireplaces")
    if subject.garage is not None and comp.garage is not None:
        parts.append(1.0)
        details.append("both have a recorded garage")
    elif subject.garage is not None or comp.garage is not None:
        details.append("garage recorded for only one (detached garages are not in county data)")
    out.append(Factor("features", FACTOR_LABELS["features"], w.features,
                      sum(parts) / len(parts) if parts else None, None, None,
                      "; ".join(details) if details else "features not recorded"))
    return out


def combine(factors: list[Factor]) -> float:
    used = [f for f in factors if f.score is not None and f.weight > 0]
    total_w = sum(f.weight for f in used)
    if total_w == 0:
        return 0.0
    return 100.0 * sum(f.weight * f.score for f in used) / total_w


def explain(rc: RankedComp) -> None:
    used = [f for f in rc.factors if f.score is not None and f.weight > 0]
    rc.missing = [f.label for f in rc.factors if f.score is None and f.weight > 0]
    strong = sorted([f for f in used if f.score >= 0.75], key=lambda f: -f.weight * f.score)
    weak = sorted([f for f in used if f.score < 0.6], key=lambda f: -f.weight * (1 - f.score))
    rc.strengths = [f"{f.label}: {f.detail}" for f in strong[:3]]
    rc.differences = [f"{f.label}: {f.detail}" for f in weak[:2]]
    parts = []
    if rc.strengths:
        parts.append("Strong match on " + "; ".join(rc.strengths[:2]))
    if rc.differences:
        parts.append("Main difference: " + rc.differences[0])
    if rc.missing:
        parts.append("Not compared (no data): " + ", ".join(m.lower() for m in rc.missing))
    rc.reason = ". ".join(parts) + "." if parts else "Limited data available for comparison."


# ---------------------------------------------------------------- pipeline
def find_comps(subject: PropertyFacts, candidates: list[tuple[SaleFacts, PropertyFacts]],
               valuation_date: dt.date, criteria: CompCriteria) -> CompSearch:
    c = criteria
    window_start = subtract_months(valuation_date, c.lookback_months)
    allowed = {v.lower() for v in c.allowed_validity}

    # Window: recorded from window_start onward, within the search radius.
    pool: list[tuple[SaleFacts, PropertyFacts, float | None]] = []
    no_location = 0
    for sale, prop in candidates:
        if sale.sale_date < window_start:
            continue
        if subject.lat is None or prop.lat is None:
            no_location += 1
            continue
        d = haversine_miles(subject.lat, subject.lon, prop.lat, prop.lon)
        if d <= c.max_distance_miles:
            pool.append((sale, prop, d))
    pool_count = len(pool)
    funnel: list[FunnelStep] = []

    def step(key: str, label: str, keep, detail_fn=None) -> None:
        nonlocal pool
        flags = [bool(keep(x)) for x in pool]  # evaluate once: some rules are stateful
        removed = [x for x, ok in zip(pool, flags) if not ok]
        pool = [x for x, ok in zip(pool, flags) if ok]
        detail = detail_fn(removed) if detail_fn and removed else None
        funnel.append(FunnelStep(key, label, len(removed), len(pool), detail))

    def top_codes(removed) -> str:
        cnt = Counter((x[0].validity or "No validity code") for x in removed)
        return "; ".join(f"{k} ({v})" for k, v in cnt.most_common(4))

    step("after_valuation_date", f"Recorded after the valuation date ({valuation_date.isoformat()})",
         lambda x: x[0].sale_date <= valuation_date)
    later = funnel[-1].removed
    step("subject_parcel", "Sale of the subject property itself", lambda x: x[0].pin != subject.pin)
    step("validity", "Not marked as a valid sale by the county", lambda x: (x[0].validity or "").lower() in allowed,
         top_codes)
    step("price", f"No price or price below ${c.min_price:,}", lambda x: (x[0].price or 0) >= c.min_price)
    if c.exclude_multi_parcel:
        step("multi_parcel", "Deed conveyed more than one parcel (price covers several parcels)",
             lambda x: not x[0].multi_parcel)
    if c.same_property_type:
        st = PROPERTY_TYPE_LABELS.get(subject.property_type, subject.property_type)
        step("property_type", f"Different property type (subject: {st})",
             lambda x: x[1].property_type == subject.property_type,
             lambda r: "; ".join(f"{PROPERTY_TYPE_LABELS.get(k, k)} ({v})"
                                 for k, v in Counter(x[1].property_type for x in r).most_common(3)))
    step("living_area_missing", "No above-grade living area on record", lambda x: bool(x[1].above_grade_sf))
    if c.living_area_tolerance_pct and subject.above_grade_sf:
        tol = c.living_area_tolerance_pct / 100
        step("living_area_range", f"Above-grade living area differs by more than {c.living_area_tolerance_pct:g}%",
             lambda x: abs(_pct(x[1].above_grade_sf, subject.above_grade_sf)) <= tol)
    step("built_after_sale", "House on record was built after the sale (price reflects land, not this house)",
         lambda x: not (x[1].year_built and x[1].year_built > x[0].sale_date.year))
    # one sale per parcel: keep the most recent eligible transfer
    latest: dict[str, dt.date] = {}
    for s, _, _ in pool:
        if s.pin not in latest or s.sale_date > latest[s.pin]:
            latest[s.pin] = s.sale_date
    seen: set[str] = set()

    def keep_latest(x) -> bool:
        s = x[0]
        if s.sale_date != latest[s.pin] or s.pin in seen:
            return False
        seen.add(s.pin)
        return True

    pool.sort(key=lambda x: (-x[0].sale_date.toordinal(), x[0].sale_id))
    step("superseded", "Earlier sale of a parcel that sold again in the window", keep_latest)

    ranked: list[RankedComp] = []
    for sale, prop, d in pool:
        factors = score_factors(subject, prop, sale, valuation_date, d, c)
        rc = RankedComp(sale=sale, prop=prop, distance_miles=d,
                        months_before=months_between(sale.sale_date, valuation_date),
                        score=combine(factors), factors=factors)
        if prop.year_remodeled and prop.year_remodeled > sale.sale_date.year:
            rc.warnings.append(f"County shows a {prop.year_remodeled} remodel after this sale; "
                               "today's record may not match the house as sold.")
        if not sale.in_latest_source:
            rc.warnings.append("This sale no longer appears in the latest county extract (kept from history).")
        explain(rc)
        ranked.append(rc)
    # Ranking is price-blind: score, then distance, then recency, then id for stability.
    ranked.sort(key=lambda r: (-round(r.score, 6), r.distance_miles or 99, -r.sale.sale_date.toordinal(),
                               r.sale.sale_id))
    for i, rc in enumerate(ranked, 1):
        rc.rank = i

    result = CompSearch(subject=subject, valuation_date=valuation_date, criteria=c, window_start=window_start,
                        pool_count=pool_count, funnel=funnel, eligible=ranked, later_sales_excluded=later)
    if no_location:
        result.warnings.append(f"{no_location} transfer(s) on parcels without a mapped address point were not "
                               "considered.")
    if subject.lat is None:
        result.warnings.append("The subject has no mapped address point, so distance cannot be measured.")
    if not subject.above_grade_sf:
        result.warnings.append("The subject has no above-grade living area on record; living-area matching "
                               "and the above-grade $/sq ft method are unavailable.")
    return result


def limit_explanation(search: CompSearch) -> str | None:
    """Plain-language explanation when fewer than `max_results` comps qualify."""
    if not search.limited:
        return None
    n, c = len(search.eligible), search.criteria
    biggest = sorted([f for f in search.funnel if f.removed], key=lambda f: -f.removed)[:3]
    filt = "; ".join(f"{f.label.lower()} removed {f.removed}" for f in biggest)
    msg = (f"Only {n} sale{'s' if n != 1 else ''} met every rule (target {c.max_results}). "
           f"The search started with {search.pool_count} recorded transfers within {c.max_distance_miles:g} mi "
           f"from {search.window_start.isoformat()} onward")
    msg += f"; {filt}." if filt else "."
    if search.insufficient:
        msg += f" That is below the minimum of {c.min_comps} comps, so treat any estimate as provisional."
    return msg


def relaxation_hints(subject: PropertyFacts, candidates, valuation_date: dt.date, criteria: CompCriteria) -> list[dict]:
    """How many sales would qualify if one rule were widened. Never changes the selection."""
    base = len(find_comps(subject, candidates, valuation_date, criteria).eligible)
    trials = []
    for label, patch in [
        (f"Widen radius to {criteria.max_distance_miles * 1.5:g} mi", {"max_distance_miles": criteria.max_distance_miles * 1.5}),
        (f"Widen radius to {criteria.max_distance_miles * 2:g} mi", {"max_distance_miles": criteria.max_distance_miles * 2}),
        (f"Extend look-back to {criteria.lookback_months * 2} months", {"lookback_months": criteria.lookback_months * 2}),
        ("Allow any living-area difference", {"living_area_tolerance_pct": None}),
        ("Include 'Pending verification' sales",
         {"allowed_validity": sorted(set(criteria.allowed_validity) | {"Pending verification"})}),
    ]:
        crit = criteria.model_copy(update=patch)
        n = len(find_comps(subject, candidates, valuation_date, crit).eligible)
        if n > base:
            trials.append({"change": label, "eligible": n, "added": n - base, "patch": patch})
    return trials
