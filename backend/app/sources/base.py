"""Provider interface for property, dwelling and sale data.

The refresh job only talks to a `DataProvider`. Fairfax County's ArcGIS layers
are the first implementation; an approved MLS feed (for example a RESO Web API
connection through Bridge) or another licensed provider can be added by
implementing the same methods and registering it in `registry.py`.

All rows carry the provider's dataset name, record identifier and the raw
payload so the app can show users exactly which public record a figure came
from.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class DatasetInfo:
    key: str
    title: str
    url: str
    publisher: str
    update_frequency: str | None = None
    last_edit: dt.datetime | None = None
    record_count: int | None = None
    terms: str | None = None


@dataclass
class ProviderInfo:
    key: str
    label: str
    kind: str  # "public_records" | "mls" | "licensed"
    attribution: str
    terms_url: str | None
    terms_summary: str
    datasets: list[DatasetInfo] = field(default_factory=list)


@dataclass
class AddressRow:
    source_dataset: str
    source_record_id: str
    source_object_id: int | None
    pin: str | None
    address_1: str
    street_num: str | None
    street_name: str | None
    unit: str | None
    city: str | None
    state: str | None
    zip: str | None
    status: str | None
    address_type: str | None
    jurisdiction: str | None
    subdivision: str | None
    lat: float | None
    lon: float | None
    raw: dict


@dataclass
class ParcelRow:
    pin: str
    legal_zip: str | None
    land_use: str | None
    livable_units: int | None
    zoning: str | None
    lot_sf: int | None
    lot_acres: float | None
    legal_description: str | None
    legal_address: str | None
    assessed_land: float | None
    assessed_building: float | None
    assessed_total: float | None
    assessed_tax_year: int | None
    tax_year: int | None
    raw: dict


@dataclass
class DwellingRow:
    pin: str
    source_object_id: int | None
    style: str | None
    year_built: int | None
    effective_year: int | None
    year_remodeled: int | None
    beds: int | None
    full_baths: int | None
    half_baths: int | None
    above_grade_sf: int | None
    rec_room_sf: int | None
    fireplaces: int | None
    basement_garage_cars: int | None
    basement: str | None
    basement_type: str | None
    basement_beds_dens: str | None
    grade: str | None
    condition: str | None
    exterior_wall: str | None
    heating: str | None
    roof: str | None
    model_name: str | None
    raw: dict


@dataclass
class AdditionRow:
    pin: str
    line: int | None
    area_sf: int | None
    lower_desc: str | None
    first_desc: str | None
    second_desc: str | None
    third_desc: str | None
    source_object_id: int | None
    raw: dict


@dataclass
class SaleRow:
    source_dataset: str
    source_object_id: int | None
    pin: str
    sale_date: dt.date | None
    price: int | None
    deed_book: str | None
    deed_page: str | None
    validity: str | None
    tax_year: int | None
    raw: dict
    list_price: int | None = None
    total_finished_sf: int | None = None
    days_on_market: int | None = None
    financing_terms: str | None = None


class DataProvider(Protocol):
    key: str

    def describe(self) -> ProviderInfo: ...

    def fetch_addresses(self, zips: list[str]) -> list[AddressRow]: ...

    def fetch_parcel_pins(self, zips: list[str]) -> set[str]: ...

    def fetch_parcels(self, pins: list[str]) -> list[ParcelRow]: ...

    def fetch_dwellings(self, pins: list[str]) -> list[DwellingRow]: ...

    def fetch_additions(self, pins: list[str]) -> list[AdditionRow]: ...

    def fetch_sales(self, pins: list[str]) -> list[SaleRow]: ...
