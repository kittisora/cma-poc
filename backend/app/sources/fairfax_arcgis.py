"""Fairfax County public property records, read from the county's ArcGIS Online
feature services (Esri hosts the services; Fairfax County publishes the data).

Verified behaviour (see docs/DATA_VERIFICATION.md):
- MAR `PARCEL_PIN` and the tax tables' `PARID` use the same fixed-width,
  space-padded format (e.g. "1022 03  0082A") and join by exact string match.
- Every layer caps a page at 2,000 rows and supports resultOffset paging.
- Sale dates are epoch milliseconds at local midnight (see util.dates).
- The Sales table repeats some transfers with identical values under different
  OBJECTIDs; de-duplication happens in the refresh job.
"""

from __future__ import annotations

import datetime as dt
import logging
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor

import httpx

from ..util.dates import arcgis_ms_to_local_date
from .base import (
    AdditionRow,
    AddressRow,
    DatasetInfo,
    DwellingRow,
    ParcelRow,
    PermitRow,
    ProviderInfo,
    SaleRow,
)

log = logging.getLogger(__name__)

PAGE_SIZE = 2000
PIN_BATCH = 150

DATASETS = {
    "mar": ("Master_Address_Repository", "Master Address Repository (MAR)"),
    "sales": ("Tax_Administration_Real_Estate_Sales_Data", "Real Estate Sales"),
    "dwelling": ("Tax_Administration_Real_Estate_Dwelling_Data", "Real Estate Dwelling"),
    "additions": ("Tax_Administration_Real_Estate_Dwelling_Addition_Data", "Real Estate Dwelling Additions"),
    "parcels": ("Tax_Administration_Real_Estate_Parcels_Data", "Real Estate Parcels"),
    "legal": ("Tax_Administration_Real_Estate_Legal_Data", "Real Estate Legal"),
    "land": ("Tax_Administration_Real_Estate_Land_Data", "Real Estate Land"),
    "values": ("Tax_Administration_Real_Estate_Assessed_Values", "Real Estate Assessed Values"),
    "building_permits": ("Building_Records_PLUS", "Building Permits (PLUS)"),
    "site_records": ("Site_Records_PLUS", "Site and Land Development Records (PLUS)"),
}

TERMS_URL = "https://www.fairfaxcounty.gov/maps/disclaimer"
TERMS_SUMMARY = (
    "Fairfax County GIS disclaimer: data is provided as a public resource without "
    "warranty of accuracy or completeness and is not a legal description. "
    "\"Copyright by Fairfax County. Except as provided herein, all rights are reserved. "
    "Authorization to reproduce material for internal or personal use by any user of "
    "this information is granted by Fairfax County.\" Distribution of client-facing "
    "reports beyond internal use needs the county's permission."
)


