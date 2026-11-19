"""Repeatable data refresh.

    python -m app.ingest.refresh                 # ZIPs from TARGET_ZIPS (.env)
    python -m app.ingest.refresh --zips 22308    # one ZIP

Guarantees
- Idempotent: running it twice in a row inserts nothing new the second time.
- Historical sales are preserved. Sales are never deleted; a sale that is no
  longer returned by the source is kept and flagged `in_latest_source=False`.
- Changes to existing provider records are copied to `source_record_history`.
- Duplicate transfer rows (same parcel, date, deed book/page and price under
  different source OBJECTIDs) are collapsed into one sale; the source IDs are kept.
- Deeds that convey more than one parcel are flagged `multi_parcel`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import time
import traceback
from collections import defaultdict
from collections.abc import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import session_factory
from ..migrate import upgrade_db
from ..models import (
    Address,
    Dwelling,
    DwellingAddition,
    Parcel,
    RefreshRun,
    Sale,
    SourceRecordHistory,
    utcnow,
)
from ..sources.base import AddressRow, DataProvider, DwellingRow, ParcelRow, SaleRow
from ..sources.registry import get_provider
from ..util.text import normalize_address, property_type_from_land_use

log = logging.getLogger("refresh")

ADDRESS_FIELDS = ["pin", "address_1", "street_num", "street_name", "unit", "city", "state", "zip",
                  "status", "address_type", "jurisdiction", "subdivision", "lat", "lon"]
PARCEL_FIELDS = ["legal_zip", "land_use", "livable_units", "zoning", "lot_sf", "lot_acres",
                 "legal_description", "assessed_land", "assessed_building", "assessed_total",
                 "assessed_tax_year", "tax_year"]
DWELLING_FIELDS = ["style", "year_built", "effective_year", "year_remodeled", "beds", "full_baths",
                   "half_baths", "above_grade_sf", "rec_room_sf", "fireplaces", "basement_garage_cars",
                   "basement", "basement_type", "basement_beds_dens", "grade", "condition",
                   "exterior_wall", "heating", "roof", "model_name"]
SALE_FIELDS = ["price", "deed_book", "deed_page", "validity", "tax_year", "multi_parcel",
               "deed_parcel_count", "list_price", "total_finished_sf", "days_on_market",
               "financing_terms"]


def sale_natural_key(pin: str, sale_date: dt.date, book: str | None, page: str | None,
                     price: int | None) -> str:
    return f"{pin}|{sale_date.isoformat()}|{book or ''}|{page or ''}|{'' if price is None else price}"


def _changed(obj, values: dict, fields: Iterable[str]) -> list[str]:
    out = []
    for f in fields:
        old, new = getattr(obj, f), values.get(f)
        if isinstance(old, float) or isinstance(new, float):
            if old is None or new is None:
                if old != new:
                    out.append(f)
            elif abs(float(old) - float(new)) > 1e-7:
                out.append(f)
        elif old != new:
            out.append(f)
    return out


def _history(session: Session, table: str, key: str, run_id: int, obj, fields: list[str]) -> None:
    prev = {f: getattr(obj, f) for f in fields}
    for k, v in prev.items():
        if isinstance(v, (dt.date, dt.datetime)):
            prev[k] = v.isoformat()
    session.add(SourceRecordHistory(table_name=table, record_key=key, run_id=run_id,
                                    previous=prev, changed_fields=fields))


# ---------------------------------------------------------------- addresses
def upsert_addresses(session: Session, provider_key: str, rows: list[AddressRow], run: RefreshRun,
                     zips: list[str], now: dt.datetime) -> dict:
    existing = {a.source_record_id: a for a in session.scalars(
        select(Address).where(Address.provider == provider_key, Address.zip.in_(zips)))}
    seen: set[str] = set()
    counts = {"inserted": 0, "updated": 0, "unchanged": 0, "missing_from_source": 0}
    for r in rows:
        if r.source_record_id in seen:
            continue
        seen.add(r.source_record_id)
        values = {f: getattr(r, f) for f in ADDRESS_FIELDS}
        search = normalize_address(" ".join(x for x in [r.address_1, r.city or "", r.state or "", r.zip or ""] if x))
        obj = existing.get(r.source_record_id)
        if obj is None:
            session.add(Address(provider=provider_key, source_dataset=r.source_dataset,
                                source_record_id=r.source_record_id, source_object_id=r.source_object_id,
                                search_text=search, raw=r.raw, retrieved_at=now,
                                first_seen_run_id=run.id, last_seen_run_id=run.id, **values))
            counts["inserted"] += 1
            continue
        changed = _changed(obj, values, ADDRESS_FIELDS)
        if changed:
            _history(session, "address", r.source_record_id, run.id, obj, changed)
            for f in changed:
                setattr(obj, f, values[f])
            counts["updated"] += 1
        else:
            counts["unchanged"] += 1
        obj.search_text, obj.raw, obj.source_object_id = search, r.raw, r.source_object_id
        obj.retrieved_at, obj.last_seen_run_id, obj.in_latest_source = now, run.id, True
    for key, obj in existing.items():
        if key not in seen and obj.in_latest_source:
            obj.in_latest_source = False
            counts["missing_from_source"] += 1
    return counts


def _primary_address(addrs: list[AddressRow]) -> AddressRow | None:
    current = [a for a in addrs if a.status == "Current"] or addrs
    if not current:
        return None
    return sorted(current, key=lambda a: (a.address_type != "MAR Residential Address",
                                          a.unit is not None, a.lat is None, a.address_1))[0]


# ------------------------------------------------------------------ parcels
def upsert_parcels(session: Session, provider_key: str, rows: list[ParcelRow],
                   addresses: list[AddressRow], run: RefreshRun, now: dt.datetime) -> dict:
    by_pin: dict[str, list[AddressRow]] = defaultdict(list)
    for a in addresses:
        if a.pin:
            by_pin[a.pin].append(a)
    pins = [r.pin for r in rows]
    existing = {}
    for i in range(0, len(pins), 900):
        existing.update({p.pin: p for p in session.scalars(select(Parcel).where(Parcel.pin.in_(pins[i:i + 900])))})
    counts = {"inserted": 0, "updated": 0, "unchanged": 0, "without_address_point": 0}
    for r in rows:
        values = {f: getattr(r, f) for f in PARCEL_FIELDS}
        prim = _primary_address(by_pin.get(r.pin, []))
        if prim is None:
            counts["without_address_point"] += 1
        derived = {
            "zip": (prim.zip if prim else None) or r.legal_zip,
            # MAR ADDRESS_1 already includes any unit ("8603 SACRAMENTO DR STE 8603")
            "primary_address": prim.address_1 if prim else r.legal_address,
            "lat": prim.lat if prim else None,
            "lon": prim.lon if prim else None,
            "property_type": property_type_from_land_use(r.land_use),
        }
        obj = existing.get(r.pin)
        if obj is None:
            session.add(Parcel(pin=r.pin, provider=provider_key, raw=r.raw, retrieved_at=now,
                               first_seen_run_id=run.id, last_seen_run_id=run.id, **values, **derived))
            counts["inserted"] += 1
            continue
        changed = _changed(obj, values, PARCEL_FIELDS)
        if changed:
            _history(session, "parcel", r.pin, run.id, obj, changed)
            counts["updated"] += 1
        else:
            counts["unchanged"] += 1
        for f, v in {**values, **derived}.items():
            setattr(obj, f, v)
        obj.raw, obj.retrieved_at, obj.last_seen_run_id, obj.in_latest_source = r.raw, now, run.id, True
    return counts


# ---------------------------------------------------------------- dwellings
def _dwelling_sig(d) -> tuple:
    return tuple(getattr(d, f) for f in DWELLING_FIELDS)


def replace_dwellings(session: Session, provider_key: str, rows: list[DwellingRow],
                      additions: list, pins: list[str], run: RefreshRun, now: dt.datetime) -> dict:
    new_by_pin: dict[str, list[DwellingRow]] = defaultdict(list)
    for r in rows:
        new_by_pin[r.pin].append(r)
    counts = {"rows": len(rows), "parcels_changed": 0, "parcels_with_multiple_dwellings": 0,
              "addition_rows": len(additions)}
    for i in range(0, len(pins), 900):
        batch = pins[i:i + 900]
        old: dict[str, list[Dwelling]] = defaultdict(list)
        for d in session.scalars(select(Dwelling).where(Dwelling.pin.in_(batch))):
            old[d.pin].append(d)
        for pin in batch:
            if pin in old and sorted(map(_dwelling_sig, old[pin]), key=str) != \
                    sorted(map(_dwelling_sig, new_by_pin.get(pin, [])), key=str):
                counts["parcels_changed"] += 1
                session.add(SourceRecordHistory(
                    table_name="dwelling", record_key=pin, run_id=run.id, changed_fields=["*"],
                    previous={"dwellings": [dict(zip(DWELLING_FIELDS, _dwelling_sig(d))) for d in old[pin]]}))
        session.execute(delete(Dwelling).where(Dwelling.pin.in_(batch)))
        session.execute(delete(DwellingAddition).where(DwellingAddition.pin.in_(batch)))
    for pin, lst in new_by_pin.items():
        if len(lst) > 1:
            counts["parcels_with_multiple_dwellings"] += 1
    session.add_all(Dwelling(provider=provider_key, pin=r.pin, source_object_id=r.source_object_id,
                             raw=r.raw, retrieved_at=now, last_seen_run_id=run.id,
                             **{f: getattr(r, f) for f in DWELLING_FIELDS}) for r in rows)
    session.add_all(DwellingAddition(provider=provider_key, pin=a.pin, line=a.line, area_sf=a.area_sf,
                                     lower_desc=a.lower_desc, first_desc=a.first_desc,
                                     second_desc=a.second_desc, third_desc=a.third_desc,
                                     source_object_id=a.source_object_id, raw=a.raw, retrieved_at=now,
                                     last_seen_run_id=run.id) for a in additions)
    return counts


# -------------------------------------------------------------------- sales
def normalize_sales(rows: list[SaleRow]) -> tuple[list[dict], dict]:
    """Collapse duplicate transfer rows and flag multi-parcel deeds."""
    groups: dict[str, list[SaleRow]] = defaultdict(list)
    skipped_no_date = 0
    for r in rows:
        if r.sale_date is None:
            skipped_no_date += 1
            continue
        groups[sale_natural_key(r.pin, r.sale_date, r.deed_book, r.deed_page, r.price)].append(r)

    deed_pins: dict[tuple[str, str], set[str]] = defaultdict(set)
    for r in rows:
        if r.deed_book and r.deed_page:
            deed_pins[(r.deed_book, r.deed_page)].add(r.pin)

    out = []
    dup_rows = 0
    for key, grp in groups.items():
        first = grp[0]
        dup_rows += len(grp) - 1
        validities = sorted({g.validity for g in grp if g.validity})
        validity = first.validity or (validities[0] if validities else None)
        deed_count = len(deed_pins.get((first.deed_book, first.deed_page), {first.pin})) \
            if first.deed_book and first.deed_page else 1
        multi = deed_count > 1 or ("multi" in (validity or "").lower())
        raw = dict(first.raw)
        if len(validities) > 1:
            raw["_validity_variants"] = validities
        out.append({
            "natural_key": key, "pin": first.pin, "sale_date": first.sale_date, "price": first.price,
            "deed_book": first.deed_book, "deed_page": first.deed_page, "validity": validity,
            "tax_year": first.tax_year, "multi_parcel": multi, "deed_parcel_count": deed_count,
            "duplicate_rows": len(grp) - 1, "source_dataset": first.source_dataset,
            "source_object_ids": sorted(g.source_object_id for g in grp if g.source_object_id is not None),
            "list_price": first.list_price, "total_finished_sf": first.total_finished_sf,
            "days_on_market": first.days_on_market, "financing_terms": first.financing_terms,
            "raw": raw,
        })
    stats = {"source_rows": len(rows), "duplicate_rows_collapsed": dup_rows,
             "skipped_missing_date": skipped_no_date,
             "multi_parcel_sales": sum(1 for s in out if s["multi_parcel"])}
    return out, stats


def upsert_sales(session: Session, provider_key: str, rows: list[SaleRow], pins: list[str],
                 run: RefreshRun, now: dt.datetime) -> dict:
    normalized, stats = normalize_sales(rows)
    existing: dict[str, Sale] = {}
    for i in range(0, len(pins), 900):
        for s in session.scalars(select(Sale).where(Sale.provider == provider_key,
                                                    Sale.pin.in_(pins[i:i + 900]))):
            existing[s.natural_key] = s
    counts = {"inserted": 0, "updated": 0, "unchanged": 0, "missing_from_source": 0, **stats}
    seen: set[str] = set()
    for v in normalized:
        key = v["natural_key"]
        seen.add(key)
        obj = existing.get(key)
        if obj is None:
            session.add(Sale(provider=provider_key, first_retrieved_at=now, last_retrieved_at=now,
                             first_seen_run_id=run.id, last_seen_run_id=run.id, in_latest_source=True, **v))
            counts["inserted"] += 1
            continue
        changed = _changed(obj, v, SALE_FIELDS)
        if changed:
            _history(session, "sale", key, run.id, obj, changed)
            for f in changed:
                setattr(obj, f, v[f])
            counts["updated"] += 1
        else:
            counts["unchanged"] += 1
        obj.source_object_ids, obj.duplicate_rows, obj.raw = v["source_object_ids"], v["duplicate_rows"], v["raw"]
        obj.last_retrieved_at, obj.last_seen_run_id, obj.in_latest_source = now, run.id, True
    for key, obj in existing.items():
        if key not in seen and obj.in_latest_source:
            obj.in_latest_source = False  # kept, never deleted
            counts["missing_from_source"] += 1
    return counts


# ---------------------------------------------------------------------- run
def run_refresh(session: Session, provider: DataProvider, zips: list[str],
                now: dt.datetime | None = None) -> RefreshRun:
    now = now or utcnow()
    run = RefreshRun(provider=provider.key, zips=",".join(zips), started_at=now, status="running")
    session.add(run)
    session.commit()
    timings: dict[str, float] = {}
    t0 = time.perf_counter()

    def mark(step: str, start: float) -> float:
        timings[step] = round(time.perf_counter() - start, 2)
        log.info("%s done in %.1fs", step, timings[step])
        return time.perf_counter()

    try:
        t = time.perf_counter()
        addresses = provider.fetch_addresses(zips)
        t = mark("fetch_addresses", t)
        legal_pins = provider.fetch_parcel_pins(zips)
        pins = sorted({a.pin for a in addresses if a.pin and a.status == "Current"} | legal_pins)
        t = mark("fetch_parcel_pins", t)
        parcels = provider.fetch_parcels(pins)
        t = mark("fetch_parcels", t)
        dwellings = provider.fetch_dwellings(pins)
        additions = provider.fetch_additions(pins)
        t = mark("fetch_dwellings", t)
        sales = provider.fetch_sales(pins)
        t = mark("fetch_sales", t)

        counts = {
            "pins": len(pins),
            "addresses": upsert_addresses(session, provider.key, addresses, run, zips, now),
            "parcels": upsert_parcels(session, provider.key, parcels, addresses, run, now),
            "dwellings": replace_dwellings(session, provider.key, dwellings, additions, pins, run, now),
            "sales": upsert_sales(session, provider.key, sales, pins, run, now),
        }
        session.flush()
        t = mark("write_database", t)
        timings["total"] = round(time.perf_counter() - t0, 2)
        counts["timings_seconds"] = timings
        run.counts = counts
        run.status = "succeeded"
        run.finished_at = utcnow()
        session.commit()
        return run
    except Exception:
        session.rollback()
        run = session.get(RefreshRun, run.id)
        run.status = "failed"
        run.error = traceback.format_exc()
        run.finished_at = utcnow()
        session.commit()
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh property, dwelling and sale records.")
    parser.add_argument("--zips", nargs="*", help="ZIP codes (default: TARGET_ZIPS)")
    parser.add_argument("--provider", help="Provider key (default: DATA_PROVIDER)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = get_settings()
    upgrade_db()
    zips = args.zips or settings.zips
    provider = get_provider(args.provider)
    with session_factory()() as session:
        run = run_refresh(session, provider, zips)
        log.info("Refresh %s %s: %s", run.id, run.status, run.counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
