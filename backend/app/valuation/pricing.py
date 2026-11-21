"""Price-per-square-foot valuation, reproducing the client's workbook method.

Workbook method (CMA Oronoco Master, rows 16-27):
  comp $/sf            = sold price / area                      (columns U and V)
  AVERAGE/MEDIAN/HIGH/LOW of comp $/sf                          (rows 16, 19, 21, 22)
  subject value        = subject finished sq ft x comp $/sf     (I, K, M, O)
  TOTAL                = mean value + garage/ADU adjustment     (U = Q + S)

The workbook keeps two area definitions apart and so does this module:
  - "above_grade":    county assessor above-grade living area (SFLA) for both
                      subject and comps (workbook column U, "based on Assessor SQFT")
  - "total_finished": total finished area including finished basement, from a
                      listing or agent input, for both subject and comps
                      (workbook column V, "based on Total Finished SQFT")
A calculation never mixes the two.

Appreciation is applied explicitly here (point x appreciation %). The workbook's
TOTAL formula omits its Appreciation column (R); with the workbook's 0% the
results are identical. See docs/WORKBOOK_ANALYSIS.md.
"""

from __future__ import annotations

import statistics
from typing import Literal

from pydantic import BaseModel, Field

from ..util.text import fmt_money

Basis = Literal["above_grade", "total_finished"]
Statistic = Literal["mean", "median"]

BASIS_LABELS = {
    "above_grade": "Price per above-grade sq ft (county assessor area)",
    "total_finished": "Price per total finished sq ft (includes finished basement)",
}


class Adjustment(BaseModel):
    label: str
    amount: float
    sf: float | None = None  # e.g. garage/ADU area (workbook column T); informational
    note: str | None = None
    source: str = "agent assumption"


class CompArea(BaseModel):
    sale_id: int | str
    label: str
    price: float
    sale_date: str
    above_grade_sf: float | None = None
    total_finished_sf: float | None = None
    total_finished_source: str | None = None
    record_id: str | None = None


class ValuationInput(BaseModel):
    subject_label: str
    subject_above_grade_sf: float | None = None
    subject_total_finished_sf: float | None = None
    subject_total_finished_source: str | None = None
    comps: list[CompArea]
    adjustments: list[Adjustment] = Field(default_factory=list)
    appreciation_pct: float = 0.0
    point_statistic: Statistic = "mean"
    primary_basis: Literal["auto", "above_grade", "total_finished"] = "auto"
    min_comps: int = 3


class CompRate(BaseModel):
    sale_id: int | str
    label: str
    price: float
    area: float
    ppsf: float
    sale_date: str
    record_id: str | None = None


class BasisResult(BaseModel):
    basis: Basis
    label: str
    available: bool
    reason_unavailable: str | None = None
    subject_area: float | None = None
    subject_area_source: str | None = None
    comps: list[CompRate] = Field(default_factory=list)
    comps_missing_area: list[str] = Field(default_factory=list)
    n: int = 0
    ppsf: dict[str, float] = Field(default_factory=dict)  # mean, median, high, low
    indicated: dict[str, float] = Field(default_factory=dict)  # subject_area x ppsf
    point_statistic: Statistic = "mean"
    base_value: float | None = None
    appreciation_amount: float = 0.0
    adjustments_total: float = 0.0
    estimate: float | None = None
    range_low: float | None = None
    range_high: float | None = None
    lines: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ValuationResult(BaseModel):
    bases: dict[str, BasisResult]
    primary_basis: Basis | None
    estimate: float | None
    range_low: float | None
    range_high: float | None
    adjustments: list[Adjustment]
    adjustments_total: float
    appreciation_pct: float
    point_statistic: Statistic
    warnings: list[str] = Field(default_factory=list)


