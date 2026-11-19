# Worked CMA example — 8069 Fairfax Rd, Alexandria VA 22308

All figures were produced by the running app on 2026-11-17 from Fairfax County records retrieved the same day.
The valuation date is 2026-11-16 (today in Fairfax County when the CMA was run). Sample outputs are in
[`docs/examples/`](examples/):
- [`CMA-8069-FAIRFAX-RD.pdf`](examples/CMA-8069-FAIRFAX-RD.pdf)
- [`CMA-8069-FAIRFAX-RD.docx`](examples/CMA-8069-FAIRFAX-RD.docx)
- [`narrative-8069-fairfax-rd.txt`](examples/narrative-8069-fairfax-rd.txt), the template narrative used because no AI key is configured

## 1. Subject (county records)

| Item | Value | Record |
|---|---|---|
| Address | 8069 FAIRFAX RD, ALEXANDRIA VA 22308 | MAR SITE_ADDRESS_ID 101470802 |
| Parcel ID | `1022 03  0082A` | PARID |
| Type / style | Single-family detached / 2 Story | Parcels LUC; Dwelling OBJECTID 337092 |
| Year built | 2012 | Dwelling |
| Beds / baths | 5 / 4 full, 1 half | Dwelling |
| Above-grade living area | 3,165 sf | Dwelling SFLA |
| Basement | Full; rec room 336 sf | Dwelling |
| Total finished area | Not recorded (agent input needed) | — |
| Lot | 6,618 sf | Land |
| Assessor condition / grade | Average / Good 10 | Dwelling CDU, GRADE |
| Garage | Attached garage, 400 sf | Dwelling Additions |
| Assessed value (TY 2026) | $1,418,070 | Assessed Values |

Recorded transfers:

| Date | Price | Validity | Deed |
|---|---:|---|---|
| 2021-06-16 | $1,150,000 | Valid and verified sale | Book 27172 Page 2126 |
| 2012-12-26 | $835,050 | Valid and verified sale | Book 22808 Page 0024 |
| 2011-09-01 | $0 | No consideration | Book 21827 Page 1222 |

## 2. Comp search (default rules)

Default rules:
- within 1.0 mile
- sold on or before the valuation date and within the last 12 months
- county validity "Valid and verified sale" only
- price ≥ $10,000
- not a multi-parcel deed
- same property type
- above-grade area within ±35%
- most recent sale per parcel

The search started with 302 recorded transfers within 1 mi from 2025-11-16 onward:
- 0 were recorded after the valuation date.
- **185 were removed by county validity code**: No consideration 123, Non-representative price 11, Valid and verified
  multi-parcel 10, Transfer of convenience 8, and others.
- **74 were removed by living area outside ±35%.**
- **43 sales were eligible.** They were ranked by similarity, and the top 5 were selected.

Ranking never uses price. Default weights (out of 100): distance 20, recency 15, living area 20, beds 6, baths 7,
lot 7, year built 8, style 5, assessor condition/grade 7, basement/fireplace/garage 5.

| # | Address | Sold | Price | AG sf | $/AG sf | Bd | Ba | Built | Lot sf | Mi | Score |
|---|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| 1 | 8032 WASHINGTON RD | 2026-04-13 | $1,455,000 | 3,056 | $476.11 | 4 | 4/1 | 2013 | 6,600 | 0.07 | 85.5 |
| 2 | 8028 WELLINGTON RD | 2026-03-20 | $1,439,000 | 3,424 | $420.27 | 5 | 4/1 | 2016 | 6,325 | 0.11 | 78.5 |
| 3 | 8006 FORT HUNT RD | 2026-10-01 | $1,375,000 | 3,612 | $380.68 | 5 | 5/1 | 2019 | 6,165 | 0.19 | 78.1 |
| 4 | 8112 WINGFIELD PL | 2026-05-22 | $1,457,500 | 3,088 | $471.99 | 4 | 4/1 | 2018 | 11,701 | 0.29 | 76.3 |
| 5 | 8113 WELLINGTON RD | 2026-02-24 | $1,405,000 | 2,947 | $476.76 | 5 | 4/1 | 2017 | 9,219 | 0.23 | 76.3 |

Reasons the app gives:

