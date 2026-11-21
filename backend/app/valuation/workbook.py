"""Regression check against the client's workbook "CMA Oronoco Master Updated 11-4-26.xlsx".

The comp rows below are transcribed from Sheet1 rows 2-14 exactly as entered
(tests/test_workbook.py re-reads the .xlsx, when present, to confirm the
transcription). All 13 comps and both subjects are in the City of Alexandria
(ZIP 22314), not Fairfax County, so the workbook is used only as a reference
for the method, never as market data for 22308/22309.
"""

from __future__ import annotations

import datetime as dt
import statistics

from ..comps.engine import CompCriteria, combine, explain, RankedComp, score_factors
from ..domain import PropertyFacts, SaleFacts
from ..util.dates import months_between
from .pricing import Adjustment, CompArea, ValuationInput, compute_valuation

WORKBOOK_FILE = "CMA Oronoco Master Updated 11-4-26.xlsx"
WORKBOOK_DATE = dt.date(2026, 11, 4)  # "Updated 11-4-26" in the file name

# Sheet1 rows 2-14. Keys follow the workbook headers. U and V are the typed-in
# $/sf values (they are not formulas in the workbook).
COMPS: list[dict] = [
    {"row": 2, "comp": 1, "address": "533 N Columbus St", "lot_sf": 1756, "year": 2017, "style": "Traditional", "beds": 4, "baths": "4/1", "fireplaces": 2, "basement": "Yes", "total_sf": 2696, "assessor_sf": 1932, "garage": "2 off-street", "condition": "Excellent", "list_price": 2150000, "sold_price": None, "sold_date": None, "U": None, "V": None, "terms": None, "dom": 42},
    {"row": 3, "comp": 2, "address": "112 Quay St", "lot_sf": 2118, "year": 1971, "style": "Colonial", "beds": 4, "baths": "3/1", "fireplaces": 2, "basement": "YES", "total_sf": 3100, "assessor_sf": 3100, "garage": "1-car attached", "condition": "Excellent", "list_price": 2875000, "sold_price": None, "sold_date": None, "U": None, "V": None, "terms": None, "dom": 51},
    {"row": 4, "comp": 3, "address": "207 S Alfred St", "lot_sf": 2008, "year": 1890, "style": "Traditional", "beds": 3, "baths": "3/1", "fireplaces": 1, "basement": "Yes", "total_sf": 2704, "assessor_sf": 2372, "garage": "2 off-street", "condition": "Excellent", "list_price": 2295000, "sold_price": 2295000, "sold_date": "2026-04-02", "U": 955, "V": 849, "terms": "Conventional", "dom": 8},
    {"row": 5, "comp": 5, "address": "714 Wythe St", "lot_sf": 2466, "year": 2009, "style": "Colonial", "beds": 5, "baths": "4/1", "fireplaces": 2, "basement": "YES", "total_sf": 3952, "assessor_sf": 2964, "garage": "2 off-street", "condition": "Excellent", "list_price": 2250000, "sold_price": 2100000, "sold_date": "2026-10-19", "U": 708.5, "V": 683, "terms": "Conventional", "dom": 152},
    {"row": 6, "comp": 6, "address": "808 Oronoco St", "lot_sf": 2070, "year": 1994, "style": "Colonial", "beds": 4, "baths": "3/1", "fireplaces": 1, "basement": "YES", "total_sf": 2420, "assessor_sf": 1344, "garage": "2-car garage", "condition": "Excellent", "list_price": 2290000, "sold_price": 2250000, "sold_date": "2026-10-19", "U": 1257, "V": 930, "terms": "Cash", "dom": 102},
    {"row": 7, "comp": 7, "address": "522 Queen St", "lot_sf": 1419, "year": 1860, "style": "Federal", "beds": 3, "baths": "3/1", "fireplaces": 2, "basement": "YES", "total_sf": 3190, "assessor_sf": 2132, "garage": "Off-Street 2-car", "condition": "Excellent", "list_price": 2495000, "sold_price": 2650232, "sold_date": "2026-05-27", "U": 1178, "V": 953, "terms": "Cash", "dom": 3},
    {"row": 8, "comp": 8, "address": "210 S Pitt St", "lot_sf": 1598, "year": 1820, "style": "Traditional", "beds": 4, "baths": "3/1", "fireplaces": 1, "basement": "YES", "total_sf": 3296, "assessor_sf": 2632, "garage": "N/A", "condition": "Excellent", "list_price": 2295000, "sold_price": 2420000, "sold_date": "2026-07-13", "U": 919, "V": 817, "terms": "Cash", "dom": 5},
    {"row": 9, "comp": 9, "address": "109 S Lee St", "lot_sf": 1881, "year": 1880, "style": "Colonial", "beds": 3, "baths": "2/1", "fireplaces": 3, "basement": "NO", "total_sf": 2084, "assessor_sf": 2084, "garage": "N/A", "condition": "Excellent", "list_price": 2300000, "sold_price": 2300000, "sold_date": "2026-07-14", "U": 1104, "V": 1104, "terms": "Cash", "dom": 6},
    {"row": 10, "comp": 10, "address": "1018 Pendleton St", "lot_sf": 2178, "year": 2027, "style": "Contemporary", "beds": 5, "baths": "5/2", "fireplaces": 1, "basement": "Yes", "total_sf": 4273, "assessor_sf": 3458, "garage": "2-car detached w/ ADU", "condition": "New", "list_price": 3499000, "sold_price": None, "sold_date": None, "U": None, "V": None, "terms": None, "dom": None},
    {"row": 11, "comp": 11, "address": "121 N West St", "lot_sf": 1696, "year": 2026, "style": "Colonial, Contemporary, Transitional", "beds": 4, "baths": "4/1", "fireplaces": 0, "basement": "No", "total_sf": 2750, "assessor_sf": 2750, "garage": "Attached 2 car", "condition": "New", "list_price": 2742500, "sold_price": None, "sold_date": None, "U": None, "V": None, "terms": None, "dom": None},
    {"row": 12, "comp": 12, "address": "107 N West St", "lot_sf": 1500, "year": 2026, "style": None, "beds": 4, "baths": "4/1", "fireplaces": 0, "basement": "No", "total_sf": 3010, "assessor_sf": 2610, "garage": "Attached 2 car", "condition": "New", "list_price": 2435000, "sold_price": None, "sold_date": None, "U": None, "V": None, "terms": None, "dom": None},
    {"row": 13, "comp": 13, "address": "220 S Fairfax St", "lot_sf": 2813, "year": 1885, "style": "Federal", "beds": 5, "baths": "3/1", "fireplaces": 2, "basement": "Yes", "total_sf": 3680, "assessor_sf": 3170, "garage": "No", "condition": "Excellent", "list_price": 2995000, "sold_price": None, "sold_date": None, "U": None, "V": None, "terms": None, "dom": None},
    {"row": 14, "comp": 14, "address": "1215 Duke St", "lot_sf": 4479, "year": 1880, "style": "Federal", "beds": 3, "baths": "2/1", "fireplaces": 2, "basement": "No", "total_sf": 2480, "assessor_sf": 2840, "garage": "Detached 2-car garage", "condition": "Excellent", "list_price": 2440000, "sold_price": None, "sold_date": None, "U": None, "V": None, "terms": None, "dom": None},
]

