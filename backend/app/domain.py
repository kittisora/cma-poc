"""Plain data objects shared by ranking, pricing, reports and the AI agent."""

from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass, field


@dataclass
class SourceRef:
    dataset: str
    record_id: str
    retrieved_at: str | None = None
    url: str | None = None
    kind: str = "public_record"  # public_record | agent_input | workbook | listing

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PropertyFacts:
    pin: str
    address: str | None
    city: str | None = None
    zip: str | None = None
    lat: float | None = None
    lon: float | None = None
    property_type: str = "OTHER"
    land_use: str | None = None
    subdivision: str | None = None
    block: str | None = None  # from the county legal description ("... BLK 7 ...")
    legal_description: str | None = None
    style: str | None = None
    year_built: int | None = None
    effective_year: int | None = None
    year_remodeled: int | None = None
    beds: int | None = None
    full_baths: int | None = None
    half_baths: int | None = None
    above_grade_sf: int | None = None
    rec_room_sf: int | None = None
    fireplaces: int | None = None
    basement: str | None = None
    basement_garage_cars: int | None = None
    garage: bool | None = None  # True = county shows a garage; None = not recorded
    garage_evidence: str | None = None
    condition: str | None = None
    grade: str | None = None
    exterior_wall: str | None = None
    lot_sf: int | None = None
    lot_acres: float | None = None
    dwelling_count: int = 0
    assessed_total: float | None = None
    assessed_tax_year: int | None = None
    tax_year: int | None = None
    total_finished_sf: int | None = None
    total_finished_source: str | None = None
    # fields replaced by the agent's description of a planned / new house (see services.SubjectPlan)
    planned: list[str] = field(default_factory=list)
    agent_inputs: dict = field(default_factory=dict)
    sources: list[SourceRef] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def baths(self) -> float | None:
        if self.full_baths is None and self.half_baths is None:
            return None
        return (self.full_baths or 0) + 0.5 * (self.half_baths or 0)

    @property
    def baths_label(self) -> str | None:
        if self.full_baths is None and self.half_baths is None:
            return None
        return f"{self.full_baths or 0}/{self.half_baths or 0}"

    @property
    def has_basement(self) -> bool | None:
        if self.basement is None:
            return None
        return self.basement.strip().lower() not in ("none", "")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["baths"] = self.baths
        d["baths_label"] = self.baths_label
        d["has_basement"] = self.has_basement
        return d


@dataclass
class SaleFacts:
    sale_id: int
    pin: str
    sale_date: dt.date
    price: int | None
    validity: str | None
    deed_book: str | None = None
    deed_page: str | None = None
    multi_parcel: bool = False
    deed_parcel_count: int = 1
    duplicate_rows: int = 0
    source_object_ids: list = field(default_factory=list)
    source_dataset: str = "Fairfax County Real Estate Sales"
    retrieved_at: str | None = None
    in_latest_source: bool = True
    list_price: int | None = None
    total_finished_sf: int | None = None

    @property
    def deed_ref(self) -> str:
        if self.deed_book and self.deed_page:
            return f"Deed Book {self.deed_book} Page {self.deed_page}"
        return "deed reference not recorded"

    def source_ref(self, url: str | None = None) -> SourceRef:
        ids = ",".join(str(i) for i in self.source_object_ids) or "n/a"
        return SourceRef(
            dataset=self.source_dataset,
            record_id=f"PARID {self.pin} · {self.deed_ref} · sale date {self.sale_date.isoformat()} · OBJECTID {ids}",
            retrieved_at=self.retrieved_at,
            url=url,
        )

    def to_dict(self) -> dict:
        d = asdict(self)
        d["sale_date"] = self.sale_date.isoformat()
        d["deed_ref"] = self.deed_ref
        return d
