"""Database schema.

Design rules
- Every row that came from a data provider keeps `provider`, the provider's own
  record identifier, the raw source payload and the retrieval timestamp so a
  report figure can be traced back to the underlying public record.
- Sales are never deleted by a refresh. A sale that disappears from the source
  is kept and marked `in_latest_source = False`.
- When a provider changes an existing record (for example a sale moves from
  "Pending verification" to "Valid and verified sale"), the previous version is
  copied to `source_record_history` before it is overwritten.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class RefreshRun(Base):
    __tablename__ = "refresh_run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(64))
    zips: Mapped[str] = mapped_column(String(200))
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="running")
    counts: Mapped[dict] = mapped_column(JSON, default=dict)
    source_versions: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text)


class Address(Base):
    __tablename__ = "address"
    __table_args__ = (
        UniqueConstraint("provider", "source_record_id", name="uq_address_source"),
        Index("ix_address_zip_status", "zip", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(64))
    source_dataset: Mapped[str] = mapped_column(String(120))
    source_record_id: Mapped[str] = mapped_column(String(64))  # MAR SITE_ADDRESS_ID
    source_object_id: Mapped[int | None] = mapped_column(Integer)
    pin: Mapped[str | None] = mapped_column(String(30), index=True)
    address_1: Mapped[str] = mapped_column(String(200))
    street_num: Mapped[str | None] = mapped_column(String(20))
    street_name: Mapped[str | None] = mapped_column(String(100))
    unit: Mapped[str | None] = mapped_column(String(40))
    city: Mapped[str | None] = mapped_column(String(60))
    state: Mapped[str | None] = mapped_column(String(4))
    zip: Mapped[str | None] = mapped_column(String(10))
    status: Mapped[str | None] = mapped_column(String(20))
    address_type: Mapped[str | None] = mapped_column(String(60))
    jurisdiction: Mapped[str | None] = mapped_column(String(60))
    subdivision: Mapped[str | None] = mapped_column(String(120))
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    search_text: Mapped[str] = mapped_column(String(300), index=True)
    raw: Mapped[dict] = mapped_column(JSON, default=dict)
    retrieved_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    first_seen_run_id: Mapped[int | None] = mapped_column(ForeignKey("refresh_run.id"))
    last_seen_run_id: Mapped[int | None] = mapped_column(ForeignKey("refresh_run.id"))
    in_latest_source: Mapped[bool] = mapped_column(Boolean, default=True)


class Parcel(Base):
    __tablename__ = "parcel"

    pin: Mapped[str] = mapped_column(String(30), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64))
    zip: Mapped[str | None] = mapped_column(String(10), index=True)
    legal_zip: Mapped[str | None] = mapped_column(String(10))
    primary_address: Mapped[str | None] = mapped_column(String(200))
    lat: Mapped[float | None] = mapped_column(Float, index=True)
    lon: Mapped[float | None] = mapped_column(Float, index=True)
    land_use: Mapped[str | None] = mapped_column(String(120))
    property_type: Mapped[str] = mapped_column(String(20), index=True, default="OTHER")
    livable_units: Mapped[int | None] = mapped_column(Integer)
    zoning: Mapped[str | None] = mapped_column(String(120))
    lot_sf: Mapped[int | None] = mapped_column(Integer)
    lot_acres: Mapped[float | None] = mapped_column(Float)
    legal_description: Mapped[str | None] = mapped_column(String(300))
    assessed_land: Mapped[float | None] = mapped_column(Float)
    assessed_building: Mapped[float | None] = mapped_column(Float)
    assessed_total: Mapped[float | None] = mapped_column(Float)
    assessed_tax_year: Mapped[int | None] = mapped_column(Integer)
    tax_year: Mapped[int | None] = mapped_column(Integer)
    raw: Mapped[dict] = mapped_column(JSON, default=dict)
    retrieved_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    first_seen_run_id: Mapped[int | None] = mapped_column(ForeignKey("refresh_run.id"))
    last_seen_run_id: Mapped[int | None] = mapped_column(ForeignKey("refresh_run.id"))
    in_latest_source: Mapped[bool] = mapped_column(Boolean, default=True)


class Dwelling(Base):
    __tablename__ = "dwelling"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(64))
    pin: Mapped[str] = mapped_column(String(30), index=True)
    source_object_id: Mapped[int | None] = mapped_column(Integer)
    style: Mapped[str | None] = mapped_column(String(60))
    year_built: Mapped[int | None] = mapped_column(Integer)
    effective_year: Mapped[int | None] = mapped_column(Integer)
    year_remodeled: Mapped[int | None] = mapped_column(Integer)
    beds: Mapped[int | None] = mapped_column(Integer)
    full_baths: Mapped[int | None] = mapped_column(Integer)
    half_baths: Mapped[int | None] = mapped_column(Integer)
    above_grade_sf: Mapped[int | None] = mapped_column(Integer)  # county SFLA
    rec_room_sf: Mapped[int | None] = mapped_column(Integer)  # county RECROMAREA
    fireplaces: Mapped[int | None] = mapped_column(Integer)
    basement_garage_cars: Mapped[int | None] = mapped_column(Integer)
    basement: Mapped[str | None] = mapped_column(String(60))
    basement_type: Mapped[str | None] = mapped_column(String(60))
    basement_beds_dens: Mapped[str | None] = mapped_column(String(20))
    grade: Mapped[str | None] = mapped_column(String(60))
    condition: Mapped[str | None] = mapped_column(String(60))
    exterior_wall: Mapped[str | None] = mapped_column(String(80))
    heating: Mapped[str | None] = mapped_column(String(60))
    roof: Mapped[str | None] = mapped_column(String(60))
    model_name: Mapped[str | None] = mapped_column(String(60))
    raw: Mapped[dict] = mapped_column(JSON, default=dict)
    retrieved_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_run_id: Mapped[int | None] = mapped_column(ForeignKey("refresh_run.id"))


class DwellingAddition(Base):
    __tablename__ = "dwelling_addition"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(64))
    pin: Mapped[str] = mapped_column(String(30), index=True)
    line: Mapped[int | None] = mapped_column(Integer)
    area_sf: Mapped[int | None] = mapped_column(Integer)
    lower_desc: Mapped[str | None] = mapped_column(String(80))
    first_desc: Mapped[str | None] = mapped_column(String(80))
    second_desc: Mapped[str | None] = mapped_column(String(80))
    third_desc: Mapped[str | None] = mapped_column(String(80))
    source_object_id: Mapped[int | None] = mapped_column(Integer)
    raw: Mapped[dict] = mapped_column(JSON, default=dict)
    retrieved_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_run_id: Mapped[int | None] = mapped_column(ForeignKey("refresh_run.id"))


class Sale(Base):
    __tablename__ = "sale"
    __table_args__ = (
        UniqueConstraint("provider", "natural_key", name="uq_sale_natural_key"),
        Index("ix_sale_date_pin", "sale_date", "pin"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(64))
    source_dataset: Mapped[str] = mapped_column(String(120))
    # pin|sale_date|deed book|deed page|price - identifies one recorded transfer.
    natural_key: Mapped[str] = mapped_column(String(200))
    pin: Mapped[str] = mapped_column(String(30), index=True)
    sale_date: Mapped[dt.date] = mapped_column(Date, index=True)
    price: Mapped[int | None] = mapped_column(Integer)
    deed_book: Mapped[str | None] = mapped_column(String(12))
    deed_page: Mapped[str | None] = mapped_column(String(12))
    validity: Mapped[str | None] = mapped_column(String(80))
    tax_year: Mapped[int | None] = mapped_column(Integer)
    multi_parcel: Mapped[bool] = mapped_column(Boolean, default=False)
    deed_parcel_count: Mapped[int] = mapped_column(Integer, default=1)
    duplicate_rows: Mapped[int] = mapped_column(Integer, default=0)
    source_object_ids: Mapped[list] = mapped_column(JSON, default=list)
    # Listing fields. Empty for county records; an MLS provider can fill them.
    list_price: Mapped[int | None] = mapped_column(Integer)
    total_finished_sf: Mapped[int | None] = mapped_column(Integer)
    days_on_market: Mapped[int | None] = mapped_column(Integer)
    financing_terms: Mapped[str | None] = mapped_column(String(60))
    raw: Mapped[dict] = mapped_column(JSON, default=dict)
    first_retrieved_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_retrieved_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    first_seen_run_id: Mapped[int | None] = mapped_column(ForeignKey("refresh_run.id"))
    last_seen_run_id: Mapped[int | None] = mapped_column(ForeignKey("refresh_run.id"))
    in_latest_source: Mapped[bool] = mapped_column(Boolean, default=True)


class Permit(Base):
    """Building permits and site (land development) records, e.g. Fairfax County PLUS.

    Replaced in place on each refresh (the permitting system is the record of truth);
    a record that disappears from the source is kept and marked in_latest_source = False.
    """

    __tablename__ = "permit"
    __table_args__ = (
        UniqueConstraint("provider", "kind", "record_id", name="uq_permit_record"),
        Index("ix_permit_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(20))  # building | site
    record_id: Mapped[str] = mapped_column(String(40))
    pin: Mapped[str | None] = mapped_column(String(30), index=True)
    app_type: Mapped[str | None] = mapped_column(String(120))
    project_name: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str | None] = mapped_column(String(80))
    status_date: Mapped[dt.date | None] = mapped_column(Date)
    submitted_date: Mapped[dt.date | None] = mapped_column(Date)
    issued_date: Mapped[dt.date | None] = mapped_column(Date)
    closed_date: Mapped[dt.date | None] = mapped_column(Date)
    address: Mapped[str | None] = mapped_column(String(200))
    zip: Mapped[str | None] = mapped_column(String(10))
    link_url: Mapped[str | None] = mapped_column(String(500))
    raw: Mapped[dict] = mapped_column(JSON, default=dict)
    retrieved_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_run_id: Mapped[int | None] = mapped_column(ForeignKey("refresh_run.id"))
    in_latest_source: Mapped[bool] = mapped_column(Boolean, default=True)


class SourceRecordHistory(Base):
    """Previous versions of provider records that changed during a refresh."""

    __tablename__ = "source_record_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    table_name: Mapped[str] = mapped_column(String(40))
    record_key: Mapped[str] = mapped_column(String(200), index=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("refresh_run.id"))
    changed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    previous: Mapped[dict] = mapped_column(JSON, default=dict)
    changed_fields: Mapped[list] = mapped_column(JSON, default=list)


class PropertyInput(Base):
    """Facts entered by an agent (for example total finished sq ft from a listing).

    Kept separate from provider data so reports can label each value's source.
    """

    __tablename__ = "property_input"
    __table_args__ = (UniqueConstraint("pin", "field", name="uq_property_input"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pin: Mapped[str] = mapped_column(String(30), index=True)
    field: Mapped[str] = mapped_column(String(60))
    value: Mapped[dict] = mapped_column(JSON)  # {"value": ...}
    note: Mapped[str | None] = mapped_column(Text)
    entered_by: Mapped[str | None] = mapped_column(String(120))
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SavedCMA(Base):
    __tablename__ = "saved_cma"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    subject_pin: Mapped[str] = mapped_column(String(30), index=True)
    valuation_date: Mapped[dt.date] = mapped_column(Date)
    state: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AppSetting(Base):
    __tablename__ = "app_setting"

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
