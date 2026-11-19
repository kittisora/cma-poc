# Test results — 2026-11-19 (Next.js frontend, OpenAI agent)

Environment: Windows 11, Python 3.13.10, Node 24.11.1, Next.js 16.4.5 (static export), SQLite, headless Microsoft Edge (Playwright).

## Automated suites

| Suite | Command (from `backend/`) | Result |
|---|---|---|
| Offline: ranking, pricing, workbook regression, refresh, API, reports, AI tool loops (OpenAI and Anthropic, scripted), AI provider selection, frontend serving, optional login | `pytest -q` | **43 passed** |
| Live county services (read-only) | `pytest -q -m live` | **9 passed** |
| Frontend type-check + production build (Next.js static export) | `npm run build` (in `frontend/`) | **passed** |
| Browser workflow, both ZIPs | `python ../scripts/e2e_ui.py` | **passed**, no page or console errors |
| Source spot-check, both ZIPs | `python ../scripts/spot_check.py "<address>" <zip>` | **29/29 and 29/29 matched** |

### What the offline suite covers

**Normal path** (`test_api.py::test_normal_path_address_to_downloaded_reports`):
- address search → comps → pricing
- agent-entered total finished sq ft switches the headline to the total-finished calculation
- adjustment → preview → PDF → Word
- the Word file contains the reviewed narrative and the estimate

**Required cases:**

| Case | Test | What it checks |
|---|---|---|
| Missing field | `test_comps.py::test_missing_field_is_dropped_and_reported` | Comp without bedrooms: factor dropped, listed as "not compared", score still valid |
| Missing field (subject) | `test_comps.py::test_subject_missing_living_area_warns` | Subject without above-grade area gets a warning |
| Insufficient comps | `test_comps.py::test_insufficient_comps_shows_what_qualifies_and_why`, `test_api.py::test_insufficient_comps_via_api` | 3 eligible: all 3 shown and selected, explanation names the limiting rules, hints add sales. 2 eligible: flagged below the minimum |
| Repeat refresh | `test_refresh.py::test_repeat_refresh_is_idempotent` | Second run inserts and updates nothing |
| Preserved history | `test_refresh.py::test_refresh_preserves_sales_missing_from_source_and_records_changes` | Sale dropped by the source is kept and flagged; validity change recorded in history; new sale inserted |
| Historical valuation | `test_comps.py::test_historical_valuation_excludes_later_sales`, `test_api.py::test_historical_valuation_via_api` | Sales after the valuation date never appear |

**Other checks:**

| Check | Test |
|---|---|
| Ranking ignores price: prices scrambled, order unchanged | `test_ranking_ignores_price` |
| Subject's own sale is never a comp | `test_subject_own_sale_never_a_comp` |
| Duplicate collapse and multi-parcel flags | `test_first_refresh_collapses_duplicates_and_flags_multi_parcel` |
| Daylight-saving and pre-1970 date conversion | `test_dates_and_text.py` |
| Area definitions never mixed; appreciation and adjustments explicit | `test_pricing.py` |
| "Estimated change since the last sale" label | `test_pricing.py` |
| Export refused when figures changed since review (HTTP 409) | `test_export_refuses_figures_that_changed` |
| Workbook regression: 1009 New = $3,190,926.67, plus 1007 and 1007A | `test_workbook.py` |
| Workbook transcription matches the .xlsx cell by cell | `test_transcription_matches_xlsx` |
| AI disabled: chat returns 503; narrative falls back to a template | `test_ai_disabled_paths` |
| OpenAI tool loop (Responses API): function calls run against backend figures, reasoning items passed back, strict schemas, model `gpt-6.2-sol` | `test_openai_tool_loop_uses_backend_figures` (scripted client) |
| Anthropic tool loop (alternative provider) | `test_agent_tool_loop_uses_backend_figures` (scripted client) |
| AI provider selection (`auto` prefers OpenAI; explicit provider without key = off) | `test_ai_provider_selection` |
| FastAPI serves the Next.js export: routes, HEAD probes, prefetch segment files, `/_next` assets, 404 page, no path escape | `test_serves_exported_frontend` |

### What the live suite covers (`tests/test_live.py`)

- Both ZIPs return more than 4,000 current addresses.
- MAR PINs join to dwelling and sales rows in both ZIPs.
- A known sale matches the source: 8069 Fairfax Rd, Deed Book 27172 Page 2126, $1,150,000, 2021-06-16.
- Paging returns more than 2,000 unique rows.
- The 10 most recent stored sales match the county service.
- Raw epoch-to-date conversion is correct.

## Live-data edge cases (via the running API)

