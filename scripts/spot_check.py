"""Spot-check a CMA against the live county records.

    python scripts/spot_check.py "8069 fairfax rd" 22308 [--base http://127.0.0.1:8000]

Fetches the app's analysis, then re-reads the subject and each selected comp
directly from the Fairfax County services (MAR address, dwelling SFLA, sale
date/price/deed) and recomputes the displayed estimate by hand.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.sources.fairfax_arcgis import FairfaxArcGISProvider  # noqa: E402

BASE = "https://services1.arcgis.com/ioennV6PpG5Xodq0/ArcGIS/rest/services"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("zip")
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    a = ap.parse_args()
    app = httpx.Client(base_url=a.base, timeout=60)
    hit = app.get("/api/search", params={"q": a.query, "zip": a.zip}).json()["results"][0]
    cma = app.post("/api/cma/analyze", json={"subject_pin": hit["pin"]}).json()
    src = FairfaxArcGISProvider(BASE, timeout=60)
    sel = [c for c in cma["comps"] if c["selected"]]
    pins = [cma["subject"]["pin"]] + [c["pin"] for c in sel]
    dw = {d.pin: d for d in src.fetch_dwellings(pins)}
    sales = {}
    for s in src.fetch_sales(pins):
        sales.setdefault(s.pin, []).append(s)
    mar = src._post(f"{src.layer_url('mar')}/query", {
        "where": "PARCEL_PIN IN (" + ",".join(f"'{p}'" for p in pins) + ") AND ADDRESS_STATUS='Current'",
        "outFields": "PARCEL_PIN,ADDRESS_1,ZIP"})["features"]
    addr = {f["attributes"]["PARCEL_PIN"]: f["attributes"] for f in mar}

    checks = []
    subj = cma["subject"]
    checks.append(("subject address", subj["address"], addr.get(subj["pin"], {}).get("ADDRESS_1")))
    checks.append(("subject ZIP", subj["zip"], addr.get(subj["pin"], {}).get("ZIP")))
    checks.append(("subject above-grade sf", subj["above_grade_sf"], dw[subj["pin"]].above_grade_sf))
    rates = []
    for c in sel:
        s = c["sale"]
        match = [x for x in sales.get(c["pin"], []) if x.deed_book == s["deed_book"] and x.deed_page == s["deed_page"]]
        m = match[0] if match else None
        checks.append((f"{c['address']} address", c["address"], addr.get(c["pin"], {}).get("ADDRESS_1")))
        checks.append((f"{c['address']} sale date", s["sale_date"], m and m.sale_date.isoformat()))
        checks.append((f"{c['address']} price", s["price"], m and m.price))
        checks.append((f"{c['address']} validity", s["validity"], m and m.validity))
        checks.append((f"{c['address']} above-grade sf", c["property"]["above_grade_sf"], dw[c["pin"]].above_grade_sf))
        if m and dw[c["pin"]].above_grade_sf:
            rates.append(m.price / dw[c["pin"]].above_grade_sf)
    by_hand = dw[subj["pin"]].above_grade_sf * statistics.fmean(rates)
    shown = cma["valuation"]["bases"]["above_grade"]["estimate"]
    checks.append(("above-grade estimate (recomputed from source)", round(shown, 2), round(by_hand, 2)))
    ok = all(str(app_v) == str(src_v) for _, app_v, src_v in checks)
    print(json.dumps({"subject": subj["address"], "valuation_date": cma["valuation_date"], "all_match": ok,
                      "checks": [{"item": i, "app": av, "source": sv, "match": str(av) == str(sv)}
                                 for i, av, sv in checks]}, indent=2, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