# Rows 25-27 ("ORONOCO ESTIMATED PRICES").
SUBJECTS: dict[str, dict] = {
    "1007 New": {"row": 25, "lot_sf": 2400, "finished_sf": 3562, "garage_adu": 225000, "garage_adu_sf": 632, "expected_total": 3392805.3333333335},
    "1007A New/Remodel": {"row": 26, "lot_sf": 2400, "finished_sf": 2765, "garage_adu": 150000, "garage_adu_sf": 398, "expected_total": 2609006.666666667},
    "1009 New": {"row": 27, "lot_sf": 2400, "finished_sf": 3335, "garage_adu": 225000, "garage_adu_sf": 634, "expected_total": 3190926.666666667},
}

ADDRESS_VERIFICATION = {
    "checked_on": "2026-11-17",
    "fairfax_mar_matches": 0,
    "result": "None of the 13 comp addresses, nor 1007/1009 Oronoco St, exist in the Fairfax County Master "
              "Address Repository. All 15 are in the City of Alexandria address layer with ZIP 22314 "
              "(maps.alexandriava.gov alxAddressWm). The workbook is therefore a method reference only; its "
              "comps are outside ZIPs 22308/22309 and outside the county data source.",
}

FLAGS: list[dict] = [
    {"cells": "U4, U6, U7", "severity": "high", "decision": True,
     "issue": "Typed-in $/sf based on assessor sq ft does not equal SOLD PRICE ÷ ASSESSOR SQFT.",
     "detail": "U4 955 vs 967.54 (2,295,000 ÷ 2,372); U6 1,257 vs 1,674.11 (2,250,000 ÷ 1,344); U7 1,178 vs "
               "1,243.07 (2,650,232 ÷ 2,132). The typed values imply areas of about 2,403, 1,790 and 2,250 sf."},
    {"cells": "V5, V7, V8", "severity": "high", "decision": True,
     "issue": "Typed-in $/sf based on total finished sq ft does not equal SOLD PRICE ÷ LISTING TOTAL SQFT.",
     "detail": "V5 683 vs 531.38 (2,100,000 ÷ 3,952); V7 953 vs 830.79 (2,650,232 ÷ 3,190); V8 817 vs 734.22 "
               "(2,420,000 ÷ 3,296). Average V (V16) is 889.33 as typed but 829.76 when recomputed, which moves "
               "the 1009 New estimate from $3,190,927 to about $2,992,236."},
    {"cells": "U2:V14", "severity": "medium", "decision": False,
     "issue": "$/sf columns are typed numbers, not formulas, so they will not update when a price or area changes."},
    {"cells": "R25:R27, U25:U27, R23, C30", "severity": "high", "decision": True,
     "issue": "Appreciation is not applied.",
     "detail": "Column R (Appreciation) is 0 and TOTAL = Q + S leaves R out of the formula. R23 reads 'at ____%' and "
               "note 1 says 'Year of Year Appreciation expected at 3% thru June 2026', a date already past on the "
               "workbook's 11-4-26 update. The client must decide the rate, the period and whether it applies."},
    {"cells": "S25:S27, T25:T27", "severity": "medium", "decision": True,
     "issue": "Garage/ADU adjustments ($225,000, $150,000, $225,000) are unexplained constants.",
     "detail": "T shows 632, 398 and 634 sf next to them. $225,000 ÷ 634 sf ≈ $355/sf, $150,000 ÷ 398 sf ≈ $377/sf. "
               "No comp in the sheet supports these amounts; they should be confirmed as an agent assumption."},
    {"cells": "B2:B14", "severity": "low", "decision": False,
     "issue": "Column B contains the literal text '#VALUE!' in every comp row (an error pasted as text)."},
    {"cells": "E16", "severity": "medium", "decision": False,
     "issue": "Mean lot size divides by 14, but there are 13 comps (comp #4 is missing).",
     "detail": "=SUM(E2:E15)/14 gives 1,998.7 sf; the true mean of the 13 lots is 2,152.4 sf."},
    {"cells": "E18", "severity": "low", "decision": False,
     "issue": "MODE formula has broken references: =MODE(E2,E3,E5,E6,E7,E8,E9,#REF!,#REF!) returns #REF!."},
    {"cells": "E19", "severity": "low", "decision": False,
     "issue": "Median lot size uses only rows 2-9: =MEDIAN(E2:E9) = 1,944.5 sf; all 13 lots give 2,008 sf."},
    {"cells": "E21, E22, S22", "severity": "low", "decision": False,
     "issue": "High/low lot sizes and the low sold price are typed in rather than calculated."},
    {"cells": "S21, V21, V22", "severity": "medium", "decision": False,
     "issue": "High/low use fixed cell references (=S7, =V9, =V5) instead of MAX/MIN.",
     "detail": "They happen to equal the current max/min, but will be wrong as soon as comps change."},
    {"cells": "AA17, AC17, AA19, AA20, AA22", "severity": "medium", "decision": True,
     "issue": "Scratch calculations with unexplained constants outside the table.",
     "detail": "=2450000/2550, ×2404, =V19*2400, =U19*2400, =750*2400. None feed the estimate; their purpose is unknown."},
    {"cells": "Q25:Q27", "severity": "low", "decision": False,
     "issue": "'MEAN VALUE' repeats the AVERAGE formula (=G×V16), so columns I and Q are identical."},
    {"cells": "L14, M14", "severity": "medium", "decision": False,
     "issue": "1215 Duke St lists total finished 2,480 sf below its assessor above-grade 2,840 sf.",
     "detail": "Total finished area cannot be smaller than above-grade area; the row note says basement area is unavailable."},
    {"cells": "D2:D14", "severity": "low", "decision": False,
     "issue": "Lot size mixes units ('18 x 94 ft' dimensions vs 0.04 / 0.03 acres in D11, D12)."},
    {"cells": "R16 vs S16", "severity": "low", "decision": False,
     "issue": "Averages mix populations: list price averages all 13 rows, sold price and $/sf average only the 6 sold rows."},
    {"cells": "Rows 2-14", "severity": "high", "decision": True,
     "issue": "All comps and both subjects are in the City of Alexandria (22314), not Fairfax County 22308/22309.",
     "detail": "Fairfax County records cannot supply or verify these sales. A live comparison for 1007/1009 Oronoco "
               "St needs City of Alexandria records or an approved MLS feed."},
]


