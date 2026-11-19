"""Repeatable refresh: idempotency, preserved history, duplicates, multi-parcel deeds."""

import datetime as dt
from dataclasses import replace

from sqlalchemy import func, select

from app.ingest.refresh import run_refresh
from app.models import Sale, SourceRecordHistory

from .conftest import SUBJECT_PIN


def _count(session, model):
    return session.scalar(select(func.count()).select_from(model))


def test_first_refresh_collapses_duplicates_and_flags_multi_parcel(loaded):
    s = loaded
    dup = s.scalar(select(Sale).where(Sale.pin == "1000 01  0002"))
    assert dup.duplicate_rows == 1 and len(dup.source_object_ids) == 2
    multi = list(s.scalars(select(Sale).where(Sale.deed_book == "31111")))
    assert len(multi) == 2 and all(m.multi_parcel and m.deed_parcel_count == 2 for m in multi)


def test_repeat_refresh_is_idempotent(loaded, fake_provider):
    s = loaded
    before = _count(s, Sale)
    run2 = run_refresh(s, fake_provider, ["22308"])
    assert run2.counts["sales"]["inserted"] == 0
    assert run2.counts["sales"]["updated"] == 0
    assert run2.counts["sales"]["unchanged"] == before
    assert run2.counts["addresses"]["inserted"] == 0
    assert _count(s, Sale) == before


def test_refresh_preserves_sales_missing_from_source_and_records_changes(loaded, fake_provider):
    s = loaded
    before = _count(s, Sale)
    # the source drops the subject's 2019 sale and re-codes comp 3's validity
    fake_provider.sales = [x for x in fake_provider.sales if x.pin != SUBJECT_PIN]
    fake_provider.sales = [replace(x, validity="Pending verification") if x.pin == "1000 01  0003" else x
                           for x in fake_provider.sales]
    # and adds a brand-new sale
    new = replace(fake_provider.sales[0], pin="1000 01  0005", sale_date=dt.date(2026, 10, 30), price=799000,
                  deed_page="7777", source_object_id=555)
    fake_provider.sales.append(new)
    run2 = run_refresh(s, fake_provider, ["22308"])
    c = run2.counts["sales"]
    assert c["inserted"] == 1 and c["updated"] == 1 and c["missing_from_source"] == 1
    assert _count(s, Sale) == before + 1  # nothing deleted
    kept = s.scalar(select(Sale).where(Sale.pin == SUBJECT_PIN))
    assert kept is not None and kept.in_latest_source is False and kept.price == 650000
    changed = s.scalar(select(Sale).where(Sale.pin == "1000 01  0003"))
    assert changed.validity == "Pending verification"
    hist = s.scalar(select(SourceRecordHistory).where(SourceRecordHistory.table_name == "sale"))
    assert hist.previous["validity"] == "Valid and verified sale" and hist.changed_fields == ["validity"]


def test_refresh_tracks_dwelling_changes(loaded, fake_provider):
    s = loaded
    fake_provider.dwellings = [replace(d, beds=5) if d.pin == SUBJECT_PIN else d for d in fake_provider.dwellings]
    run2 = run_refresh(s, fake_provider, ["22308"])
    assert run2.counts["dwellings"]["parcels_changed"] == 1
    hist = s.scalar(select(SourceRecordHistory).where(SourceRecordHistory.table_name == "dwelling"))
    assert hist.record_key == SUBJECT_PIN and hist.previous["dwellings"][0]["beds"] == 4
