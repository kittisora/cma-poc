# Data verification — Fairfax County public records for 22308 / 22309

Checked 2026-11-17 against the live services. Raw service and item metadata is saved in
[`docs/source_metadata/`](source_metadata/).

**Bottom line:** the county's public ArcGIS services support a working CMA for 22308 and 22309. Addresses join to
dwellings and sale history by an exact parcel ID. Sale prices and dates come from recorded deeds and are updated
daily. Three things are not in the data and stay agent inputs:
- total finished square footage
- detached garages and ADUs
- listing details (list price, days on market, financing terms, remarks)

Client-facing distribution of reports needs the county's permission (see [Terms](#terms-of-use-and-permissions)).

## 1. Sources

All layers are published by Fairfax County on Esri ArcGIS Online (organisation `ioennV6PpG5Xodq0`). They are public,
need no token, and are updated daily from the Department of Tax Administration (DTA) system. Esri hosts the
services; the county owns the data.

| Dataset | Service | Rows (county-wide) | Used for |
|---|---|---:|---|
| Master Address Repository (MAR) | `Master_Address_Repository` | 388,169 | Address, ZIP, parcel ID, map point |
| Real Estate Sales | `Tax_Administration_Real_Estate_Sales_Data` | 1,447,870 | Sale date, price, deed book/page, validity |
| Real Estate Dwelling | `Tax_Administration_Real_Estate_Dwelling_Data` | 340,853 | Style, year built, beds, baths, above-grade sq ft, condition |
| Dwelling Additions | `Tax_Administration_Real_Estate_Dwelling_Addition_Data` | 1,514,827 | Attached garage, carport, porches, decks |
| Parcels (tax) | `Tax_Administration_Real_Estate_Parcels_Data` | 370,774 | Land use (property type), zoning |
| Legal | `Tax_Administration_Real_Estate_Legal_Data` | 369,970 | Legal ZIP, legal description |
| Land | `Tax_Administration_Real_Estate_Land_Data` | 372,509 | Lot sq ft / acres |
| Assessed Values | `Tax_Administration_Real_Estate_Assessed_Values` | 369,572 | Current assessment (TY 2026) |