def _ppsf(row: dict, basis: str, use_typed: bool) -> float | None:
    if use_typed:
        return row["U" if basis == "above_grade" else "V"]
    area = row["assessor_sf" if basis == "above_grade" else "total_sf"]
    return row["sold_price"] / area if row["sold_price"] and area else None


def sold_rows() -> list[dict]:
    return [r for r in COMPS if r["sold_price"]]


def reproduce_workbook(subject: str = "1009 New", finished_sf: float | None = None,
                       garage_adjustment: float | None = None, appreciation_pct: float = 0.0) -> dict:
    """Variant A: the workbook exactly as entered (typed $/sf, average of the sold rows)."""
    s = SUBJECTS[subject]
    area = finished_sf if finished_sf is not None else s["finished_sf"]
    adj = garage_adjustment if garage_adjustment is not None else s["garage_adu"]
    out = workbook_formula(area, adj, appreciation_pct)
    # compare with the workbook whenever the inputs equal the workbook's own inputs
    out["expected_workbook_total"] = (s["expected_total"] if (area == s["finished_sf"] and adj == s["garage_adu"]
                                                              and not appreciation_pct) else None)
    return out


def workbook_formula(area: float, adj: float, appreciation_pct: float = 0.0) -> dict:
    """The workbook's formula for any subject area: average typed $/sf (column V) × area + adjustment."""
    rows = sold_rows()
    rates = [r["V"] for r in rows]
    mean = statistics.fmean(rates)
    base = area * mean
    total = base * (1 + appreciation_pct / 100) + adj
    return {
        "variant": "A", "title": "Workbook as entered",
        "description": "Average of the typed-in $/sf on total finished area (V2:V14) for the 6 sold comps, "
                       "× subject finished sq ft, + garage/ADU adjustment. Mirrors cells V16 and U27.",
        "comps": [{"address": r["address"], "sold_price": r["sold_price"], "sold_date": r["sold_date"],
                   "area": r["total_sf"], "ppsf": r["V"], "ppsf_source": "typed in workbook column V"} for r in rows],
        "ppsf": {"mean": mean, "median": statistics.median(rates), "high": max(rates), "low": min(rates)},
        "subject_area": area, "base_value": base, "adjustment": adj, "appreciation_pct": appreciation_pct,
        "estimate": total,
        "range_low": area * min(rates) * (1 + appreciation_pct / 100) + adj,
        "range_high": area * max(rates) * (1 + appreciation_pct / 100) + adj,
        "expected_workbook_total": None,
        "lines": [f"Average of V for sold comps = ({' + '.join(f'{r}' for r in rates)}) ÷ {len(rates)} = ${mean:,.4f}/sf",
                  f"{area:,.0f} sf × ${mean:,.4f}/sf = ${base:,.2f}",
                  f"+ garage/ADU adjustment ${adj:,.0f}" + (f", appreciation {appreciation_pct:g}%" if appreciation_pct else ""),
                  f"= ${total:,.2f}"],
    }


