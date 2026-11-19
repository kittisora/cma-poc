import pytest

from app.valuation.pricing import Adjustment, CompArea, ValuationInput, change_since_last_sale, compute_valuation


def _comps(total=True):
    return [
        CompArea(sale_id=1, label="A", price=1_000_000, sale_date="2026-01-01", above_grade_sf=2000,
                 total_finished_sf=2500 if total else None),
        CompArea(sale_id=2, label="B", price=900_000, sale_date="2026-02-01", above_grade_sf=1800,
                 total_finished_sf=2400 if total else None),
        CompArea(sale_id=3, label="C", price=1_200_000, sale_date="2026-03-01", above_grade_sf=2000,
                 total_finished_sf=3000 if total else None),
    ]


def test_bases_use_matching_area_definitions():
    v = compute_valuation(ValuationInput(subject_label="S", subject_above_grade_sf=2000,
                                         subject_total_finished_sf=2600, comps=_comps()))
    ag, tf = v.bases["above_grade"], v.bases["total_finished"]
    assert [c.ppsf for c in ag.comps] == [500, 500, 600]          # price / above-grade
    assert [c.ppsf for c in tf.comps] == [400, 375, 400]          # price / total finished
    assert ag.estimate == pytest.approx(2000 * (1600 / 3))
    assert tf.estimate == pytest.approx(2600 * (1175 / 3))
    assert tf.ppsf["median"] == 400 and tf.ppsf["high"] == 400 and tf.ppsf["low"] == 375
    assert v.primary_basis == "total_finished" and v.estimate == tf.estimate


def test_total_finished_unavailable_falls_back_to_above_grade():
    v = compute_valuation(ValuationInput(subject_label="S", subject_above_grade_sf=2000, comps=_comps(total=False)))
    assert not v.bases["total_finished"].available
    assert "Subject total finished" in v.bases["total_finished"].reason_unavailable
    assert v.primary_basis == "above_grade"


def test_adjustments_and_appreciation_are_explicit():
    v = compute_valuation(ValuationInput(
        subject_label="S", subject_above_grade_sf=2000, comps=_comps(total=False), appreciation_pct=3,
        adjustments=[Adjustment(label="Garage/ADU", amount=225000)], point_statistic="median"))
    ag = v.bases["above_grade"]
    base = 2000 * 500
    assert ag.base_value == base
    assert ag.estimate == pytest.approx(base * 1.03 + 225000)
    assert ag.range_low == pytest.approx(2000 * 500 * 1.03 + 225000)
    assert ag.range_high == pytest.approx(2000 * 600 * 1.03 + 225000)
    assert any("Garage/ADU" in line for line in ag.lines)


def test_too_few_comps_warns():
    v = compute_valuation(ValuationInput(subject_label="S", subject_above_grade_sf=2000, comps=_comps()[:2]))
    assert any("at least 3" in w for w in v.warnings)


def test_change_since_last_sale_label():
    ch = change_since_last_sale(1_100_000, 1_000_000, "2020-01-01")
    assert ch["label"] == "Estimated change since the last sale"
    assert ch["amount"] == 100_000 and ch["pct"] == pytest.approx(10)
    assert change_since_last_sale(None, 1, "x") is None