| Case | Subject | Result |
|---|---|---|
| Historical valuation 2025-06-30 | 8069 Fairfax Rd | 399 later sales excluded; newest comp 2025-06-23; estimate $1,425,554 |
| Only three qualify | 8125 Mount Vernon Hwy (22309) | 3 shown and selected; explanation and widening hints (+16 / +46 / +3 / +42) |
| None qualify | 835 Herbert Springs Rd (15,705 sf) | 0 eligible; no estimate; explanation and hint |
| Missing bedrooms | 1214 Woodcliff Ct | Bedrooms "not compared" on each comp; estimate $1,175,690 |
| Vacant land | 8207A Frye Rd | No dwelling; no estimate; three warnings |
| Repeat refresh (live) | both ZIPs | 0 inserted, 0 updated, 61,264 unchanged, 245 s |

## Browser workflow (Next.js UI)

`scripts/e2e_ui.py` runs in headless Edge against the app served by FastAPI. For each of the two addresses it:
- types the address and picks the match
- waits for comps and pricing
- clicks comp marker 2 on the map and checks that the same comp's table row is highlighted
- opens the comp detail side panel
- unchecks comp 1 and checks that the estimate changes, then resets to the automatic top 5
- drafts the narrative, opens the report preview dialog, and downloads the PDF and the Word file

It also opens the Ask AI panel, visits Workbook check (the regression badge shows "passed") and Data & sources,
returns to the CMA page with its state kept, and switches to dark mode.

| Check | 22308 (8069 Fairfax Rd) | 22309 (7910 Martha Washington St) |
|---|---|---|
| Estimate shown | $1,408,932 | $773,939 |
| Comps selected | 5 | 5 |
| Map click highlights row | yes | yes |
| Excluding a comp changes the estimate | yes | yes |
| PDF / Word downloaded | 25.7 KB / 52.5 KB | 26.2 KB / 52.5 KB |
| Page or console errors | none | none |

Screenshots: `docs/screenshots/` (cma_22308, cma_22309, comp_table, comp_detail, report_22308, report_22309, ask_ai,
workbook_check, data_sources, cma_dark, start).

## Timing

| Measurement | 22308 (8069 Fairfax Rd) | 22309 (7910 Martha Washington St) |
|---|---:|---:|
| Browser: address typed → options shown | 0.4 s | 0.3–0.5 s |
| Browser: → comps + pricing on screen | 1.3–2.3 s | 1.3–2.4 s |
| Browser: → full scripted workflow incl. preview, detail panel, PDF and Word | 10.8–14.7 s | 12.8–16.4 s |
| API: search → comps + pricing (median of 3) | 0.39 s | 0.61 s |
| API: search → narrative → PDF → Word (median of 3) | 2.48 s | 2.90 s |

| Data import (both ZIPs) | Seconds |
|---|---:|
| Fetch addresses | 7 |
| Fetch parcel IDs | 4 |
| Fetch parcel, legal, land, values | 57 |
| Fetch dwellings and additions | 117 |
| Fetch sales | 39 |
| Write database | 21 |
| **Total** | **245** (first run 254) |

## Live AI (OpenAI `gpt-6.2-sol`, 2026-11-20)

| Check | Result |
|---|---|
| `scripts\check-ai.ps1` (one small call) | OK, the model replied "OK" |
| Chat via API: "Why were these comps chosen, and which is the weakest?" (8069 Fairfax Rd) | Answered in 14.5 s after reading three tools (ranked comps, subject facts, search explanation). Every comp is cited by PARID and deed. |
| Narrative via API (8069 Fairfax Rd) | Drafted by AI in 13.3 s. It quotes the backend estimate exactly ($1,408,932.13), states the area basis, and lists what to inspect without inferring repairs from age. |
| Browser: "Draft with AI" for both addresses, then one chat question (`e2e_ui.py --ask-ai`) | Passed. The reply arrived in 18.1 s, cites county records, and renders as formatted Markdown. No page errors. |
| Account with no credit (the first key) | Chat shows "The OpenAI account has no credits left…"; the narrative falls back to the template |

The browser test calls the AI for each "Draft with AI" when a key is configured; `--ask-ai` adds one chat question.

## Not verified

- **PostgreSQL/PostGIS.** Docker and PostgreSQL are not installed here, so everything ran on SQLite. The CI workflow
  runs the full suite against `postgis/postgis:16-3.4`, but it has not run yet: the project is not in a git
  repository or on GitHub.
- **Docker image build.** The Dockerfile has not been built locally (no Docker).
- **Claude in Chrome extension.** It was not connected, so browser checks used Playwright with the installed Edge.