def _valuation_from_rows(rows: list[dict], area: float, adj: float, appreciation_pct: float) -> dict:
    inp = ValuationInput(
        subject_label="workbook subject", subject_total_finished_sf=area,
        subject_total_finished_source="workbook column G",
        comps=[CompArea(sale_id=r["row"], label=r["address"], price=r["sold_price"], sale_date=r["sold_date"],
                        above_grade_sf=r["assessor_sf"], total_finished_sf=r["total_sf"],
                        record_id=f"workbook row {r['row']}") for r in rows],
        adjustments=[Adjustment(label="Garage/ADU (workbook assumption)", amount=adj, source="workbook assumption")],
        appreciation_pct=appreciation_pct, primary_basis="total_finished", min_comps=3,
    )
    return compute_valuation(inp).bases["total_finished"].model_dump()


def recompute_same_comps(subject: str = "1009 New", finished_sf: float | None = None,
                         garage_adjustment: float | None = None, appreciation_pct: float = 0.0) -> dict:
    """Variant B: same 6 sold comps, $/sf recalculated as sold price ÷ listing total sq ft."""
    s = SUBJECTS[subject]
    area = finished_sf if finished_sf is not None else s["finished_sf"]
    adj = garage_adjustment if garage_adjustment is not None else s["garage_adu"]
    return recalculated_formula(area, adj, appreciation_pct)


