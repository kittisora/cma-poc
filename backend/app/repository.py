"""Database reads that turn stored provider rows into PropertyFacts / SaleFacts."""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from collections.abc import Iterable

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from .domain import PropertyFacts, SaleFacts, SourceRef
from .models import (
    Address,
    AppSetting,
    Dwelling,
    DwellingAddition,
    Parcel,
    PropertyInput,
    RefreshRun,
    Sale,
    utcnow,
)
from .sources.fairfax_arcgis import DATASETS
from .util.geo import bounding_box
from .util.text import search_tokens

ARCGIS_BASE = "https://services1.arcgis.com/ioennV6PpG5Xodq0/ArcGIS/rest/services"


def layer_url(key: str) -> str:
    return f"{ARCGIS_BASE}/{DATASETS[key][0]}/FeatureServer/0"


def _iso(ts: dt.datetime | None) -> str | None:
    return ts.isoformat() if ts else None


# ------------------------------------------------------------------ search
def search_addresses(session: Session, query: str, zip_code: str | None = None, limit: int = 15) -> list[dict]:
    tokens = search_tokens(query)
    stmt = select(Address, Parcel).join(Parcel, Parcel.pin == Address.pin, isouter=True).where(
        Address.status == "Current")
    if zip_code:
        stmt = stmt.where(Address.zip == zip_code)
    for tok in tokens:
        if tok.isdigit():
            # match the house number exactly at the start, or a unit/ZIP elsewhere
            stmt = stmt.where(or_(Address.search_text.like(f"{tok} %"), Address.search_text.like(f"% {tok} %"),
                                  Address.search_text.like(f"% {tok}")))
        else:
            stmt = stmt.where(Address.search_text.like(f"%{tok}%"))
    stmt = stmt.order_by(Address.street_name, func.length(Address.street_num), Address.street_num,
                         Address.unit).limit(limit)
    out = []
    for a, p in session.execute(stmt):
        out.append({
            "pin": a.pin, "address": a.address_1, "city": a.city,
            "zip": a.zip, "lat": a.lat, "lon": a.lon,
            "property_type": p.property_type if p else None, "land_use": p.land_use if p else None,
            "address_id": a.source_record_id,
        })
    return out


# ---------------------------------------------------------------- property
def _garage_from(additions: list[DwellingAddition], dwelling: Dwelling | None) -> tuple[bool | None, str | None]:
    found = []
    for a in additions:
        for desc in (a.lower_desc, a.first_desc, a.second_desc, a.third_desc):
            if desc and ("GARAGE" in desc.upper() or "CARPORT" in desc.upper()):
                found.append(f"{desc.title()}{f' ({a.area_sf:,} sf)' if a.area_sf else ''}")
    if dwelling and dwelling.basement_garage_cars:
        found.append(f"Basement garage ({dwelling.basement_garage_cars}-car)")
    if found:
        return True, "; ".join(dict.fromkeys(found))
    return None, None


def load_inputs(session: Session, pins: Iterable[str]) -> dict[str, dict[str, dict]]:
    pins = list(set(pins))
    out: dict[str, dict[str, dict]] = defaultdict(dict)
    for i in range(0, len(pins), 900):
        for row in session.scalars(select(PropertyInput).where(PropertyInput.pin.in_(pins[i:i + 900]))):
            out[row.pin][row.field] = {"value": row.value.get("value"), "note": row.note,
                                       "updated_at": _iso(row.updated_at), "entered_by": row.entered_by}
    return out


