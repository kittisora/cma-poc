"""Measure CMA turnaround for real addresses through the HTTP API (no browser).

    python scripts/timing.py [--base http://127.0.0.1:8000] [--runs 3]

Steps timed per address: address search -> comps + pricing -> narrative draft ->
PDF export -> Word export. The initial data import is timed separately by the
refresh job (see `refresh_run.counts.timings_seconds`).
"""

from __future__ import annotations

import argparse
import json
import statistics
import time

import httpx

ADDRESSES = [("8069 fairfax rd", "22308"), ("7910 martha washington", "22309")]


def one(c: httpx.Client, query: str, zip_code: str) -> dict:
    t = {}
    t0 = time.perf_counter()
    r = c.get("/api/search", params={"q": query, "zip": zip_code}).json()["results"][0]
    t["search"] = time.perf_counter() - t0
    req = {"subject_pin": r["pin"]}
    s = time.perf_counter()
    a = c.post("/api/cma/analyze", json=req).json()
    t["comps_and_pricing"] = time.perf_counter() - s
    s = time.perf_counter()
    narrative = c.post("/api/agent/narrative", json=req).json()["narrative"]
    t["narrative"] = time.perf_counter() - s
    body = {"cma": req, "narrative": narrative, "expected_estimate": a["valuation"]["estimate"]}
    for fmt in ("pdf", "docx"):
        s = time.perf_counter()
        resp = c.post(f"/api/reports/{fmt}", json=body)
        resp.raise_for_status()
        t[fmt] = time.perf_counter() - s
    t["total"] = time.perf_counter() - t0
    return {"address": r["address"], "zip": r["zip"], "estimate": round(a["valuation"]["estimate"]),
            "comps": len(a["selected_sale_ids"]), **{k: round(v, 3) for k, v in t.items()}}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--runs", type=int, default=3)
    args = ap.parse_args()
    with httpx.Client(base_url=args.base, timeout=120) as c:
        meta = c.get("/api/meta").json()
        rows = [one(c, q, z) for _ in range(args.runs) for q, z in ADDRESSES]
    summary = {z: {"median_total_s": round(statistics.median(r["total"] for r in rows if r["zip"] == z), 3),
                   "median_comps_and_pricing_s": round(statistics.median(r["comps_and_pricing"] for r in rows
                                                                         if r["zip"] == z), 3)}
               for _, z in ADDRESSES}
    print(json.dumps({"runs": rows, "summary": summary,
                      "initial_import": (meta["data"]["last_refresh"] or {}).get("counts", {}).get("timings_seconds")},
                     indent=2))
