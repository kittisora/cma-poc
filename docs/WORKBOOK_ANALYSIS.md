# Workbook analysis — "CMA Oronoco Master Updated 11-4-26.xlsx"

The workbook has one sheet (`Sheet1`, A1:AC32) and 13 embedded property photos:
- Rows 2–14: comps. There are 13 rows; comp #4 is missing.
- Rows 16–22: summary statistics.
- Rows 24–27: estimated prices for three subjects ("1007 New", "1007A New/Remodel", "1009 New").
- Rows 29–31: notes.

The app reproduces it in [`backend/app/valuation/workbook.py`](../backend/app/valuation/workbook.py), and
[`tests/test_workbook.py`](../backend/tests/test_workbook.py) re-reads the .xlsx to confirm the transcription.

**Location.** All 13 comps and both subjects are in the **City of Alexandria (22314)**, not Fairfax County
22308/22309 (see [DATA_VERIFICATION.md §9](DATA_VERIFICATION.md#9-workbook-example-addresses)). The workbook is
therefore a reference for fields and method only.

## Formula trace for "1009 New"

| Cell | Formula | Value |
|---|---|---|
| V4…V9 | typed numbers (not formulas) | 849, 683, 930, 953, 817, 1104 ($/total finished sf, the 6 sold comps) |
| V16 | `=AVERAGE(V2:V14)` (blank rows ignored) | 889.3333 |
| G27 | typed | 3,335 finished sf |
| I27 / Q27 | `=G27*V16` | 2,965,926.67 |
| S27 | typed "ADD For Garage/ADU" | 225,000 (T27 shows 634 sf) |
| R27 | typed "Appreciation" | 0 |
| U27 | `=Q27+S27` | **3,190,926.67** |

**Area definitions are consistent in the headline.** The subject's total finished sq ft (G) is multiplied by the
average $/sf of comp price ÷ comp total finished sq ft (V). The assessor-based column U is calculated and summarised
(U16, U19, U21, U22) but never used in an estimate. The app keeps the same two separate calculations: above-grade
area on both sides, or total finished area on both sides.

## Regression result

`GET /api/workbook/regression?subject=1009 New` (also the **Workbook check** page):

| Variant | What changes | 1009 New |
|---|---|---:|
| **A. Workbook as entered** | Typed V values, average of the 6 sold comps × 3,335 sf + $225,000 | **$3,190,926.67** = workbook U27 ✔ |
| B. Same comps, $/sf recalculated | V recomputed as sold price ÷ listing total sq ft (column L) | $2,992,235.73 |
| C. App's own comp selection | Recorded sales only; total finished area within ±35% (drops 109 S Lee St at 2,084 sf, −38%); ranked by similarity; top 5; $/sf recalculated | $2,809,550.44 |

- "1007 New" ($3,392,805.33) and "1007A New/Remodel" ($2,609,006.67) also reproduce to the cent.
- The garage/ADU amount, finished sq ft and appreciation are editable on that page. They apply only to the workbook
  example and are never added to other properties automatically.
- **Live comparison is not possible for this subject.** 1009 Oronoco St is outside Fairfax County, so county records
  cannot supply comps for it. The live comp selection is demonstrated on 22308/22309 addresses instead
  (see [WORKED_EXAMPLE.md](WORKED_EXAMPLE.md)).

**Why A and B differ:** three of the six typed $/sf values on total finished area do not equal sold price ÷ listing
total sq ft. That alone moves the estimate by about $198,700.

## Issues found

| Cells | Severity | Issue | Needs client decision |
|---|---|---|---|
| U4, U6, U7 | High | Typed $/sf (assessor) ≠ sold ÷ assessor sf. U4 955 vs 967.54; U6 1,257 vs 1,674.11; U7 1,178 vs 1,243.07. The typed values imply areas of about 2,403, 1,790 and 2,250 sf | Yes: which areas are correct |
| V5, V7, V8 | High | Typed $/sf (total finished) ≠ sold ÷ listing total sf. V5 683 vs 531.38; V7 953 vs 830.79; V8 817 vs 734.22. Recomputed average is 829.76, not 889.33 | Yes |
| U2:V14 | Medium | $/sf columns are typed numbers, not formulas, so they do not update when inputs change | — |
| R25:R27, U25:U27, R23, C30 | High | Appreciation is not applied. R is 0, TOTAL = Q + S omits R, R23 reads "at ____%", and the note says "3% thru June 2026", already past by the 11-4-26 update | Yes: rate, period, whether to apply |
| S25:S27, T25:T27 | Medium | Garage/ADU adjustments ($225,000 / $150,000 / $225,000) are unexplained constants: about $355/sf and $377/sf against 634/398 sf, with no supporting comp | Yes: confirm basis |
| B2:B14 | Low | Column B is the literal text "#VALUE!" in every comp row | — |
| E16 | Medium | Mean lot `=SUM(E2:E15)/14` divides by 14 but there are 13 comps: 1,998.7 sf vs a true 2,152.4 sf | — |
| E18 | Low | `=MODE(E2,E3,E5,E6,E7,E8,E9,#REF!,#REF!)` returns #REF! | — |
| E19 | Low | `=MEDIAN(E2:E9)` covers only 8 of 13 lots: 1,944.5 vs 2,008 sf | — |
| E21, E22, S22 | Low | High/low lot and low sold price are typed, not calculated | — |
| S21, V21, V22 | Medium | `=S7`, `=V9`, `=V5` hard-code the current max/min rows instead of MAX/MIN | — |
| AA17, AC17, AA19, AA20, AA22 | Medium | Scratch formulas with unexplained constants: `=2450000/2550`, `×2404`, `=V19*2400`, `=U19*2400`, `=750*2400`. None feed the estimate | Yes: delete or explain |
| Q25:Q27 | Low | "MEAN VALUE" repeats the AVERAGE formula, so I and Q are identical | — |
| L14, M14 | Medium | 1215 Duke St: total finished 2,480 < above-grade 2,840, which is impossible (the note says basement area is unknown) | — |
| D2:D14 | Low | Lot size mixes dimensions ("18 x 94 ft") and acres (0.04, 0.03) | — |
| R16 vs S16 | Low | List-price average uses all 13 rows; sold-price and $/sf averages use the 6 sold rows | — |
| Rows 2–14 | High | All addresses are in the City of Alexandria (22314), not Fairfax 22308/22309 | Yes: which market/source for Oronoco CMAs |

## How the app implements the method

[`backend/app/valuation/pricing.py`](../backend/app/valuation/pricing.py):

- Comp $/sf = recorded sale price ÷ area, calculated rather than typed.
- Average, median, high and low $/sf, each multiplied by the subject's area (the workbook's I, K, M and O columns).
- Point estimate = average (the workbook's choice), or median if the user selects it.
- Appreciation is applied explicitly: point × appreciation %. This fixes the workbook's TOTAL formula, which leaves R out.
- Adjustments are itemised, labelled "agent assumption", and added to the estimate and to both ends of the range.
- Range = the subject's area × the low and high comp $/sf, with the same appreciation and adjustments applied.
- When "total finished" is chosen, every comp in that calculation must have a total finished value. Comps without
  one are listed and left out of that calculation. The two area definitions are never mixed.
