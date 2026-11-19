"""Shared fixtures.

Offline tests use `FakeProvider`, a small synthetic neighbourhood whose rows have
the same shape as Fairfax County's records, loaded through the real refresh job.
Tests that hit the live county services are marked `live` and run only with
`pytest -m live`.
"""

from __future__ import annotations

import datetime as dt
import os
from dataclasses import replace

import pytest

# Tests never call a real AI provider: blank the keys even when .env holds real ones
# (environment variables take precedence over the .env file).
for _key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
    os.environ[_key] = ""
os.environ["AI_PROVIDER"] = "auto"

from app.config import get_settings  # noqa: E402
from app.db import make_engine, session_factory, set_engine  # noqa: E402
from app.migrate import upgrade_db  # noqa: E402
from app.sources.base import AdditionRow, AddressRow, DwellingRow, ParcelRow, ProviderInfo, SaleRow  # noqa: E402

SUBJECT_PIN = "1000 01  0001"
LAT0, LON0 = 38.74, -77.06
MI_LAT = 1 / 69.0  # degrees latitude per mile


def _addr(pin, num, street, lat, lon, zip_="22308", unit=None):
    return AddressRow(source_dataset="Fairfax County Master Address Repository", source_record_id=f"A{pin}",
                      source_object_id=1, pin=pin, address_1=f"{num} {street}", street_num=str(num),
                      street_name=street, unit=unit, city="ALEXANDRIA", state="VA", zip=zip_, status="Current",
                      address_type="MAR Residential Address", jurisdiction="FAIRFAX COUNTY", subdivision="TEST",
                      lat=lat, lon=lon, raw={"PARCEL_PIN": pin})


def _parcel(pin, land_use="Single-family, Detached ", lot=10000):
    return ParcelRow(pin=pin, legal_zip="22308", land_use=land_use, livable_units=1, zoning="R-3", lot_sf=lot,
                     lot_acres=round(lot / 43560, 4), legal_description="TEST LT", legal_address=None,
                     assessed_land=300000, assessed_building=500000, assessed_total=800000, assessed_tax_year=2026,
                     tax_year=2027, raw={"parcels": {"PARID": pin}})


def _dwelling(pin, sfla=2000, beds=4, full=2, half=1, year=1965, style="2 Story", cdu="Average", grade="Average",
              oid=1):
    return DwellingRow(pin=pin, source_object_id=oid, style=style, year_built=year, effective_year=None,
                       year_remodeled=None, beds=beds, full_baths=full, half_baths=half, above_grade_sf=sfla,
                       rec_room_sf=400, fireplaces=1, basement_garage_cars=None, basement="Full",
                       basement_type=None, basement_beds_dens=None, grade=grade, condition=cdu,
                       exterior_wall="Brick", heating="Central A/C", roof="Composition Shingle", model_name=None,
                       raw={"PARID": pin, "SFLA": sfla})


def _sale(pin, date, price, validity="Valid and verified sale", book=None, page=None, oid=None):
    return SaleRow(source_dataset="Fairfax County Real Estate Sales", source_object_id=oid or abs(hash((pin, date))) % 10**7,
                   pin=pin, sale_date=dt.date.fromisoformat(date), price=price, deed_book=book or "30000",
                   deed_page=page or str(abs(hash((pin, date, price))) % 9000 + 1000), validity=validity,
                   tax_year=2027, raw={"PARID": pin, "PRICE": price})