def _basis(inp: ValuationInput, basis: Basis) -> BasisResult:
    if basis == "above_grade":
        subj_area, subj_src = inp.subject_above_grade_sf, "county assessor above-grade living area (SFLA)"
        get = lambda c: c.above_grade_sf  # noqa: E731
    else:
        subj_area = inp.subject_total_finished_sf
        subj_src = inp.subject_total_finished_source or "agent input"
        get = lambda c: c.total_finished_sf  # noqa: E731

    r = BasisResult(basis=basis, label=BASIS_LABELS[basis], available=False, subject_area=subj_area,
                    subject_area_source=subj_src, point_statistic=inp.point_statistic)
    for c in inp.comps:
        area = get(c)
        if area and area > 0 and c.price and c.price > 0:
            r.comps.append(CompRate(sale_id=c.sale_id, label=c.label, price=c.price, area=area,
                                    ppsf=c.price / area, sale_date=c.sale_date, record_id=c.record_id))
        else:
            r.comps_missing_area.append(c.label)
    r.n = len(r.comps)
    area_word = "above-grade" if basis == "above_grade" else "total finished"
    if not subj_area:
        r.reason_unavailable = f"Subject {area_word} sq ft is not available" + (
            " — enter it from the listing or a measurement." if basis == "total_finished" else ".")
        return r
    if r.n == 0:
        r.reason_unavailable = f"No selected comp has a {area_word} sq ft value" + (
            " — enter total finished sq ft for each comp." if basis == "total_finished" else ".")
        return r

    rates = [c.ppsf for c in r.comps]
    r.ppsf = {"mean": statistics.fmean(rates), "median": statistics.median(rates),
              "high": max(rates), "low": min(rates)}
    r.indicated = {k: subj_area * v for k, v in r.ppsf.items()}
    r.available = True
    r.base_value = r.indicated[inp.point_statistic]
    pct = inp.appreciation_pct / 100.0
    r.appreciation_amount = r.base_value * pct
    r.adjustments_total = sum(a.amount for a in inp.adjustments)
    r.estimate = r.base_value + r.appreciation_amount + r.adjustments_total
    r.range_low = r.indicated["low"] * (1 + pct) + r.adjustments_total
    r.range_high = r.indicated["high"] * (1 + pct) + r.adjustments_total

    stat_word = "average" if inp.point_statistic == "mean" else "median"
    r.lines.append(f"{r.n} comp{'s' if r.n != 1 else ''}: price ÷ {area_word} sq ft = "
                   + ", ".join(f"${c.ppsf:,.2f}" for c in r.comps))
    r.lines.append(f"Average ${r.ppsf['mean']:,.2f}/sf · median ${r.ppsf['median']:,.2f}/sf · "
                   f"high ${r.ppsf['high']:,.2f}/sf · low ${r.ppsf['low']:,.2f}/sf")
    r.lines.append(f"{subj_area:,.0f} sf × ${r.ppsf[inp.point_statistic]:,.2f}/sf ({stat_word}) = "
                   f"{fmt_money(r.base_value, cents=True)}")
    if inp.appreciation_pct:
        r.lines.append(f"Appreciation {inp.appreciation_pct:+g}% = {fmt_money(r.appreciation_amount, cents=True)}")
    for a in inp.adjustments:
        r.lines.append(f"{a.label}: {'+' if a.amount >= 0 else '-'}{fmt_money(abs(a.amount), cents=True)}"
                       f" ({a.source})")
    r.lines.append(f"Estimate = {fmt_money(r.estimate, cents=True)}")
    r.lines.append(f"Range (low–high comp $/sf, same adjustments) = {fmt_money(r.range_low)} – "
                   f"{fmt_money(r.range_high)}")
    if r.n < inp.min_comps:
        r.warnings.append(f"Only {r.n} comp(s) with {area_word} area; at least {inp.min_comps} are recommended.")
    if r.comps_missing_area:
        r.warnings.append(f"Left out of this method for missing {area_word} sq ft: " + ", ".join(r.comps_missing_area))
    return r


def compute_valuation(inp: ValuationInput) -> ValuationResult:
    bases = {b: _basis(inp, b) for b in ("above_grade", "total_finished")}
    if inp.primary_basis == "auto":
        tf = bases["total_finished"]
        # The workbook's headline uses total finished area; use it when it is complete enough.
        primary: Basis | None = "total_finished" if tf.available and tf.n >= min(inp.min_comps, len(inp.comps)) \
            else ("above_grade" if bases["above_grade"].available else None)
    else:
        primary = inp.primary_basis if bases[inp.primary_basis].available else None
    p = bases[primary] if primary else None
    warnings = []
    if primary is None:
        warnings.append("No valuation method has enough data. Select comps and confirm the subject's area.")
    if len(inp.comps) < inp.min_comps:
        warnings.append(f"Only {len(inp.comps)} comp(s) selected; at least {inp.min_comps} are recommended.")
    return ValuationResult(
        bases=bases, primary_basis=primary, estimate=p.estimate if p else None,
        range_low=p.range_low if p else None, range_high=p.range_high if p else None,
        adjustments=inp.adjustments, adjustments_total=sum(a.amount for a in inp.adjustments),
        appreciation_pct=inp.appreciation_pct, point_statistic=inp.point_statistic, warnings=warnings,
    )


def change_since_last_sale(estimate: float | None, last_price: float | None, last_date: str | None) -> dict | None:
    """Labelled exactly as 'Estimated change since the last sale' wherever it is shown."""
    if estimate is None or not last_price:
        return None
    diff = estimate - last_price
    return {"label": "Estimated change since the last sale", "amount": diff, "pct": diff / last_price * 100,
            "last_sale_price": last_price, "last_sale_date": last_date}
