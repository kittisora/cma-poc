"""End-to-end through the HTTP API: address entry -> comps -> pricing -> downloaded report."""

import io
import time
import zipfile
from types import SimpleNamespace

from .conftest import SUBJECT_PIN, VALUATION_DATE


def test_normal_path_address_to_downloaded_reports(client):
    t0 = time.perf_counter()
    found = client.get("/api/search", params={"q": "100 main st", "zip": "22308"}).json()["results"]
    assert found[0]["pin"] == SUBJECT_PIN

    body = {"subject_pin": SUBJECT_PIN, "valuation_date": VALUATION_DATE.isoformat()}
    cma = client.post("/api/cma/analyze", json=body).json()
    assert len(cma["selected_sale_ids"]) == 5
    est = cma["valuation"]["estimate"]
    assert est and cma["valuation"]["primary_basis"] == "above_grade"
    assert cma["change_since_last_sale"]["label"] == "Estimated change since the last sale"
    assert cma["comps"][0]["source"]["record_id"].startswith(f"PARID {cma['comps'][0]['pin']}")

    # agent enters total finished sq ft for subject and comps -> total-finished method becomes primary
    client.put(f"/api/properties/{SUBJECT_PIN}/inputs", json={"field": "total_finished_sf", "value": 2400,
                                                              "note": "listing"})
    tf = {c["sale_id"]: 2300 + 10 * i for i, c in enumerate(cma["comps"]) if c["selected"]}
    body2 = {**body, "comp_total_finished": tf,
             "adjustments": [{"label": "Garage", "amount": 20000, "note": "agent estimate"}]}
    cma2 = client.post("/api/cma/analyze", json=body2).json()
    assert cma2["valuation"]["primary_basis"] == "total_finished"
    est2 = cma2["valuation"]["estimate"]

    report = {"cma": body2, "narrative": "Reviewed narrative.", "expected_estimate": est2,
              "branding": {"company": "Test Realty", "primary_color": "#004488"}}
    preview = client.post("/api/reports/preview", json=report).json()
    assert preview["estimate"]["raw"]["estimate"] == est2
    assert preview["narrative"] == "Reviewed narrative."
    assert any(s["kind"] == "agent_input" for s in preview["sources"])

    pdf = client.post("/api/reports/pdf", json=report)
    assert pdf.status_code == 200 and pdf.content[:5] == b"%PDF-"
    assert "attachment" in pdf.headers["content-disposition"]
    xlsx = client.post("/api/reports/xlsx", json=report)
    assert xlsx.status_code == 200 and xlsx.headers["content-disposition"].endswith('.xlsx"')
    check_xlsx(xlsx.content, est2)
    docx = client.post("/api/reports/docx", json=report)
    assert docx.status_code == 200
    with zipfile.ZipFile(io.BytesIO(docx.content)) as z:
        xml = z.read("word/document.xml").decode()
    assert "Reviewed narrative." in xml and "Estimated change since the last sale" in xml
    assert f"{est2:,.0f}"[:5] in xml.replace("$", "")
    assert time.perf_counter() - t0 < 30


def check_xlsx(content: bytes, estimate: float) -> None:
    """The Excel report carries the workbook's ESTIMATED PRICES block with stored (cached) values."""
    import pytest
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    assert wb.sheetnames == ["CMA", "Subject", "Sources"]
    ws = wb["CMA"]
    cells = {c.value: c for row in ws.iter_rows() for c in row if isinstance(c.value, str)}
    for h in ("ESTIMATED PRICES", "AVERAGE", "MEDIAN", "HIGH", "LOW", "Appreciation", "ADD For Garage/ADU", "SF",
              "TOTAL", "MEAN", "MODE"):
        assert h in cells, h
    total = cells["TOTAL"]
    headline = ws.cell(row=total.row + 1, column=total.column).value
    assert abs(headline - estimate) < 0.01
    formulas = openpyxl.load_workbook(io.BytesIO(content))["CMA"]
    assert str(formulas.cell(row=total.row + 1, column=total.column).value).startswith("=")