def _clean(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


class FairfaxArcGISProvider:
    key = "fairfax_arcgis"
    label = "Fairfax County public records (Department of Tax Administration and MAR, via ArcGIS Online)"

    def __init__(self, base_url: str, token: str = "", timeout: float = 120.0, concurrency: int = 4,
                 client: httpx.Client | None = None):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.concurrency = max(1, concurrency)
        self.client = client or httpx.Client(timeout=timeout, headers={"User-Agent": "cma-app/1.0"})

    # ------------------------------------------------------------------ http
    def layer_url(self, dataset: str) -> str:
        return f"{self.base_url}/{DATASETS[dataset][0]}/FeatureServer/0"

    def _post(self, url: str, params: dict) -> dict:
        data = {"f": "json", **params}
        if self.token:
            data["token"] = self.token
        last: Exception | None = None
        for attempt in range(5):
            try:
                resp = self.client.post(url, data=data)
                resp.raise_for_status()
                body = resp.json()
                if "error" in body:
                    raise RuntimeError(f"ArcGIS error from {url}: {body['error']}")
                return body
            except (httpx.HTTPError, RuntimeError, ValueError) as exc:
                last = exc
                wait = 1.5 * (attempt + 1)
                log.warning("ArcGIS request failed (%s); retrying in %.1fs", exc, wait)
                time.sleep(wait)
        raise RuntimeError(f"ArcGIS request failed after retries: {last}")

    def _query_all(self, dataset: str, where: str, **extra) -> list[dict]:
        """Page through a layer with resultOffset until exceededTransferLimit is false."""
        url = f"{self.layer_url(dataset)}/query"
        features: list[dict] = []
        offset = 0
        while True:
            body = self._post(url, {
                "where": where, "outFields": "*", "orderByFields": "OBJECTID",
                "resultOffset": offset, "resultRecordCount": PAGE_SIZE, **extra,
            })
            page = body.get("features", [])
            features.extend(page)
            offset += len(page)
            if not page or not body.get("exceededTransferLimit"):
                break
        return features

    def _query_pins(self, dataset: str, pins: list[str], field: str = "PARID", **extra) -> list[dict]:
        def chunk(seq: list[str], n: int) -> Iterable[list[str]]:
            for i in range(0, len(seq), n):
                yield seq[i:i + n]

        def one(batch: list[str]) -> list[dict]:
            quoted = ",".join("'" + p.replace("'", "''") + "'" for p in batch)
            return self._query_all(dataset, f"{field} IN ({quoted})", **extra)

        with ThreadPoolExecutor(self.concurrency) as ex:
            results = list(ex.map(one, list(chunk(sorted(set(pins)), PIN_BATCH))))
        return [f for batch in results for f in batch]

    # -------------------------------------------------------------- metadata
    def describe(self) -> ProviderInfo:
        datasets = []
        for key, (service, title) in DATASETS.items():
            last_edit = None
            count = None
            try:
                meta = self._post(self.layer_url(key), {})
                ms = (meta.get("editingInfo") or {}).get("dataLastEditDate") or (
                    meta.get("editingInfo") or {}).get("lastEditDate")
                if ms:
                    last_edit = dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc)
            except Exception as exc:  # metadata is informational only
                log.warning("Could not read metadata for %s: %s", service, exc)
            datasets.append(DatasetInfo(
                key=key, title=f"Fairfax County {title}", url=self.layer_url(key),
                publisher="Fairfax County, Virginia (DIT GIS Division; Department of Tax Administration)",
                update_frequency="Daily", last_edit=last_edit, record_count=count, terms=TERMS_URL,
            ))
        return self.static_info(datasets)

    def static_info(self, datasets: list[DatasetInfo] | None = None) -> ProviderInfo:
        if datasets is None:
            datasets = [DatasetInfo(key=k, title=f"Fairfax County {t}", url=self.layer_url(k),
                                    publisher="Fairfax County, Virginia", update_frequency="Daily",
                                    terms=TERMS_URL) for k, (_, t) in DATASETS.items()]
        return ProviderInfo(
            key=self.key, label=self.label, kind="public_records",
            attribution="Source: Fairfax County, Virginia — Department of Tax Administration real estate "
                        "records and Master Address Repository, published on ArcGIS Online.",
            terms_url=TERMS_URL, terms_summary=TERMS_SUMMARY, datasets=datasets,
        )

    # ------------------------------------------------------------- addresses
    def fetch_addresses(self, zips: list[str]) -> list[AddressRow]:
        zip_list = ",".join(f"'{z}'" for z in zips)
        feats = self._query_all("mar", f"ZIP IN ({zip_list})", outSR=4326)
        rows = []
        for f in feats:
            a = f["attributes"]
            g = f.get("geometry") or {}
            unit = " ".join(x for x in [_clean(a.get("UNIT_TYPE")), _clean(a.get("UNIT_NUMBER"))] if x) or None
            rows.append(AddressRow(
                source_dataset="Fairfax County Master Address Repository",
                source_record_id=str(a.get("SITE_ADDRESS_ID") or a.get("CAD_KEY") or a.get("OBJECTID")),
                source_object_id=a.get("OBJECTID"),
                pin=_clean(a.get("PARCEL_PIN")),
                address_1=_clean(a.get("ADDRESS_1")) or "",
                street_num=_clean(a.get("FULL_STREET_NUM")),
                street_name=_clean(a.get("FULL_NAME")),
                unit=unit,
                city=_clean(a.get("CITY")), state=_clean(a.get("STATE")), zip=_clean(a.get("ZIP")),
                status=_clean(a.get("ADDRESS_STATUS")), address_type=_clean(a.get("ADDRESS_TYPE")),
                jurisdiction=_clean(a.get("JURISDICTION")), subdivision=_clean(a.get("SUBDIVISION")),
                lat=g.get("y"), lon=g.get("x"), raw=a,
            ))
        return rows

    def fetch_parcel_pins(self, zips: list[str]) -> set[str]:
        """Parcels whose legal (tax) address is in the ZIPs, including ones without a MAR point."""
        zip_list = ",".join(f"'{z}'" for z in zips)
        feats = self._query_all("legal", f"ZIP1 IN ({zip_list})")
        return {f["attributes"]["PARID"] for f in feats if f["attributes"].get("PARID")}

    # --------------------------------------------------------------- parcels
    def fetch_parcels(self, pins: list[str]) -> list[ParcelRow]:
        parcels = {f["attributes"]["PARID"]: f["attributes"] for f in self._query_pins("parcels", pins)}
        legal = {f["attributes"]["PARID"]: f["attributes"] for f in self._query_pins("legal", pins)}
        values = {f["attributes"]["PARID"]: f["attributes"] for f in self._query_pins("values", pins)}
        land: dict[str, list[dict]] = {}
        for f in self._query_pins("land", pins):
            land.setdefault(f["attributes"]["PARID"], []).append(f["attributes"])

        rows = []
        for pin in sorted(set(parcels) | set(legal) | set(values) | set(land)):
            p, lg, v, ld = parcels.get(pin, {}), legal.get(pin, {}), values.get(pin, {}), land.get(pin, [])
            lot_sf = sum(x.get("SF") or 0 for x in ld) or (lg.get("SQFT") or None)
            lot_acres = sum(x.get("ACRES") or 0 for x in ld) or (lg.get("ACRES") or None)
            legal_desc = " ".join(x for x in [_clean(lg.get("LEGAL1")), _clean(lg.get("LEGAL2")),
                                              _clean(lg.get("LEGAL3"))] if x) or None
            legal_addr = " ".join(str(x) for x in [lg.get("ADRNO"), _clean(lg.get("ADRADD")),
                                                    _clean(lg.get("ADRDIR")), _clean(lg.get("ADRSTR")),
                                                    _clean(lg.get("ADRSUF"))] if x) or None
            rows.append(ParcelRow(
                pin=pin, legal_zip=_clean(lg.get("ZIP1")), land_use=_clean(p.get("LUC_DESC")),
                livable_units=p.get("LIVUNIT"), zoning=_clean(p.get("ZONING_DESC")),
                lot_sf=int(lot_sf) if lot_sf else None,
                lot_acres=round(lot_acres, 4) if lot_acres else None,
                legal_description=legal_desc, legal_address=legal_addr,
                assessed_land=v.get("APRLAND"), assessed_building=v.get("APRBLDG"),
                assessed_total=v.get("APRTOT"), assessed_tax_year=v.get("TAXYR"),
                tax_year=p.get("TAXYR") or lg.get("TAXYR"),
                raw={"parcels": p, "legal": lg, "values": v, "land": ld},
            ))
        return rows

    def fetch_dwellings(self, pins: list[str]) -> list[DwellingRow]:
        rows = []
        for f in self._query_pins("dwelling", pins):
            a = f["attributes"]
            rows.append(DwellingRow(
                pin=a["PARID"], source_object_id=a.get("OBJECTID"), style=_clean(a.get("STYLE_DESC")),
                year_built=a.get("YRBLT") or None, effective_year=a.get("EFFYR") or None,
                year_remodeled=a.get("YRREMOD") or None, beds=a.get("RMBED"),
                full_baths=a.get("FIXBATH"), half_baths=a.get("FIXHALF"),
                above_grade_sf=a.get("SFLA") or None, rec_room_sf=a.get("RECROMAREA") or None,
                fireplaces=a.get("WBFP_PF"), basement_garage_cars=a.get("BSMTCAR"),
                basement=_clean(a.get("BSMT_DESC")), basement_type=_clean(a.get("USER9_DESC")),
                basement_beds_dens=_clean(a.get("USER10")), grade=_clean(a.get("GRADE_DESC")),
                condition=_clean(a.get("CDU_DESC")), exterior_wall=_clean(a.get("EXTWALL_DESC")),
                heating=_clean(a.get("HEAT_DESC")), roof=_clean(a.get("USER13_DESC")),
                model_name=_clean(a.get("USER6")), raw=a,
            ))
        return rows

    def fetch_additions(self, pins: list[str]) -> list[AdditionRow]:
        rows = []
        for f in self._query_pins("additions", pins):
            a = f["attributes"]
            rows.append(AdditionRow(
                pin=a["PARID"], line=a.get("LLINE"), area_sf=a.get("AREA"),
                lower_desc=_clean(a.get("LOWER_DESC")), first_desc=_clean(a.get("FIRST_DESC")),
                second_desc=_clean(a.get("SECOND_DESC")), third_desc=_clean(a.get("THIRD_DESC")),
                source_object_id=a.get("OBJECTID"), raw=a,
            ))
        return rows

    def fetch_permits(self, pins: list[str]) -> list[PermitRow]:
        """Building permits and site records from PLUS (the county's permitting system) for these parcels."""
        rows = []
        for kind, dataset in (("building", "building_permits"), ("site", "site_records")):
            for f in self._query_pins(dataset, pins, field="PARCEL_ID", returnGeometry="false"):
                a = f["attributes"]
                if not _clean(a.get("RECORDID")) or (a.get("PUBLIC_VIEW") or "Yes").lower() == "no":
                    continue
                d = arcgis_ms_to_local_date
                rows.append(PermitRow(
                    kind=kind, record_id=a["RECORDID"].strip(), pin=_clean(a.get("PARCEL_ID")),
                    app_type=_clean(a.get("APPTYPEALIAS")), project_name=_clean(a.get("PROJECT_NAME")),
                    status=_clean(a.get("RECORD_STATUS")), status_date=d(a.get("RECORD_STATUS_DATE")),
                    submitted_date=d(a.get("SUBMITTED_DATE")),
                    issued_date=d(a.get("ISSUED_DATE") if kind == "building" else a.get("APPROVED_DATE")),
                    closed_date=d(a.get("CLOSED_DATE")), address=_clean(a.get("ADDRESS_1")),
                    zip=_clean(a.get("ZIP_CODE")), link_url=_clean(a.get("LINK_URL")), raw=a,
                ))
        return rows

    def fetch_sales(self, pins: list[str]) -> list[SaleRow]:
        rows = []
        for f in self._query_pins("sales", pins):
            a = f["attributes"]
            rows.append(SaleRow(
                source_dataset="Fairfax County Real Estate Sales", source_object_id=a.get("OBJECTID"),
                pin=a["PARID"], sale_date=arcgis_ms_to_local_date(a.get("SALEDT")), price=a.get("PRICE"),
                deed_book=_clean(a.get("BOOK")), deed_page=_clean(a.get("PAGE")),
                validity=_clean(a.get("SALEVAL_DESC")), tax_year=a.get("TAXYR"), raw=a,
            ))
        return rows
