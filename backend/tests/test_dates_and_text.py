import datetime as dt

from app.util.dates import arcgis_ms_to_local_date, subtract_months
from app.util.text import normalize_address, property_type_from_land_use


def test_sale_date_local_midnight():
    # 2021-06-16 04:00 UTC = midnight EDT
    assert arcgis_ms_to_local_date(1623816000000) == dt.date(2021, 6, 16)
    # 2012-12-26 05:00 UTC = midnight EST
    assert arcgis_ms_to_local_date(1356498000000) == dt.date(2012, 12, 26)


def test_sale_date_dst_artifacts_round_to_nearest_day():
    # stored one hour early (23:00 local the previous evening) -> next day
    assert arcgis_ms_to_local_date(1623816000000 - 3600_000) == dt.date(2021, 6, 16)
    # stored one hour late (01:00 local) -> same day
    assert arcgis_ms_to_local_date(1623816000000 + 3600_000) == dt.date(2021, 6, 16)


def test_sale_date_before_1970():
    ms = int((dt.datetime(1965, 3, 1, 5, tzinfo=dt.timezone.utc) - dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc))
             .total_seconds() * 1000)
    assert arcgis_ms_to_local_date(ms) == dt.date(1965, 3, 1)
    assert arcgis_ms_to_local_date(None) is None


def test_subtract_months_clamps_day():
    assert subtract_months(dt.date(2026, 3, 31), 1) == dt.date(2026, 2, 28)
    assert subtract_months(dt.date(2026, 11, 16), 12) == dt.date(2025, 11, 16)


def test_address_normalization():
    assert normalize_address("8069 Fairfax Road, Alexandria") == "8069 FAIRFAX RD ALEXANDRIA"
    assert normalize_address("123 north main street #4") == "123 N MAIN ST UNIT 4"


def test_property_type_mapping():
    assert property_type_from_land_use("Single-family, Detached ") == "DETACHED"
    assert property_type_from_land_use("Townhouse in condominium development") == "TOWNHOUSE"
    assert property_type_from_land_use("Garden Style condominium (=<4story)") == "CONDO"
    assert property_type_from_land_use("Condominium Office (< = 4 stories)") == "OTHER"
    assert property_type_from_land_use("Single-family residences inf com/ind") == "OTHER"
    assert property_type_from_land_use(None) == "OTHER"