def test_search_by_subdivision_block_street(client):
    areas = client.get("/api/search/areas").json()
    assert {"name": "TEST", "count": areas["subdivisions"][0]["count"]} == areas["subdivisions"][0]
    assert areas["blocks"] == []  # blocks are listed only within a subdivision
    assert any(s["name"] == "MAIN ST" for s in areas["streets"])
    found = client.get("/api/search/properties", params={"subdivision": "test", "street": "MAIN ST"}).json()
    assert found["total"] >= 1 and found["results"][0]["pin"] == SUBJECT_PIN
    assert found["results"][0]["subdivision"] == "TEST"
    assert client.get("/api/search/properties").status_code == 422
    assert client.get("/api/search/properties", params={"subdivision": "NOWHERE"}).json()["total"] == 0


def test_block_and_lot_parsing():
    from app.repository import parse_block, parse_lot
    assert parse_block("MT VERNON TERRACE LT 21 BLK A") == "A"
    assert parse_block("HOLLIN HALL VILLAGE LT 530 BLK 2 SEC 3") == "2"
    assert parse_block("WOODLAWN MEWS LT 69") is None and parse_block(None) is None
    assert parse_lot("ADDITION PLYMOUTH HAVEN LT 6B BLK 6 SEC 2") == "6B"


def test_export_refuses_figures_that_changed(client):
    report = {"cma": {"subject_pin": SUBJECT_PIN, "valuation_date": VALUATION_DATE.isoformat()},
              "expected_estimate": 1.0}
    r = client.post("/api/reports/pdf", json=report)
    assert r.status_code == 409 and "review the CMA again" in r.json()["detail"]


def test_manual_comp_selection_and_exclusion(client):
    body = {"subject_pin": SUBJECT_PIN, "valuation_date": VALUATION_DATE.isoformat()}
    auto = client.post("/api/cma/analyze", json=body).json()
    keep = auto["selected_sale_ids"][:3]
    manual = client.post("/api/cma/analyze", json={**body, "selected_sale_ids": keep}).json()
    assert manual["selection_mode"] == "manual" and manual["selected_sale_ids"] == keep
    assert manual["valuation"]["bases"]["above_grade"]["n"] == 3


def test_historical_valuation_via_api(client):
    r = client.post("/api/cma/analyze", json={"subject_pin": SUBJECT_PIN, "valuation_date": "2026-07-01"}).json()
    assert all(c["sale"]["sale_date"] <= "2026-07-01" for c in r["comps"])
    assert r["search"]["later_sales_excluded"] >= 2


def test_insufficient_comps_via_api(client):
    r = client.post("/api/cma/analyze", json={"subject_pin": SUBJECT_PIN, "valuation_date": VALUATION_DATE.isoformat(),
                                              "criteria": {"max_distance_miles": 0.35}}).json()
    assert r["search"]["eligible_count"] == 3 and r["search"]["limited"]
    assert r["search"]["limit_explanation"].startswith("Only 3 sales")
    assert r["search"]["hints"]
    assert len(r["selected_sale_ids"]) == 3 and r["valuation"]["estimate"]


def test_workbook_endpoint(client):
    r = client.get("/api/workbook/regression", params={"subject": "1009 New"}).json()
    assert r["regression"]["passed"]


def test_ai_disabled_paths(client):
    chat = client.post("/api/agent/chat", json={"cma": {"subject_pin": SUBJECT_PIN}, "messages": [
        {"role": "user", "content": "Why these comps?"}]})
    assert chat.status_code == 503
    nar = client.post("/api/agent/narrative", json={"subject_pin": SUBJECT_PIN,
                                                    "valuation_date": VALUATION_DATE.isoformat()}).json()
    assert nar["generated_by"] == "template" and "Comparable sales" in nar["narrative"]
    assert "Year built by itself does not establish" in nar["narrative"]


