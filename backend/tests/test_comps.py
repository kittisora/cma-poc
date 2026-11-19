"""Comp eligibility, ranking and explanations."""

import datetime as dt
from dataclasses import replace

from app import repository as repo
from app.comps.engine import CompCriteria, find_comps, limit_explanation, relaxation_hints
from app.util.dates import subtract_months

from .conftest import SUBJECT_PIN, VALUATION_DATE


def _run(session, vdate=VALUATION_DATE, **crit):
    c = CompCriteria(**crit)
    subj = repo.get_property(session, SUBJECT_PIN)
    cands = repo.get_candidate_sales(session, subj.lat, subj.lon, c.max_distance_miles * 2,
                                     subtract_months(vdate, c.lookback_months * 2))
    return subj, cands, find_comps(subj, cands, vdate, c)


def _funnel(search):
    return {f.key: f.removed for f in search.funnel}


def test_normal_path_ranks_five_and_explains_filters(loaded):
    subj, _, s = _run(loaded)
    assert [rc.prop.pin for rc in s.top] == ["1000 01  0002", "1000 01  0003", "1000 01  0004",
                                             "1000 01  0006", "1000 01  0005"]
    f = _funnel(s)
    assert f["after_valuation_date"] == 1          # 1000 01 0008 sold 2026-12-15
    assert f["validity"] == 1                      # "No consideration"
    assert f["multi_parcel"] == 2                  # deed 31111/0001 covers two parcels
    assert f["property_type"] == 1                 # townhouse
    assert all(rc.distance_miles <= 1.0 for rc in s.eligible)
    top = s.top[0]
    assert top.rank == 1 and top.reason.startswith("Strong match on")
    assert {fa.key for fa in top.factors} >= {"distance", "recency", "living_area", "beds", "baths", "lot_size",
                                               "age", "style", "condition", "features"}


def test_historical_valuation_excludes_later_sales(loaded):
    # On 2026-07-01, the 2026-08-01 and 2026-09-01 sales had not happened yet.
    _, _, s = _run(loaded, vdate=dt.date(2026, 7, 1))
    dates = [rc.sale.sale_date for rc in s.eligible]
    assert dates and max(dates) <= dt.date(2026, 7, 1)
    assert "1000 01  0002" not in {rc.prop.pin for rc in s.eligible}
    assert _funnel(s)["after_valuation_date"] >= 2


def test_ranking_ignores_price(loaded):
    subj, cands, s1 = _run(loaded)
    # multiply every price by a different factor: rank order must not change
    shuffled = [(replace(sale, price=(sale.price or 0) * (7 - i % 5)), prop) for i, (sale, prop) in enumerate(cands)]
    s2 = find_comps(subj, shuffled, VALUATION_DATE, CompCriteria())
    assert [rc.sale.sale_id for rc in s1.eligible] == [rc.sale.sale_id for rc in s2.eligible]
    assert [round(rc.score, 6) for rc in s1.eligible] == [round(rc.score, 6) for rc in s2.eligible]


def test_missing_field_is_dropped_and_reported(loaded):
    subj, cands, _ = _run(loaded)
    cands = [(sale, replace(prop, beds=None)) if prop.pin == "1000 01  0002" else (sale, prop) for sale, prop in cands]
    s = find_comps(subj, cands, VALUATION_DATE, CompCriteria())
    rc = next(r for r in s.eligible if r.prop.pin == "1000 01  0002")
    beds = next(f for f in rc.factors if f.key == "beds")
    assert beds.score is None and "Bedrooms" in rc.missing
    assert "not compared" in rc.reason.lower()
    assert 0 < rc.score <= 100


def test_subject_missing_living_area_warns(loaded):
    subj, cands, _ = _run(loaded)
    s = find_comps(replace(subj, above_grade_sf=None), cands, VALUATION_DATE, CompCriteria())
    assert any("no above-grade living area" in w for w in s.warnings)


def test_insufficient_comps_shows_what_qualifies_and_why(loaded):
    # A 0.35 mi radius leaves three eligible sales.
    subj, cands, s = _run(loaded, max_distance_miles=0.35)
    assert len(s.eligible) == 3
    assert s.limited and not s.insufficient
    msg = limit_explanation(s)
    assert msg.startswith("Only 3 sales met every rule (target 5)")
    hints = relaxation_hints(subj, cands, VALUATION_DATE, CompCriteria(max_distance_miles=0.35))
    assert any(h["change"].startswith("Widen radius") and h["added"] >= 1 for h in hints)
    # Two eligible is below the minimum of three.
    _, _, s2 = _run(loaded, max_distance_miles=0.25)
    assert len(s2.eligible) == 2 and s2.insufficient
    assert "below the minimum" in limit_explanation(s2)


def test_subject_own_sale_never_a_comp(loaded):
    _, _, s = _run(loaded, vdate=dt.date(2023, 1, 1), lookback_months=60)
    assert SUBJECT_PIN not in {rc.prop.pin for rc in s.eligible}
    assert _funnel(s)["subject_parcel"] == 1