Base URL: `https://services1.arcgis.com/ioennV6PpG5Xodq0/ArcGIS/rest/services/<service>/FeatureServer/0`.
Field definitions come from the county's data dictionary,
[`dta_assessment_tables.pdf`](https://www.fairfaxcounty.gov/maps/sites/maps/files/assets/documents/dta_assessment_tables.pdf).

## 2. Real queries for each target ZIP

| Query | 22308 | 22309 |
|---|---:|---:|
| MAR addresses `ZIP='…'` | 5,103 | 10,929 |
| …current residential | 5,012 | 9,630 |
| …current non-residential | 68 | 813 |
| …historic (retired) | 23 | 486 |

Both ZIPs together give:

| Item | Count |
|---|---:|
| Parcels loaded (current MAR PINs + legal ZIP1) | 14,902 |
| Parcel records written | 14,898 |
| Dwelling records | 14,249 |
| Addition rows | 62,748 |
| Sale rows from the source | 61,690 |
| Unique sales after de-duplication | 61,264 |

Sale dates in the source run from 1912-07-19 to 2026-11-09.

"Valid and verified" sales per year in the two ZIPs: 2019: 709, 2020: 716, 2021: 826, 2022: 661, 2023: 487, 2024: 470,
2025: 431, 2026 (to Nov 9): 459.

## 3. How an address joins to a dwelling and its sales

```
MAR.PARCEL_PIN  ==  Dwelling.PARID  ==  Sales.PARID  ==  Parcels/Legal/Land/Values.PARID  ==  Parcels.PIN
```

- **Exact string match, fixed width.** IDs are space-padded, for example `1022 03  0082A` (two spaces before `0082A`)
  and `1022 0201    C`. Trimming or collapsing the inner spaces breaks the join. The app stores IDs verbatim and
  the PDF renderer preserves the spacing.
- **Worked join: 8069 Fairfax Rd, 22308.**
  - MAR: `SITE_ADDRESS_ID 101470802`, PARCEL_PIN `1022 03  0082A`.
  - Dwelling `OBJECTID 337092`: 2 Story, built 2012, 5 bedrooms, 4 full and 1 half bath, SFLA 3,165 sf, rec room 336 sf.
  - 3 sales:
    - 2011-09-01, $0, "No consideration"
    - 2012-12-26, $835,050, valid
    - 2021-06-16, $1,150,000, valid, Deed Book 27172 Page 2126
  - Land: 6,618 sf. Assessed (TY 2026): $1,418,070.
- **Cardinality.**
  - MAR → parcel is many-to-one: 95 parcels have more than one current address, mostly apartment and condo buildings (up to 106 addresses).
  - Parcel → dwelling is one-to-many: 18 parcels have two dwellings. The app uses the largest and adds a note.
  - Parcel → sales is one-to-many.
- **Units.** MAR `ADDRESS_1` already contains the unit (`8603 SACRAMENTO DR STE 8603`) for all 2,789 unit addresses.
  Condo units have their own PINs and dwelling rows.
- **ZIP sources disagree on 6 parcels** (MAR ZIP vs legal ZIP1). The app uses the MAR ZIP and keeps the legal ZIP.
- **153 parcels have no MAR address point** (common areas, some land). They cannot be mapped, so they are never used as comps.

## 4. Paging, dates and formats

- **Paging.** Every layer returns at most 2,000 rows per request and supports `resultOffset`. The refresh orders by
  `OBJECTID` and pages until `exceededTransferLimit` is false. Sales and dwellings are requested in batches of 150
  `PARID IN (…)`, with 4 requests in parallel. `tests/test_live.py::test_pagination_returns_more_than_one_page`
  checks paging against the live service.
- **Sale dates.** Dates are epoch milliseconds stored at local midnight. 471 rows land at 23:00 and 115 at 01:00
  local time because of daylight-saving offsets, so dates are rounded to the nearest local midnight in
  `America/New_York`. Pre-1970 dates are negative epochs and are handled (Windows' `fromtimestamp` cannot convert them).
- **Tax years.** The sales, parcels, legal and land tables are tagged TY 2027; assessed values are TY 2026.
- **Units of measure.** Areas are in square feet and lots in sq ft and acres. Prices are whole dollars of recorded
  consideration; seller concessions are not recorded.

## 5. Duplicates, multi-parcel deeds and sale validity

- **Duplicate transfers.**
  - 421 rows are exact duplicates of another row: same PARID, date, deed book/page, price and validity, but a different OBJECTID.
  - The refresh collapses rows on `(PARID, date, book, page, price)`, which removed 426 rows in total.
  - All source OBJECTIDs are kept, and differing validity text is kept in `raw._validity_variants`.
- **Multi-parcel deeds.**
  - 961 deed book/page references cover more than one parcel.
  - 3,016 sales are flagged multi-parcel: either the deed covers several parcels or the validity code says "multi-parcel".
  - 60 of them carry the plain code "Valid and verified sale" even though the price covers several parcels.
  - Multi-parcel sales are excluded from comps by default.
- **Validity codes (`SALEVAL_DESC`)** across all sales:

  | Code | Rows |
  |---|---:|
  | Valid and verified sale | 26,845 |
  | (blank, mostly pre-2004) | 11,090 |
  | No consideration | 10,594 |
  | Pending verification | 3,367 |
  | Non-representative price based on comps | 1,744 |
  | Duress | 1,367 |
  | Valid and verified multi-parcel sale | 1,270 |
  | Foreclosure | 1,099 |
  | Others (42 codes) | — |

  - Default comp eligibility is **"Valid and verified sale"** only.
  - The user can also accept "Pending verification" (recent sales not yet reviewed by the county), "Sale from lender - valid sale price" and "Valid and verified multi-parcel sale".
  - No other code can be selected.
- In 2024 to 2026, 1,360 of 3,294 transfers were valid and verified. Most of the rest were $0 or non-market transfers.

## 6. Missing fields (22308 + 22309)

| Field | Missing / zero |
|---|---:|
| Above-grade sq ft (SFLA) | 3 dwellings |
| Bedrooms (RMBED) | 332 dwellings (2.3%) |
| Full baths (FIXBATH) | 58 dwellings |
| Condition (CDU) | 11 |
| Grade | 21 |
| Basement description | 12 |
| Sale price null / $0 | 77 / 18,219 sales |
| Deed book/page blank | 11,076 sales (older records) |
| Map point | 153 parcels |

The app never fills a gap. A missing factor is dropped from that comp's score and listed as "not compared". A
subject without above-grade area gets no above-grade estimate and a warning.

## 7. Above-grade vs total finished square footage

| Term | Definition | Source |
|---|---|---|
| Above-grade living area | County `SFLA`: "Above grade living area total sq ft" (data dictionary) | County dwelling record |
| Basement rec room | County `RECROMAREA`: "Basement Rec room size (sq.ft)" | County dwelling record |
| Total finished area | Above-grade plus finished below-grade area, as listed | **Not in county data**: listing or agent input |

The workbook keeps these apart:
- Column U is "PRICE per SQFT (based on Assesor SQFT)".
- Column V is "PRICE per SQFT (based on Total Finished SQFT)".

The app keeps two separate calculations, each using matching area definitions. It does **not** treat
SFLA + RECROMAREA as total finished area. A rec room is only part of a finished basement, and the workbook's
listing figures do not follow that formula. Total finished sq ft is entered per property in the app, labelled
"agent input", and kept for reuse.

## 8. Field availability for the client workbook

| Workbook field | Status | Source / note |
|---|---|---|
| Address, ZIP, parcel | County | MAR |
| Lot area | County | Land SF; lot dimensions ("18 x 94 ft") are not published |
| Age / year built | County | YRBLT, EFFYR, YRREMOD |
| Style | County (different vocabulary) | County uses "2 Story", "Split Level"; "Colonial"/"Federal" are listing terms |
| Beds, baths, fireplaces, basement | County | RMBED, FIXBATH/FIXHALF, WBFP_PF, BSMT_DESC |
| Assessor above-grade sq ft | County | SFLA |
| Listing total finished sq ft | **Agent input / MLS** | Not in county data |
| Exterior | County | EXTWALL_DESC |
| Garage | Partial | Attached garage and carport (Additions), basement garage (BSMTCAR). Detached garage, ADU and parking are **agent input** |
| Condition | Partial | Assessor CDU and grade (mass appraisal). Listing condition is **agent input** |
| Improvements | **Agent input / MLS** | Only the remodel year is recorded |
| List price, DOM, terms | **MLS** | Not public-record fields |
| Sold price, sold date | County | Recorded deed |
| $/sf (assessor / total finished) | Calculated | Total-finished $/sf needs the agent input above |
| Appreciation %, garage/ADU adjustment | **Client decision** | Assumptions, editable per CMA |

## 9. Workbook example addresses

None of the 13 comps, nor 1007 and 1009 Oronoco St, exist anywhere in the Fairfax County MAR (0 matches county-wide).
All 15 are in the City of Alexandria's address layer (`maps.alexandriava.gov/…/alxAddressWm`) with ZIP **22314**.
The City of Alexandria is an independent city with its own assessor. These addresses are outside 22308/22309 and
outside this data source, so the workbook is used only as a reference for fields and method (see
[WORKBOOK_ANALYSIS.md](WORKBOOK_ANALYSIS.md)).

## 10. Refresh behaviour and traceability

- `python -m app.ingest.refresh` is repeatable. The second live run inserted 0 rows and updated 0 rows; all 61,264
  sales were unchanged. It took 245 s; the first import took 254 s.
- **Sales are never deleted.** A sale missing from a later extract is kept and flagged `in_latest_source = false`.
- Changed records (for example a validity change from "Pending verification" to "Valid and verified sale") are
  copied to `source_record_history` before they are overwritten.
- Every stored row keeps the provider, dataset, source record ID (OBJECTIDs; deed book/page for sales; SITE_ADDRESS_ID
  for addresses), the raw source payload, and first/last retrieval timestamps.
- Reports list, for the subject and every comp: dataset, record ID (PARID · deed book/page · sale date · OBJECTID) and
  retrieval time.
- Spot check on 2026-11-17 (`scripts/spot_check.py`): 29 of 29 items matched the live services for 8069 Fairfax Rd
  (22308) and 29 of 29 for 7910 Martha Washington St (22309). That covers addresses, ZIPs, areas, sale dates, prices,
  validity codes, and the displayed estimate recomputed from source values.

## Terms of use and permissions

The licence on every dataset points to the [Fairfax County GIS disclaimer](https://www.fairfaxcounty.gov/maps/disclaimer):

> "Copyright by Fairfax County. Except as provided herein, all rights are reserved. Authorization to reproduce
> material for internal or personal use by any user of this information is granted by Fairfax County…"

The disclaimer also says the data has no warranty of accuracy or completeness and is not a legal description.

- **Internal use** by the team is authorized.
- **Client-facing reports** given to sellers or buyers reproduce county data beyond internal use. Written permission
  should be requested from the Fairfax County DIT GIS Division and the Department of Tax Administration before
  reports are distributed. Until then, treat exported reports as internal working documents. The app prints the
  terms on every report.
- **Esri account.** Not needed to read these public layers. If the county later issues a token or the client moves to
  Esri-hosted services, set `ARCGIS_TOKEN`. Use of ArcGIS Online is also subject to Esri's terms.
- **Map tiles.** The dashboard uses OpenStreetMap's public tiles, which are fine for light internal use. For production
  traffic, switch to a provider with a commercial tile plan, for example Esri basemaps on the client's account. The
  report map is drawn locally without tiles, so exported reports carry no basemap licensing.
- **MLS feed.** The client's Bridge application has no approved local MLS feed. Adding one requires the MLS's data licence;
  display and redistribution rules for MLS data are typically stricter than county terms.