class _FakeMessages:
    """Scripted model: asks for comps and valuation, then answers citing a record."""

    def __init__(self):
        self.calls = []

    def create(self, **kw):
        self.calls.append(kw)
        n = len(self.calls)
        if n == 1:
            return SimpleNamespace(stop_reason="tool_use", content=[
                SimpleNamespace(type="tool_use", id="t1", name="get_ranked_comps", input={"include_candidates": False}),
                SimpleNamespace(type="tool_use", id="t2", name="get_valuation", input={}),
            ])
        tool_results = kw["messages"][-1]["content"]
        assert {r["tool_use_id"] for r in tool_results} == {"t1", "t2"}
        return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(
            type="text", text="The top comp is 102 MAIN ST [PARID 1000 01  0002 · Deed Book 30000].")])


def test_agent_tool_loop_uses_backend_figures(loaded):
    from app.agent.agent import TOOLS, run_agent
    from app.services import CMARequest

    fake = SimpleNamespace(beta=SimpleNamespace(messages=_FakeMessages()))
    out = run_agent(loaded, CMARequest(subject_pin=SUBJECT_PIN, valuation_date=VALUATION_DATE),
                    [{"role": "user", "content": "Explain the comps"}], client=fake, provider="anthropic")
    assert "[PARID 1000 01  0002" in out["reply"]
    assert [t["tool"] for t in out["tool_calls"]] == ["get_ranked_comps", "get_valuation"]
    first = fake.beta.messages.calls[0]
    assert first["model"] == "claude-opus-5-5" and first["fallbacks"] == "default"
    assert all(t["strict"] and t["input_schema"]["additionalProperties"] is False for t in TOOLS)


class _FakeResponses:
    """Scripted OpenAI Responses API: reasoning + two function calls, then a cited answer."""

    def __init__(self):
        self.calls = []

    def create(self, **kw):
        import copy
        self.calls.append(copy.copy(kw) | {"input": list(kw["input"])})
        if len(self.calls) == 1:
            return SimpleNamespace(status="completed", output_text="", output=[
                SimpleNamespace(type="reasoning", id="rs_1", summary=[]),
                SimpleNamespace(type="function_call", id="fc_1", call_id="c1", name="get_ranked_comps",
                                arguments='{"include_candidates": false}'),
                SimpleNamespace(type="function_call", id="fc_2", call_id="c2", name="get_valuation", arguments="{}"),
            ])
        sent = kw["input"]
        outputs = [i for i in sent if isinstance(i, dict) and i.get("type") == "function_call_output"]
        assert {o["call_id"] for o in outputs} == {"c1", "c2"}
        assert any(getattr(i, "type", None) == "reasoning" for i in sent), "reasoning items must be passed back"
        valuation = __import__("json").loads(next(o["output"] for o in outputs if o["call_id"] == "c2"))
        text = f"Estimate {valuation['estimate']:.0f} [PARID 1000 01  0002 · Deed Book 30000]."
        return SimpleNamespace(status="completed", output_text=text, output=[
            SimpleNamespace(type="message", content=[SimpleNamespace(type="output_text", text=text)])])


def test_openai_tool_loop_uses_backend_figures(loaded):
    from app.agent.agent import OPENAI_TOOLS, run_agent
    from app.services import CMARequest, run_cma

    req = CMARequest(subject_pin=SUBJECT_PIN, valuation_date=VALUATION_DATE)
    fake = SimpleNamespace(responses=_FakeResponses())
    out = run_agent(loaded, req, [{"role": "user", "content": "Explain the estimate"}], client=fake, provider="openai")
    assert out["provider"] == "openai" and out["model"] == "gpt-6.2-sol"
    assert [t["tool"] for t in out["tool_calls"]] == ["get_ranked_comps", "get_valuation"]
    assert f"{run_cma(loaded, req)['valuation']['estimate']:.0f}" in out["reply"]
    first = fake.responses.calls[0]
    assert first["model"] == "gpt-6.2-sol" and first["tools"] is OPENAI_TOOLS and "reasoning" not in first
    assert all(t["type"] == "function" and t["strict"] and t["parameters"]["additionalProperties"] is False
               and set(t["parameters"]["required"]) == set(t["parameters"]["properties"]) for t in OPENAI_TOOLS)