def recalculated_formula(area: float, adj: float, appreciation_pct: float = 0.0) -> dict:
    """Variant B for any subject area: the workbook's sold comps with $/sf recalculated."""
    v = _valuation_from_rows(sold_rows(), area, adj, appreciation_pct)
    return {"variant": "B", "title": "Same comps, $/sf recalculated",
            "description": "The same 6 sold comps with $/sf recalculated by the app as sold price ÷ listing total "
                           "finished sq ft (column L), instead of the typed-in column V.", **v}


def app_selected(subject: str = "1009 New", finished_sf: float | None = None,
                 garage_adjustment: float | None = None, appreciation_pct: float = 0.0,
                 criteria: CompCriteria | None = None) -> dict:
    """Variant C: the app's own eligibility and ranking rules applied to the workbook's sales."""
    s = SUBJECTS[subject]
    area = finished_sf if finished_sf is not None else s["finished_sf"]
    adj = garage_adjustment if garage_adjustment is not None else s["garage_adu"]
    c = criteria or CompCriteria()
    subj = PropertyFacts(pin=subject, address=subject, property_type="TOWNHOUSE", year_built=WORKBOOK_DATE.year,
                         lot_sf=s["lot_sf"], total_finished_sf=int(area))
    excluded, ranked = [], []
    for r in COMPS:
        if not r["sold_price"]:
            excluded.append({"address": r["address"], "reason": "Active listing, no recorded sale price"})
            continue
        sale = SaleFacts(sale_id=r["row"], pin=r["address"], sale_date=dt.date.fromisoformat(r["sold_date"]),
                         price=r["sold_price"], validity="workbook sold row", source_dataset="Client workbook")
        if sale.sale_date > WORKBOOK_DATE:
            excluded.append({"address": r["address"], "reason": "Sold after the valuation date"})
            continue
        full, half = (int(x) for x in r["baths"].split("/"))
        prop = PropertyFacts(pin=r["address"], address=r["address"], property_type="TOWNHOUSE",
                             year_built=r["year"], beds=r["beds"], full_baths=full, half_baths=half,
                             above_grade_sf=r["assessor_sf"], total_finished_sf=r["total_sf"], lot_sf=r["lot_sf"],
                             style=r["style"], fireplaces=r["fireplaces"],
                             basement="Full" if r["basement"].lower() == "yes" else "None")
        diff = (r["total_sf"] - area) / area
        if c.living_area_tolerance_pct and abs(diff) > c.living_area_tolerance_pct / 100:
            excluded.append({"address": r["address"],
                             "reason": f"Total finished area {r['total_sf']:,} sf is {diff * 100:+.0f}% vs the subject's "
                                       f"{area:,.0f} sf (tolerance ±{c.living_area_tolerance_pct:g}%)"})
            continue
        factors = score_factors(subj, prop, sale, WORKBOOK_DATE, None, c, area_attr="total_finished_sf")
        rc = RankedComp(sale=sale, prop=prop, distance_miles=None,
                        months_before=months_between(sale.sale_date, WORKBOOK_DATE), score=combine(factors),
                        factors=factors)
        explain(rc)
        ranked.append(rc)
    ranked.sort(key=lambda x: (-x.score, -x.sale.sale_date.toordinal()))
    chosen = ranked[: c.max_results]
    for rc in ranked[c.max_results:]:
        excluded.append({"address": rc.prop.address, "reason": f"Ranked #{ranked.index(rc) + 1}; only the top "
                                                                f"{c.max_results} are used"})
    rows = [next(r for r in COMPS if r["address"] == rc.prop.address) for rc in chosen]
    v = _valuation_from_rows(rows, area, adj, appreciation_pct)
    return {"variant": "C", "title": "App's own comp selection",
            "description": "The app's rules applied to the workbook's comps: recorded sales only, total finished "
                           f"area within ±{c.living_area_tolerance_pct:g}%, ranked by similarity (location is not "
                           "available for these addresses), top 5, $/sf recalculated.",
            "ranking": [{"address": rc.prop.address, "score": round(rc.score, 1), "reason": rc.reason}
                        for rc in ranked],
            "excluded": excluded, **v}


