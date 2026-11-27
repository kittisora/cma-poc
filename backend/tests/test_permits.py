"""Building permits and site records: stages, area search, multi-street search and CMA warnings."""

import datetime as dt

from app.repository import permit_stage

from .conftest import SUBJECT_PIN, VALUATION_DATE


def test_permit_stage_rules():
    today = dt.date(2026, 11, 27)
    recent = dt.date(2026, 6, 1)
    assert permit_stage("building", "Issued", recent, None, today=today) == "active"
    assert permit_stage("building", "Issued - Amendment Pending", recent, None, today=today) == "active"
    assert permit_stage("building", "In Review", None, None, recent, today=today) == "pending"
    assert permit_stage("building", "Closed", recent, dt.date(2026, 9, 1), today=today) == "completed"
    assert permit_stage("site", "Recorded", recent, None, today=today) == "completed"
    assert permit_stage("site", "Approved", recent, None, today=today) == "active"
    assert permit_stage("site", "Approved", dt.date(2015, 1, 1), None, today=today) == "stale"
    assert permit_stage("building", "Expired", recent, None, today=today) == "inactive"
    assert permit_stage("building", "Refund Request Pending", recent, None, today=today) == "inactive"


def test_permits_in_an_area_with_summary(client):
    r = client.get("/api/permits", params={"subdivision": "TEST"}).json()
    assert r["total"] == 5
    assert r["summary"]["by_stage"] == {"active": 2, "completed": 1, "inactive": 1, "stale": 1}
    assert r["summary"]["new_construction"]["active"] == 2  # infill grading plan + new house
    first = {p["record_id"]: p for p in r["results"]}
    assert first["BLDR-1"]["street"] == "MAIN ST" and first["BLDR-1"]["lat"] is not None
    active = client.get("/api/permits", params={"street": ["MAIN ST"], "stage": "active"}).json()
    assert {p["record_id"] for p in active["results"]} == {"INF-1", "BLDR-1"}
    elm = client.get("/api/permits", params={"street": ["ELM CT"]}).json()
    assert [p["stage"] for p in elm["results"]] == ["stale"]
    assert client.get("/api/permits", params={"pin": SUBJECT_PIN}).json()["results"][0]["record_id"] == "INF-1"
    assert client.get("/api/permits", params={"stage": "bogus"}).status_code == 422


def test_multi_street_search_lists_every_address_with_permit_badge(client):
    r = client.get("/api/search/properties", params=[("subdivision", "TEST"), ("street", "MAIN ST"),
                                                     ("street", "ELM CT")]).json()
    streets = {x["street"] for x in r["results"]}
    assert streets == {"MAIN ST", "ELM CT"} and r["total"] == 10
    badges = {x["pin"]: x["permit_stage"] for x in r["results"]}
    assert badges[SUBJECT_PIN] == "active" and badges["1000 01  0003"] is None
    one = client.get("/api/search/properties", params={"street": "ELM CT"}).json()
    assert one["total"] == 1


def test_cma_shows_subject_permits_and_flags_rebuilt_comps(client):
    cma = client.post("/api/cma/analyze", json={"subject_pin": SUBJECT_PIN,
                                                 "valuation_date": VALUATION_DATE.isoformat()}).json()
    assert [p["record_id"] for p in cma["subject_permits"]] == ["INF-1"]
    comp = next(c for c in cma["comps"] if c["pin"] == "1000 01  0002")
    assert comp["permits"][0]["record_id"] == "BLDR-1"
    assert any("BLDR-1" in w and "after this sale" in w for w in comp["warnings"])
    other = next(c for c in cma["comps"] if c["pin"] == "1000 01  0003")
    assert not any("permit" in w for w in other["warnings"])  # its addition permit came before the sale