def build_facts(parcel: Parcel, dwellings: list[Dwelling], additions: list[DwellingAddition],
                address: Address | None, inputs: dict[str, dict]) -> PropertyFacts:
    primary = max(dwellings, key=lambda d: (d.above_grade_sf or 0, d.year_built or 0)) if dwellings else None
    garage, garage_ev = _garage_from(additions, primary)
    f = PropertyFacts(
        pin=parcel.pin, address=parcel.primary_address, city=address.city if address else None,
        zip=parcel.zip, lat=parcel.lat, lon=parcel.lon, property_type=parcel.property_type,
        land_use=parcel.land_use, subdivision=address.subdivision if address else None,
        legal_description=parcel.legal_description, lot_sf=parcel.lot_sf, lot_acres=parcel.lot_acres,
        assessed_total=parcel.assessed_total, assessed_tax_year=parcel.assessed_tax_year,
        tax_year=parcel.tax_year, dwelling_count=len(dwellings), garage=garage, garage_evidence=garage_ev,
    )
    if primary:
        for attr in ("style", "year_built", "effective_year", "year_remodeled", "beds", "full_baths",
                     "half_baths", "above_grade_sf", "rec_room_sf", "fireplaces", "basement",
                     "basement_garage_cars", "condition", "grade", "exterior_wall"):
            setattr(f, attr, getattr(primary, attr))
    retrieved = _iso(parcel.retrieved_at)
    f.sources.append(SourceRef("Fairfax County Real Estate Parcels / Legal / Land / Assessed Values",
                               f"PARID {parcel.pin} (tax year {parcel.tax_year})", retrieved,
                               layer_url("parcels")))
    if primary:
        f.sources.append(SourceRef("Fairfax County Real Estate Dwelling",
                                   f"PARID {parcel.pin} · OBJECTID {primary.source_object_id}",
                                   _iso(primary.retrieved_at), layer_url("dwelling")))
    if address:
        f.sources.append(SourceRef("Fairfax County Master Address Repository",
                                   f"SITE_ADDRESS_ID {address.source_record_id}", _iso(address.retrieved_at),
                                   layer_url("mar")))
    if len(dwellings) > 1:
        f.notes.append(f"County records list {len(dwellings)} dwellings on this parcel; the largest "
                       f"({primary.above_grade_sf or 0:,} sf above grade) is used.")
    if not dwellings:
        f.notes.append("No dwelling record on file (vacant land or non-residential).")
    if parcel.lat is None:
        f.notes.append("No mapped address point; distance cannot be measured.")
    # agent-entered facts
    f.agent_inputs = inputs
    tf = inputs.get("total_finished_sf")
    if tf and tf.get("value"):
        f.total_finished_sf = int(tf["value"])
        f.total_finished_source = "agent input" + (f" ({tf['note']})" if tf.get("note") else "")
        f.sources.append(SourceRef("Agent input", f"total finished sq ft for PARID {parcel.pin}",
                                   tf.get("updated_at"), None, kind="agent_input"))
    return f


def get_properties(session: Session, pins: Iterable[str]) -> dict[str, PropertyFacts]:
    pins = list(set(pins))
    parcels: dict[str, Parcel] = {}
    dwell: dict[str, list[Dwelling]] = defaultdict(list)
    adds: dict[str, list[DwellingAddition]] = defaultdict(list)
    addrs: dict[str, Address] = {}
    for i in range(0, len(pins), 900):
        batch = pins[i:i + 900]
        parcels.update({p.pin: p for p in session.scalars(select(Parcel).where(Parcel.pin.in_(batch)))})
        for d in session.scalars(select(Dwelling).where(Dwelling.pin.in_(batch))):
            dwell[d.pin].append(d)
        for a in session.scalars(select(DwellingAddition).where(DwellingAddition.pin.in_(batch))):
            adds[a.pin].append(a)
        for a in session.scalars(select(Address).where(Address.pin.in_(batch), Address.status == "Current")
                                 .order_by(Address.unit.is_not(None), Address.address_1)):
            addrs.setdefault(a.pin, a)
    inputs = load_inputs(session, pins)
    return {pin: build_facts(p, dwell.get(pin, []), adds.get(pin, []), addrs.get(pin), inputs.get(pin, {}))
            for pin, p in parcels.items()}


def get_property(session: Session, pin: str) -> PropertyFacts | None:
    return get_properties(session, [pin]).get(pin)


