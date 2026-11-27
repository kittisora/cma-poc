"""Database reads that turn stored provider rows into PropertyFacts / SaleFacts."""

from __future__ import annotations

import datetime as dt
import re
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
    Permit,
    PropertyInput,
    RefreshRun,
    Sale,
    utcnow,
)
from .sources.fairfax_arcgis import DATASETS
from .util.dates import subtract_months, today_local
from .util.geo import bounding_box
from .util.text import parse_block, parse_lot, search_tokens

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


# ------------------------------------------------- subdivision / block / street
# Blocks come from the county legal description (util.text.parse_block); the Master
# Address Repository's own SUBDIVISION_BLOCK is almost never filled in.
_area_cache: dict = {"key": None, "rows": []}


def _natural_key(s: str) -> tuple:
    return tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in re.findall(r"\d+|\D+", s))


def _area_rows(session: Session) -> list[dict]:
    """Every current address with its subdivision, block and street, cached until the next refresh."""
    key = (id(session.get_bind()), session.scalar(select(func.max(RefreshRun.id))),
           session.scalar(select(func.count()).select_from(Address)))
    if _area_cache["key"] == key:
        return _area_cache["rows"]
    stmt = (select(Address.pin, Address.address_1, Address.street_num, Address.street_name, Address.unit,
                   Address.city, Address.zip, Address.lat, Address.lon, Address.subdivision,
                   Address.source_record_id, Parcel.legal_description, Parcel.property_type, Parcel.land_use)
            .join(Parcel, Parcel.pin == Address.pin, isouter=True).where(Address.status == "Current"))
    rows = []
    for r in session.execute(stmt):
        rows.append({
            "pin": r.pin, "address": r.address_1, "street_num": r.street_num or "", "street": r.street_name,
            "unit": r.unit or "", "city": r.city, "zip": r.zip, "lat": r.lat, "lon": r.lon,
            "subdivision": (r.subdivision or "").strip() or None, "block": parse_block(r.legal_description),
            "lot": parse_lot(r.legal_description), "legal_description": r.legal_description,
            "property_type": r.property_type, "land_use": r.land_use, "address_id": r.source_record_id,
        })
    _area_cache.update(key=key, rows=rows)
    return rows


def _area_filter(rows: list[dict], subdivision: str | None, block: str | None,
                 street: str | list[str] | None, zip_code: str | None) -> list[dict]:
    """Filter by subdivision, block, one or more streets, and ZIP (each optional)."""
    def norm(x: str | None) -> str | None:
        return x.strip().upper() if x and x.strip() else None
    sub, blk = norm(subdivision), norm(block)
    streets = {s for s in (norm(x) for x in ([street] if isinstance(street, str) else (street or []))) if s}
    return [r for r in rows
            if (not sub or (r["subdivision"] or "").upper() == sub)
            and (not blk or (r["block"] or "") == blk)
            and (not streets or (r["street"] or "").upper() in streets)
            and (not zip_code or r["zip"] == zip_code)]


def _counts(rows: list[dict], field: str) -> list[dict]:
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        if r[field]:
            counts[r[field]] += 1
    return [{"name": k, "count": counts[k]} for k in sorted(counts, key=_natural_key)]


def search_areas(session: Session, subdivision: str | None = None, block: str | None = None,
                 zip_code: str | None = None) -> dict:
    """Choices for the three search filters. Blocks narrow to the subdivision; streets to both."""
    rows = _area_rows(session)
    in_zip = _area_filter(rows, None, None, None, zip_code)
    in_sub = _area_filter(in_zip, subdivision, None, None, None)
    in_block = _area_filter(in_sub, None, block, None, None)
    return {"subdivisions": _counts(in_zip, "subdivision"),
            "blocks": _counts(in_sub, "block") if subdivision else [],
            "streets": _counts(in_block, "street")}


def search_by_area(session: Session, subdivision: str | None = None, block: str | None = None,
                   street: str | list[str] | None = None, zip_code: str | None = None, limit: int = 2000) -> dict:
    found = _area_filter(_area_rows(session), subdivision, block, street, zip_code)
    stages = permit_stage_by_pin(session)
    found.sort(key=lambda r: (r["street"] or "", _natural_key(r["street_num"]), _natural_key(r["unit"])))
    keep = ("pin", "address", "city", "zip", "lat", "lon", "property_type", "land_use", "address_id",
            "subdivision", "block", "lot", "street")
    return {"total": len(found),
            "results": [{**{k: r[k] for k in keep}, "permit_stage": stages.get(r["pin"])} for r in found[:limit]]}


# ------------------------------------------------------------------ permits
PERMIT_STAGES = {
    "active": "Issued / under construction",
    "pending": "In review (not yet issued)",
    "completed": "Completed",
    "stale": "Older than 3 years, no closure recorded",
    "inactive": "Expired, withdrawn or void",
}
ACTIVE_YEARS = 3  # an issued/approved record with no closure after this long is not treated as current work
_INACTIVE = ("expired", "withdrawn", "void", "cancel", "denied", "disapproved", "refund")
_DONE = ("closed", "final", "complete", "recorded", "occupancy")


def permit_stage(kind: str, status: str | None, issued: dt.date | None, closed: dt.date | None,
                 submitted: dt.date | None = None, today: dt.date | None = None) -> str:
    """Plain stage of a permit or site record, from its status in the permitting system.

    Many old records were approved decades ago and never closed in the system, so an open record
    older than ACTIVE_YEARS is reported as "stale" rather than as current construction.
    """
    s = (status or "").strip().lower()
    if any(k in s for k in _INACTIVE):
        return "inactive"
    if closed or any(k in s for k in _DONE):
        return "completed"
    started = issued or submitted
    if started and started < subtract_months(today or today_local(), 12 * ACTIVE_YEARS):
        return "stale"
    if kind == "building":
        return "active" if issued or s.startswith("issued") else "pending"
    # site records: an approved / bonded plan means work may proceed
    return "active" if issued or s.startswith(("approved", "bond", "issued")) else "pending"