def test_ai_provider_selection(monkeypatch):
    from app.config import Settings

    assert Settings(_env_file=None, openai_api_key="", anthropic_api_key="").active_ai_provider is None
    assert Settings(_env_file=None, openai_api_key="k", anthropic_api_key="k").active_ai_provider == "openai"
    s = Settings(_env_file=None, openai_api_key="", anthropic_api_key="k")
    assert s.active_ai_provider == "anthropic" and s.ai_model == "claude-opus-5-5"
    assert Settings(_env_file=None, ai_provider="anthropic", openai_api_key="k").active_ai_provider is None
    assert Settings(_env_file=None, ai_provider="none", openai_api_key="k").ai_enabled is False


def test_optional_basic_auth(loaded, monkeypatch):
    from fastapi.testclient import TestClient

    from app.config import get_settings
    from app.main import create_app

    monkeypatch.setenv("APP_PASSWORD", "s3cret")
    get_settings.cache_clear()
    try:
        c = TestClient(create_app(run_migrations=False))
        assert c.get("/api/health").status_code == 200
        assert c.get("/api/meta").status_code == 401
        assert c.get("/api/meta", auth=("team", "wrong")).status_code == 401
        assert c.get("/api/meta", auth=("team", "s3cret")).status_code == 200
    finally:
        monkeypatch.delenv("APP_PASSWORD")
        get_settings.cache_clear()


def test_serves_exported_frontend(loaded, monkeypatch, tmp_path):
    """FastAPI serves the Next.js static export: one HTML file per route, /_next assets, HEAD probes, 404 page."""
    from fastapi.testclient import TestClient

    from app.config import get_settings
    from app.main import create_app

    (tmp_path / "_next" / "static").mkdir(parents=True)
    (tmp_path / "_next" / "static" / "app.js").write_text("console.log(1)")
    for name, body in {"index.html": "home", "workbook.html": "workbook", "workbook.txt": "rsc", "404.html": "missing"}.items():
        (tmp_path / name).write_text(body)
    (tmp_path / "workbook" / "__next.workbook").mkdir(parents=True)
    (tmp_path / "workbook" / "__next.workbook" / "__PAGE__.txt").write_text("segment")
    monkeypatch.setenv("FRONTEND_DIST", str(tmp_path))
    get_settings.cache_clear()
    try:
        c = TestClient(create_app(run_migrations=False))
        assert c.get("/").text == "home"
        assert c.get("/workbook").text == "workbook" and c.get("/workbook/").text == "workbook"
        assert c.head("/workbook").status_code == 200
        assert c.get("/workbook.txt?_rsc=abc").text == "rsc"
        assert c.get("/workbook/__next.workbook.__PAGE__.txt?_rsc=x").text == "segment"
        assert c.get("/_next/static/app.js").status_code == 200
        missing = c.get("/no-such-page")
        assert missing.status_code == 404 and missing.text == "missing"
        assert c.get("/../secrets").status_code == 404
        assert c.get("/api/health").json() == {"ok": True}
        assert c.get("/api/nope").status_code == 404
    finally:
        get_settings.cache_clear()


def test_openai_no_credit_is_reported_plainly(loaded):
    import httpx
    import openai
    import pytest

    from app.agent.agent import NO_CREDIT_MESSAGE, AgentUnavailable, run_agent
    from app.services import CMARequest

    class _NoCredit:
        def create(self, **kw):
            resp = httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com/v1/responses"))
            raise openai.RateLimitError("You have no credits remaining.", response=resp,
                                        body={"code": "insufficient_quota", "message": "You have no credits remaining."})

    with pytest.raises(AgentUnavailable) as err:
        run_agent(loaded, CMARequest(subject_pin=SUBJECT_PIN, valuation_date=VALUATION_DATE),
                  [{"role": "user", "content": "hi"}], client=SimpleNamespace(responses=_NoCredit()), provider="openai")
    assert str(err.value) == NO_CREDIT_MESSAGE


