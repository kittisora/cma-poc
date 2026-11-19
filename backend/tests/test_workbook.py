"""Regression check against the client's workbook ("1009 New" ≈ $3,190,927)."""

from pathlib import Path

import pytest

from app.valuation.workbook import COMPS, SUBJECTS, WORKBOOK_FILE, regression_report, reproduce_workbook

WORKBOOK = Path(__file__).resolve().parents[2] / WORKBOOK_FILE


def test_1009_new_reproduces_workbook_total():
    r = regression_report("1009 New")
    assert r["regression"]["passed"] is True
    assert r["variants"][0]["estimate"] == pytest.approx(3190926.666666667, abs=0.01)
    assert round(r["variants"][0]["estimate"]) == 3190927


@pytest.mark.parametrize("subject", list(SUBJECTS))
def test_all_workbook_subjects_reproduce(subject):
    a = reproduce_workbook(subject)
    assert a["estimate"] == pytest.approx(SUBJECTS[subject]["expected_total"], abs=0.01)


def test_recomputed_and_app_selected_variants():
    r = regression_report("1009 New")
    a, b, c = r["variants"]
    # B: same 6 comps, $/sf = sold / listing total sq ft
    assert b["n"] == 6 and b["estimate"] == pytest.approx(2992235.73, abs=0.01)
    # C: app rules drop 109 S Lee St (2,084 sf is -38% vs 3,335 sf) and keep 5
    assert c["n"] == 5 and c["estimate"] == pytest.approx(2809550.44, abs=0.01)
    assert any(x["address"] == "109 S Lee St" and "tolerance" in x["reason"] for x in c["excluded"])
    assert sum(1 for x in c["excluded"] if "Active listing" in x["reason"]) == 7
    assert r["live_comparison"]["available"] is False


def test_explicit_original_inputs_still_compare_to_workbook():
    r = regression_report("1009 New", finished_sf=3335, garage_adjustment=225000)
    assert r["regression"]["passed"] is True


def test_garage_adjustment_is_editable():
    r = regression_report("1009 New", garage_adjustment=150000)
    assert r["variants"][0]["estimate"] == pytest.approx(3190926.666666667 - 75000, abs=0.01)
    assert r["regression"]["expected"] is None  # not the workbook's inputs any more


def test_flags_cover_known_workbook_issues():
    cells = " ".join(f["cells"] for f in regression_report()["flags"])
    for needle in ("U4", "V5", "E16", "E18", "R25", "S25", "AA17", "B2"):
        assert needle in cells


@pytest.mark.skipif(not WORKBOOK.exists(), reason="workbook not present")
def test_transcription_matches_xlsx():
    openpyxl = pytest.importorskip("openpyxl")
    ws = openpyxl.load_workbook(WORKBOOK, data_only=True).active
    for c in COMPS:
        row = c["row"]
        assert ws[f"C{row}"].value == c["address"]
        assert ws[f"L{row}"].value == c["total_sf"]
        assert ws[f"M{row}"].value == c["assessor_sf"]
        assert ws[f"S{row}"].value == c["sold_price"]
        assert ws[f"U{row}"].value == c["U"]
        assert ws[f"V{row}"].value == c["V"]
    assert ws["G27"].value == 3335 and ws["S27"].value == 225000
    assert ws["U27"].value == pytest.approx(3190926.666666667)