class FakeProvider:
    """A synthetic neighbourhood around (LAT0, LON0) with known answers."""

    key = "fake"

    def __init__(self):
        self.addresses = [_addr(SUBJECT_PIN, 100, "MAIN ST", LAT0, LON0)]
        self.parcels = [_parcel(SUBJECT_PIN)]
        self.dwellings = [_dwelling(SUBJECT_PIN)]
        self.sales = [_sale(SUBJECT_PIN, "2019-05-01", 650000, book="25000", page="0100")]
        comps = [
            # pin,           miles N, sfla, beds, year, sale date,    price,   validity
            ("1000 01  0002", 0.10, 2050, 4, 1966, "2026-08-01", 900000, "Valid and verified sale"),
            ("1000 01  0003", 0.20, 1900, 4, 1964, "2026-06-15", 860000, "Valid and verified sale"),
            ("1000 01  0004", 0.30, 2200, 5, 1970, "2026-03-10", 950000, "Valid and verified sale"),
            ("1000 01  0005", 0.40, 1800, 3, 1960, "2026-01-20", 780000, "Valid and verified sale"),
            ("1000 01  0006", 0.50, 2100, 4, 1968, "2025-12-05", 905000, "Valid and verified sale"),
            ("1000 01  0007", 0.15, 2000, 4, 1965, "2026-09-01", 10, "No consideration"),
            ("1000 01  0008", 0.25, 2000, 4, 1965, "2026-12-15", 990000, "Valid and verified sale"),  # after val date
            ("1000 01  0009", 2.50, 2000, 4, 1965, "2026-07-01", 880000, "Valid and verified sale"),  # too far
        ]
        for i, (pin, miles, sfla, beds, year, date, price, validity) in enumerate(comps, start=2):
            self.addresses.append(_addr(pin, 100 + i, "MAIN ST", LAT0 + miles * MI_LAT, LON0))
            self.parcels.append(_parcel(pin))
            self.dwellings.append(_dwelling(pin, sfla=sfla, beds=beds, year=year, oid=i))
            self.sales.append(_sale(pin, date, price, validity))
        # an exact duplicate row of comp 2's sale (same values, different OBJECTID)
        dup = [s for s in self.sales if s.pin == "1000 01  0002"][0]
        self.sales.append(replace(dup, source_object_id=999001))
        # a multi-parcel deed: one deed book/page covering two parcels
        for pin, miles in (("1000 01  0010", 0.12), ("1000 01  0011", 0.13)):
            self.addresses.append(_addr(pin, 200 + int(miles * 100), "OAK ST", LAT0 + miles * MI_LAT, LON0 + 0.001))
            self.parcels.append(_parcel(pin))
            self.dwellings.append(_dwelling(pin, sfla=2000))
            self.sales.append(_sale(pin, "2026-05-05", 1800000, "Valid and verified sale", book="31111", page="0001"))
        # a townhouse (different property type)
        th = "1000 02  0001"
        self.addresses.append(_addr(th, 300, "ELM CT", LAT0 + 0.05 * MI_LAT, LON0))
        self.parcels.append(_parcel(th, land_use="Townhouse in ownership development", lot=2000))
        self.dwellings.append(_dwelling(th, sfla=1900))
        self.sales.append(_sale(th, "2026-07-07", 600000))
        self.additions = [AdditionRow(pin=SUBJECT_PIN, line=1, area_sf=400, lower_desc=None,
                                      first_desc="ATTACHED GARAGE", second_desc=None, third_desc=None,
                                      source_object_id=1, raw={})]

    def describe(self) -> ProviderInfo:
        return ProviderInfo(key="fake", label="Fake", kind="test", attribution="test", terms_url=None,
                            terms_summary="test")

    def fetch_addresses(self, zips):
        return [a for a in self.addresses if a.zip in zips]

    def fetch_parcel_pins(self, zips):
        return {p.pin for p in self.parcels}

    def fetch_parcels(self, pins):
        return [p for p in self.parcels if p.pin in pins]

    def fetch_dwellings(self, pins):
        return [d for d in self.dwellings if d.pin in pins]

    def fetch_additions(self, pins):
        return [a for a in self.additions if a.pin in pins]

    def fetch_sales(self, pins):
        return [s for s in self.sales if s.pin in pins]


@pytest.fixture
def db_url(tmp_path):
    """SQLite by default. Set TEST_DATABASE_URL (e.g. a PostgreSQL/PostGIS URL in CI) to test another engine;
    its public schema is reset before each test."""
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        eng = make_engine(url)
        with eng.begin() as conn:
            conn.exec_driver_sql("DROP SCHEMA IF EXISTS public CASCADE")
            conn.exec_driver_sql("CREATE SCHEMA public")
        eng.dispose()
        return url
    return f"sqlite:///{(tmp_path / 'test.db').as_posix()}"


@pytest.fixture
def engine(db_url):
    upgrade_db(db_url)
    eng = make_engine(db_url)
    set_engine(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    with session_factory()() as s:
        yield s


@pytest.fixture
def fake_provider():
    return FakeProvider()


@pytest.fixture
def loaded(session, fake_provider):
    from app.ingest.refresh import run_refresh

    run = run_refresh(session, fake_provider, ["22308"])
    assert run.status == "succeeded"
    return session


@pytest.fixture
def client(loaded, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import create_app

    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    get_settings.cache_clear()
    app = create_app(run_migrations=False)
    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()


VALUATION_DATE = dt.date(2026, 11, 1)