def test_workbook_check_with_a_property_subject(client):
    """The Workbook Check subject can be any property in the loaded data; the choice is saved for the team."""
    assert client.get("/api/workbook/subject").json()["key"] == "1009 New"  # default

    saved = client.put("/api/workbook/subject", json={"kind": "property", "key": SUBJECT_PIN}).json()
    assert saved["kind"] == "property" and saved["label"].startswith("100 MAIN ST")
    assert client.get("/api/workbook/subject").json() == saved
    assert client.put("/api/workbook/subject", json={"kind": "property", "key": "nope"}).status_code == 404

    r = client.get("/api/workbook/regression", params={"subject_pin": SUBJECT_PIN}).json()
    assert r["subject_kind"] == "property" and r["regression"]["expected"] is None
    assert r["inputs"]["garage_adjustment"] == 0  # the workbook's $225,000 is never carried over
    a, b, c = r["variants"]
    assert a["estimate"] == r["inputs"]["finished_sf"] * a["ppsf"]["mean"]  # workbook formula on this subject's area
    live = client.post("/api/cma/analyze", json={"subject_pin": SUBJECT_PIN}).json()["valuation"]["estimate"]
    assert c["variant"] == "C" and abs(c["estimate"] - live) < 0.01  # same figures as the CMA page

    # the workbook's own subjects still reproduce the workbook total
    client.put("/api/workbook/subject", json={"kind": "workbook", "key": "1009 New"})
    assert client.get("/api/workbook/regression", params={"subject": "1009 New"}).json()["regression"]["passed"]


def test_planned_house_drives_ranking_and_is_labelled(client):
    body = {"subject_pin": SUBJECT_PIN, "valuation_date": VALUATION_DATE.isoformat()}
    county = client.post("/api/cma/analyze", json=body).json()
    plan = {"beds": 5, "full_baths": 4, "half_baths": 1, "above_grade_sf": 2200, "year_built": 2026,
            "condition": "Excellent", "style": "  "}
    planned = client.post("/api/cma/analyze", json={**body, "plan": plan}).json()
    s = planned["subject"]
    assert (s["beds"], s["baths_label"], s["above_grade_sf"], s["year_built"]) == (5, "4/1", 2200, 2026)
    assert s["style"] == county["subject"]["style"]  # blank fields keep the county value
    assert set(s["planned"]) == {"beds", "full_baths", "half_baths", "above_grade_sf", "year_built", "condition"}
    assert planned["county_values"]["beds"] == county["subject"]["beds"]
    assert s["notes"][0].startswith("Planned house (agent input)")
    # comps are compared with the planned house, not the county record
    beds = next(f for f in planned["comps"][0]["factors"] if f["key"] == "beds")
    assert beds["subject_value"] == "5"
    assert planned["valuation"]["bases"]["above_grade"]["subject_area"] == 2200
    assert county["change_since_last_sale"] and planned["change_since_last_sale"] is None
    preview = client.post("/api/reports/preview", json={"cma": {**body, "plan": plan}}).json()
    rows = {r[0]: r for r in preview["subject_rows"]}
    assert rows["Bedrooms"][1:] == [5, "Planned house (agent input)"]
    assert rows["Style"][2] == "County dwelling"
    assert any(src["kind"] == "agent_input" and "planned house" in src["record_id"] for src in preview["sources"])
    # an empty plan changes nothing
    same = client.post("/api/cma/analyze", json={**body, "plan": {}}).json()
    assert same["plan"] is None and same["valuation"]["estimate"] == county["valuation"]["estimate"]
    assert client.post("/api/cma/analyze", json={**body, "plan": {"beds": -1}}).status_code == 422


def test_meta_offers_planned_house_choices(client):
    opts = client.get("/api/meta").json()["subject_options"]
    assert "2 Story" in opts["styles"] and "Excellent" in opts["conditions"]