def to_sale_facts(s: Sale) -> SaleFacts:
    return SaleFacts(
        sale_id=s.id, pin=s.pin, sale_date=s.sale_date, price=s.price, validity=s.validity,
        deed_book=s.deed_book, deed_page=s.deed_page, multi_parcel=s.multi_parcel,
        deed_parcel_count=s.deed_parcel_count, duplicate_rows=s.duplicate_rows,
        source_object_ids=list(s.source_object_ids or []), source_dataset=s.source_dataset,
        retrieved_at=_iso(s.last_retrieved_at), in_latest_source=s.in_latest_source,
        list_price=s.list_price, total_finished_sf=s.total_finished_sf,
    )


def get_sale_history(session: Session, pin: str) -> list[SaleFacts]:
    rows = session.scalars(select(Sale).where(Sale.pin == pin).order_by(Sale.sale_date.desc(), Sale.id.desc()))
    return [to_sale_facts(s) for s in rows]


def get_sales_by_ids(session: Session, ids: Iterable[int]) -> dict[int, SaleFacts]:
    ids = list(set(ids))
    if not ids:
        return {}
    return {s.id: to_sale_facts(s) for s in session.scalars(select(Sale).where(Sale.id.in_(ids)))}


def get_candidate_sales(session: Session, lat: float, lon: float, radius_miles: float,
                        start_date: dt.date) -> list[tuple[SaleFacts, PropertyFacts]]:
    """All recorded transfers on parcels inside a bounding box from `start_date` onward.

    No validity, date-ceiling or price filtering happens here: the comp engine
    applies every rule itself so it can explain what each one removed.
    """
    min_lat, max_lat, min_lon, max_lon = bounding_box(lat, lon, radius_miles)
    stmt = (select(Sale).join(Parcel, Parcel.pin == Sale.pin)
            .where(and_(Sale.sale_date >= start_date, Parcel.lat.between(min_lat, max_lat),
                        Parcel.lon.between(min_lon, max_lon))))
    sales = list(session.scalars(stmt))
    props = get_properties(session, {s.pin for s in sales})
    return [(to_sale_facts(s), props[s.pin]) for s in sales if s.pin in props]


# ----------------------------------------------------------- agent inputs
def set_input(session: Session, pin: str, field_name: str, value, note: str | None = None,
              entered_by: str | None = None) -> None:
    row = session.scalar(select(PropertyInput).where(PropertyInput.pin == pin, PropertyInput.field == field_name))
    if value in (None, ""):
        if row:
            session.delete(row)
        session.commit()
        return
    if row is None:
        row = PropertyInput(pin=pin, field=field_name, value={"value": value})
        session.add(row)
    row.value, row.note, row.entered_by, row.updated_at = {"value": value}, note, entered_by, utcnow()
    session.commit()


# ----------------------------------------------------------------- status
def data_status(session: Session) -> dict:
    last = session.scalar(select(RefreshRun).where(RefreshRun.status == "succeeded")
                          .order_by(RefreshRun.finished_at.desc()))
    latest_sale = session.scalar(select(func.max(Sale.sale_date)))
    return {
        "last_refresh": None if last is None else {
            "id": last.id, "provider": last.provider, "zips": last.zips,
            "started_at": _iso(last.started_at), "finished_at": _iso(last.finished_at), "counts": last.counts,
        },
        "parcels": session.scalar(select(func.count()).select_from(Parcel)) or 0,
        "sales": session.scalar(select(func.count()).select_from(Sale)) or 0,
        "latest_sale_date": latest_sale.isoformat() if latest_sale else None,
    }


def get_setting(session: Session, key: str) -> dict | None:
    row = session.get(AppSetting, key)
    return row.value if row else None


def put_setting(session: Session, key: str, value: dict) -> None:
    row = session.get(AppSetting, key)
    if row is None:
        session.add(AppSetting(key=key, value=value))
    else:
        row.value, row.updated_at = value, utcnow()
    session.commit()
