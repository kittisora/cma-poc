# Decisions that need the client

These cannot be settled from the data or the code. Until each one is decided, the app uses the default shown.

| # | Decision | Why it matters | App default until decided |
|---|---|---|---|
| 1 | **Permission to distribute county data in client-facing reports.** Contact the Fairfax County DIT GIS Division / Department of Tax Administration. | The county disclaimer authorizes internal or personal use only. | Reports print the county terms; treat them as internal working documents. |
| 2 | **Source of total finished sq ft** (listing, measurement, or agent estimate) and who enters it. | The workbook's headline method uses total finished area, which the county does not record. | Uses assessor above-grade area until values are entered; switches to total finished when the subject and comps have it. |
| 3 | **Appreciation**: rate, period and whether to apply it. The workbook note says "3% thru June 2026", but its formula applies 0%. | Changes every estimate. | 0%, editable per CMA. |
| 4 | **Garage/ADU adjustment basis.** Confirm the workbook's $225,000 / $150,000, or give a rule (for example $/sf). | Unexplained constants in the workbook; no comp supports them. | No adjustment unless the agent adds one, labelled "agent assumption". |
| 5 | **Correct areas for workbook comps** 207 S Alfred, 714 Wythe, 808 Oronoco, 522 Queen and 210 S Pitt (typed $/sf ≠ price ÷ area), and 1215 Duke (total finished < above-grade). | Moves 1009 New from $3,190,927 to about $2,992,236. | Regression reproduces the workbook as entered and shows the recalculated figure beside it. |
| 6 | **Market and source for Old Town Alexandria (22314) CMAs** like the Oronoco workbook. | Those addresses are outside Fairfax County, so a City of Alexandria provider or MLS is needed. | Not supported; workbook used as a method reference only. |
| 7 | **Point estimate: average or median $/sf.** | The workbook uses the average; the median resists outliers. | Average (workbook), switchable. |
| 8 | **Comp rules and weights**: radius, look-back, size tolerance, which county validity codes count. | Affects which sales are comps. | 1 mi, 12 months, ±35%, "Valid and verified sale" only, top 5; all editable. |
| 9 | **MLS feed.** Pursue Bridge approval or another licensed provider for list price, DOM, terms, total finished sq ft and condition. | These fields are not public record. | County data only; provider interface ready for a second source. |
| 10 | **Hosting, map tiles and AI key.** Where to deploy; a commercial tile provider (for example the client's Esri account); the AI spend limit and model. The client has supplied an OpenAI key (2026-11-19); a dedicated key with a monthly limit is advisable because this one was shared over chat. | OpenStreetMap tiles suit light internal use only; the AI assistant uses the server-side key only. | Local hosting, OSM tiles, OpenAI `gpt-6.2-sol` once the key is in `.env`. |