def is_new_construction(app_type: str | None) -> bool:
    t = (app_type or "").lower()
    return t.endswith(" new") or "infill lot grading" in t or "subdivision" in t or "record plat" in t


def permit_dict(p: Permit) -> dict:
    return {
        "kind": p.kind, "record_id": p.record_id, "pin": p.pin, "type": p.app_type, "project": p.project_name,
        "status": p.status, "stage": permit_stage(p.kind, p.status, p.issued_date, p.closed_date, p.submitted_date),
        "new_construction": is_new_construction(p.app_type), "address": p.address, "zip": p.zip,
        "submitted": _d(p.submitted_date), "issued": _d(p.issued_date), "closed": _d(p.closed_date),
        "status_date": _d(p.status_date), "link": p.link_url, "in_latest_source": p.in_latest_source,
    }


def _d(v: dt.date | None) -> str | None:
    return v.isoformat() if v else None


def _permit_sort(p: dict) -> tuple:
    return (p["status_date"] or p["submitted"] or "", p["record_id"])


def permits_for_pins(session: Session, pins: Iterable[str]) -> dict[str, list[dict]]:
    pins = list(set(p for p in pins if p))
    out: dict[str, list[dict]] = defaultdict(list)
    for i in range(0, len(pins), 900):
        for p in session.scalars(select(Permit).where(Permit.pin.in_(pins[i:i + 900]))):
            out[p.pin].append(permit_dict(p))
    for v in out.values():
        v.sort(key=_permit_sort, reverse=True)
    return out


def search_permits(session: Session, subdivision: str | None = None, block: str | None = None,
                   streets: list[str] | None = None, zip_code: str | None = None, stage: str | None = None,
                   kind: str | None = None, new_only: bool = False, since: dt.date | None = None,
                   limit: int = 2000) -> dict:
    """Permits in an area (subdivision / block / streets / ZIP), joined to the address and its location."""
    area = _area_filter(_area_rows(session), subdivision, block, streets, zip_code)
    by_pin: dict[str, dict] = {}
    for r in area:
        by_pin.setdefault(r["pin"], r)
    filtered_area = bool(subdivision or block or streets or zip_code)
    stmt = select(Permit)
    if kind:
        stmt = stmt.where(Permit.kind == kind)
    if since:
        stmt = stmt.where(or_(Permit.status_date >= since, Permit.submitted_date >= since))
    rows = []
    for p in session.scalars(stmt):
        a = by_pin.get(p.pin)
        if filtered_area and a is None:
            continue
        d = permit_dict(p)
        if stage and d["stage"] != stage:
            continue
        if new_only and not d["new_construction"]:
            continue
        d.update({"lat": a["lat"] if a else None, "lon": a["lon"] if a else None,
                  "subdivision": a["subdivision"] if a else None, "block": a["block"] if a else None,
                  "street": a["street"] if a else None, "site_address": a["address"] if a else d["address"]})
        rows.append(d)
    rows.sort(key=_permit_sort, reverse=True)
    summary = {"by_stage": defaultdict(int), "by_type": defaultdict(int), "new_construction": defaultdict(int),
               "parcels": len({r["pin"] for r in rows})}
    for r in rows:
        summary["by_stage"][r["stage"]] += 1
        summary["by_type"][r["type"] or "Other"] += 1
        if r["new_construction"]:
            summary["new_construction"][r["stage"]] += 1
    summary = {k: (dict(sorted(v.items(), key=lambda x: -x[1])) if isinstance(v, dict) else v)
               for k, v in summary.items()}
    return {"total": len(rows), "results": rows[:limit], "summary": summary, "stages": PERMIT_STAGES}


def permit_stage_by_pin(session: Session) -> dict[str, str]:
    """The most significant open stage per parcel (active beats pending); used to badge search results."""
    out: dict[str, str] = {}
    for p in session.scalars(select(Permit).where(Permit.in_latest_source.is_(True))):
        st = permit_stage(p.kind, p.status, p.issued_date, p.closed_date, p.submitted_date)
        if st == "active" or (st == "pending" and out.get(p.pin) != "active"):
            out[p.pin] = st
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
        block=parse_block(parcel.legal_description), legal_description=parcel.legal_description, lot_sf=parcel.lot_sf, lot_acres=parcel.lot_acres,
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


def get_candidate_sales_in_subdivision(session: Session, subdivision: str,
                                       start_date: dt.date) -> list[tuple[SaleFacts, PropertyFacts]]:
    """All recorded transfers from `start_date` onward on parcels addressed in `subdivision`."""
    pins = select(Address.pin).where(Address.status == "Current",
                                      func.upper(func.trim(Address.subdivision)) == subdivision.strip().upper())
    sales = list(session.scalars(select(Sale).where(Sale.sale_date >= start_date, Sale.pin.in_(pins))))
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


def dwelling_choices(session: Session) -> dict:
    """County values offered for describing a planned house, most common first."""
    def common(col) -> list[str]:
        rows = session.execute(select(col, func.count()).where(col.is_not(None)).group_by(col)
                               .order_by(func.count().desc()))
        return [v for v, n in rows if n >= 5]
    return {"styles": common(Dwelling.style), "basements": common(Dwelling.basement),
            "conditions": ["Poor", "Fair", "Average", "Average Plus", "Good", "Very Good", "Excellent"]}


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