1. Strong match on distance (0.07 mi) and above-grade living area (3,056 vs 3,165 sf, −3%). Main difference: sold 7.1 months before the valuation date.
2. Strong match on distance (0.11 mi) and living area (+8%). Main difference: sold 7.9 months before.
3. Strong match on distance (0.19 mi) and recency (sold 1.5 months before). Main difference: living area +14%.
4. Strong match on living area (−2%) and baths (same 4/1). Main difference: sold 5.8 months before.
5. Strong match on living area (−7%) and distance (0.23 mi). Main difference: sold 8.7 months before.

Source records, all "Valid and verified sale" and retrieved 2026-11-17:

| # | Record |
|---|---|
| 1 | PARID `1022 03  0092A` · Deed Book 28664 Page 0342 · OBJECTID 1428239 |
| 2 | PARID `1022 03  0130A` · Deed Book 28643 Page 0860 · OBJECTID 1411323 |
| 3 | PARID `1022 03  0036A` · Deed Book 28811 Page 1251 · OBJECTID 1434322 |
| 4 | PARID `1022 02100011` · Deed Book 28702 Page 1019 · OBJECTID 1422237 |
| 5 | PARID `1022 12  0182` · Deed Book 28619 Page 1403 · OBJECTID 1416430 |

## 3. Pricing (workbook method, above-grade calculation)

The total-finished calculation is unavailable until the agent enters total finished sq ft for the subject and comps.
The app therefore uses assessor above-grade area for both the subject and the comps.

```
$/sf = price ÷ above-grade sf:  $476.11, $420.27, $380.68, $471.99, $476.76
average $445.16 · median $471.99 · high $476.76 · low $380.68

Estimate  = 3,165 sf × $445.16/sf (average)  = $1,408,932.13
Range     = 3,165 × $380.68 … 3,165 × $476.76 = $1,204,838 – $1,508,933
Median-based alternative: 3,165 × $471.99   = $1,493,843
Adjustments: none · Appreciation: 0%

Estimated change since the last sale: +$258,932 (+22.5%) vs $1,150,000 on 2021-06-16
```

As a check, the county's own TY 2026 assessment is $1,418,070, 0.6% above the estimate.

Each figure was recomputed by `scripts/spot_check.py` from the live county services. All 29 checks matched,
including the $1,408,932.13 estimate.

## 4. Condition evidence

County records show only an assessor condition rating (Average) and grade (Good 10). Nothing in them indicates a
repair need, and year built by itself does not establish one. To confirm on site or from disclosures:
- interior condition and finishes
- roof, HVAC, water heater and windows
- basement finish and any water intrusion
- any detached garage or ADU

## 5. Timing

| Path | Time |
|---|---:|
| Browser (headless Edge): type address → comps + pricing on screen | 2.3–3.0 s |
| Browser: type address → PDF and Word downloaded (includes exclude/re-include and narrative draft) | 8.2–9.4 s |
| API only: search → comps + pricing → narrative → PDF → Word (median of 3) | 2.5 s |
| Initial data import for both ZIPs (separate, one-time; repeat refresh is the same) | 254 s first run, 245 s repeat |

A person reviewing the comps and narrative adds reading time. The system itself returns a complete, exportable CMA
in a few seconds.

## Second ZIP: 7910 Martha Washington St, 22309

1952 single-family detached house, 1,978 sf above grade.
- 22 eligible sales; the top 5 were selected.
- **Estimate $773,939**, range $670,833 – $900,478.
- Estimated change since the last sale: +$136,439 (+21.4%) vs $637,500 on 2022-10-17.
- Spot check: 29 of 29 items matched the county services.

## Limited-comp example: 8125 Mount Vernon Hwy, 22309

3,989 sf single-family detached house. Only three sales met every rule, so the app shows those three and explains why:

> Only 3 sales met every rule (target 5). The search started with 197 recorded transfers within 1 mi from
> 2025-11-16 onward; not marked as a valid sale by the county removed 112; above-grade living area differs by more
> than 35% removed 42; different property type (subject: single-family detached) removed 40.

It offers one-click widening with the number of extra sales each option adds:
- radius 1.5 mi: +16
- radius 2 mi: +46
- 24-month look-back: +3
- any living-area difference: +42

The estimate from the three comps was $1,323,996.