def regression_report(subject: str = "1009 New", finished_sf: float | None = None,
                      garage_adjustment: float | None = None, appreciation_pct: float = 0.0) -> dict:
    a = reproduce_workbook(subject, finished_sf, garage_adjustment, appreciation_pct)
    b = recompute_same_comps(subject, finished_sf, garage_adjustment, appreciation_pct)
    c = app_selected(subject, finished_sf, garage_adjustment, appreciation_pct)
    expected = a["expected_workbook_total"]
    return {
        "workbook": WORKBOOK_FILE, "subject": subject, "valuation_date": WORKBOOK_DATE.isoformat(),
        "inputs": {"finished_sf": a["subject_area"], "garage_adjustment": a["adjustment"],
                   "appreciation_pct": appreciation_pct,
                   "garage_adjustment_note": "Editable assumption specific to this workbook example. "
                                             "It is not applied to any other property."},
        "regression": {"expected": expected, "actual": a["estimate"],
                       "passed": None if expected is None else abs(a["estimate"] - expected) < 0.01},
        "variants": [a, b, c],
        "live_comparison": {
            "available": False,
            "reason": "1009 Oronoco St is in the City of Alexandria (22314). Fairfax County records do not cover it, "
                      "so the app cannot select live comps for this example. Live selection is demonstrated on "
                      "22308/22309 addresses instead.",
        },
        "address_verification": ADDRESS_VERIFICATION,
        "flags": FLAGS,
        "subjects": {k: {kk: vv for kk, vv in v.items() if kk != "expected_total"} for k, v in SUBJECTS.items()},
    }
