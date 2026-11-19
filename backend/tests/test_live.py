"""Read-only checks against the live Fairfax County services.

Run with:  pytest -m live
They query the county directly (not the local database) and, when the local
database has been refreshed, spot-check stored values against the source.
"""

import datetime as dt

import httpx
import pytest

from app.config import get_settings
from app.sources.fairfax_arcgis import FairfaxArcGISProvider
from app.util.dates import arcgis_ms_to_local_date

pytestmark = pytest.mark.live

KNOWN = {"pin": "1022 03  0082A", "address": "8069 FAIRFAX RD", "zip": "22308",
         "sale": {"date": dt.date(2021, 6, 16), "price": 1150000, "book": "27172", "page": "2126"}}


@pytest.fixture(scope="module")
def provider():
    s = get_settings()
    return FairfaxArcGISProvider(s.arcgis_base_url, timeout=60)


@pytest.mark.parametrize("zip_code", ["22308", "22309"])
def test_mar_has_current_residential_addresses(provider, zip_code):
    body = provider._post(f"{provider.layer_url('mar')}/query", {
        "where": f"ZIP='{zip_code}' AND ADDRESS_STATUS='Current'", "returnCountOnly": "true"})
    assert body["count"] > 4000


@pytest.mark.parametrize("zip_code", ["22308", "22309"])
def test_address_joins_dwelling_and_sales(provider, zip_code):
    feats = provider._post(f"{provider.layer_url('mar')}/query", {
        "where": f"ZIP='{zip_code}' AND ADDRESS_STATUS='Current' AND ADDRESS_TYPE='MAR Residential Address'",
        "outFields": "PARCEL_PIN,ADDRESS_1", "resultRecordCount": 25})["features"]
    pins = [f["attributes"]["PARCEL_PIN"] for f in feats]
    dw = provider.fetch_dwellings(pins)
    sales = provider.fetch_sales(pins)
    assert {d.pin for d in dw} & set(pins), "dwelling PARID must match MAR PARCEL_PIN exactly"
    assert {s.pin for s in sales} <= set(pins)


def test_known_sale_matches_source(provider):
    sales = provider.fetch_sales([KNOWN["pin"]])
    match = [s for s in sales if s.deed_book == KNOWN["sale"]["book"] and s.deed_page == KNOWN["sale"]["page"]]
    assert match and match[0].price == KNOWN["sale"]["price"] and match[0].sale_date == KNOWN["sale"]["date"]


def test_pagination_returns_more_than_one_page(provider):
    rows = provider._query_all("mar", "ZIP='22308'")
    assert len(rows) > 2000 and len({r["attributes"]["OBJECTID"] for r in rows}) == len(rows)


def test_local_database_matches_source_sample(provider):
    """Spot-check 10 recent stored sales against the county service (skipped if the DB is empty)."""
    from sqlalchemy import select

    from app.db import session_factory
    from app.models import Sale

    with session_factory()() as s:
        rows = list(s.scalars(select(Sale).where(Sale.price > 0).order_by(Sale.sale_date.desc()).limit(10)))
    if not rows:
        pytest.skip("local database not refreshed")
    by_pin = {}
    for src in provider.fetch_sales([r.pin for r in rows]):
        by_pin.setdefault(src.pin, []).append(src)
    for r in rows:
        assert any(x.sale_date == r.sale_date and x.price == r.price and x.deed_book == r.deed_book
                   for x in by_pin.get(r.pin, [])), f"{r.pin} {r.sale_date} {r.price} not found in source"


def test_date_conversion_against_raw(provider):
    body = provider._post(f"{provider.layer_url('sales')}/query", {
        "where": f"PARID='{KNOWN['pin']}' AND BOOK='{KNOWN['sale']['book']}'", "outFields": "SALEDT"})
    assert arcgis_ms_to_local_date(body["features"][0]["attributes"]["SALEDT"]) == KNOWN["sale"]["date"]


def test_service_is_reachable():
    r = httpx.get(get_settings().arcgis_base_url + "?f=json", timeout=30)
    assert r.status_code == 200
