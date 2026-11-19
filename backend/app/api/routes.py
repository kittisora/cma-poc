from __future__ import annotations

import datetime as dt
import re
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import repository as repo
from ..agent.agent import AgentUnavailable, generate_narrative, run_agent
from ..agent.template import template_narrative
from ..comps.engine import OPTIONAL_VALIDITY, CompCriteria
from ..config import get_settings
from ..db import get_session
from ..models import SavedCMA, utcnow
from ..reports.model import Branding, FiguresChanged, ReportRequest, build_report, public_model
from ..reports.render_docx import render_docx
from ..reports.render_pdf import render_pdf
from ..services import CMARequest, NotFound, run_cma
from ..sources.registry import get_provider
from ..valuation.workbook import regression_report
from ..fieldmap import FIELD_MAP
from ..util.dates import today_local

router = APIRouter(prefix="/api")


def default_branding(session: Session) -> Branding:
    saved = repo.get_setting(session, "branding")
    if saved:
        return Branding(**saved)
    s = get_settings()
    return Branding(company=s.brand_company, agent_name=s.brand_agent_name, phone=s.brand_phone,
                    email=s.brand_email, primary_color=s.brand_color)


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/meta")
def meta(session: Session = Depends(get_session)):
    s = get_settings()
    info = get_provider().static_info()
    return {
        "app": "CMA", "target_zips": s.zips, "ai_enabled": s.ai_enabled, "ai_model": s.ai_model,
        "ai_provider": s.active_ai_provider,
        "data": repo.data_status(session),
        "provider": {"key": info.key, "label": info.label, "kind": info.kind, "attribution": info.attribution,
                     "terms_url": info.terms_url, "terms_summary": info.terms_summary,
                     "datasets": [{"key": d.key, "title": d.title, "url": d.url} for d in info.datasets]},
        "default_criteria": CompCriteria().model_dump(),
        "validity_options": {"default": CompCriteria().allowed_validity, "optional": OPTIONAL_VALIDITY},
        "today": today_local().isoformat(),
        "field_map": FIELD_MAP,
    }


@router.get("/search")
def search(q: str = Query(..., min_length=2), zip: str | None = None, limit: int = 15,
           session: Session = Depends(get_session)):
    t0 = time.perf_counter()
    results = repo.search_addresses(session, q, zip or None, min(limit, 50))
    return {"results": results, "timing_ms": round((time.perf_counter() - t0) * 1000, 1)}


@router.get("/properties/{pin}")
def property_detail(pin: str, session: Session = Depends(get_session)):
    facts = repo.get_property(session, pin)
    if facts is None:
        raise HTTPException(404, f"Parcel {pin!r} not found")
    return {"facts": facts.to_dict(), "sale_history": [s.to_dict() for s in repo.get_sale_history(session, pin)]}


class InputBody(BaseModel):
    field: str = Field(pattern=r"^(total_finished_sf|condition_notes|garage_notes)$")
    value: int | float | str | None = None
    note: str | None = None
    entered_by: str | None = None


@router.put("/properties/{pin}/inputs")
def put_input(pin: str, body: InputBody, session: Session = Depends(get_session)):
    if repo.get_property(session, pin) is None:
        raise HTTPException(404, f"Parcel {pin!r} not found")
    value = body.value
    if body.field == "total_finished_sf" and value not in (None, ""):
        try:
            value = int(float(value))
        except (TypeError, ValueError):
            raise HTTPException(422, "total_finished_sf must be a number")
        if not 100 <= value <= 30000:
            raise HTTPException(422, "total_finished_sf must be between 100 and 30,000")
    repo.set_input(session, pin, body.field, value, body.note, body.entered_by)
    return {"ok": True, "inputs": repo.load_inputs(session, [pin]).get(pin, {})}


@router.post("/cma/analyze")
def analyze(req: CMARequest, session: Session = Depends(get_session)):
    try:
        return run_cma(session, req)
    except NotFound as exc:
        raise HTTPException(404, str(exc))


@router.get("/workbook/regression")
def workbook(subject: str = "1009 New", finished_sf: float | None = None, garage_adjustment: float | None = None,
             appreciation_pct: float = 0.0):
    try:
        return regression_report(subject, finished_sf, garage_adjustment, appreciation_pct)
    except KeyError:
        raise HTTPException(404, f"Unknown workbook subject {subject!r}")


# ------------------------------------------------------------------ reports
def _report(session: Session, req: ReportRequest) -> dict:
    try:
        return build_report(session, req, default_branding(session))
    except NotFound as exc:
        raise HTTPException(404, str(exc))
    except FiguresChanged as exc:
        raise HTTPException(409, str(exc))


@router.post("/reports/preview")
def report_preview(req: ReportRequest, session: Session = Depends(get_session)):
    return public_model(_report(session, req))


def _filename(report: dict, ext: str) -> str:
    addr = report["title"].split("—")[-1].strip()
    slug = re.sub(r"[^A-Za-z0-9]+", "-", addr).strip("-")[:60] or "report"
    return f"CMA-{slug}-{report['valuation_date']}.{ext}"


@router.post("/reports/pdf")
def report_pdf(req: ReportRequest, session: Session = Depends(get_session)):
    r = _report(session, req)
    return Response(render_pdf(r), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{_filename(r, "pdf")}"',
                             "X-CMA-Fingerprint": r["fingerprint"]})


@router.post("/reports/docx")
def report_docx(req: ReportRequest, session: Session = Depends(get_session)):
    r = _report(session, req)
    return Response(render_docx(r),
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f'attachment; filename="{_filename(r, "docx")}"',
                             "X-CMA-Fingerprint": r["fingerprint"]})


@router.get("/settings/branding")
def get_branding(session: Session = Depends(get_session)):
    return default_branding(session).model_dump()


@router.put("/settings/branding")
def put_branding(b: Branding, session: Session = Depends(get_session)):
    if b.logo_data_url and len(b.logo_data_url) > 1_500_000:
        raise HTTPException(413, "Logo is too large (limit about 1 MB).")
    repo.put_setting(session, "branding", b.model_dump())
    return b.model_dump()


# -------------------------------------------------------------------- agent
class ChatBody(BaseModel):
    cma: CMARequest
    messages: list[dict]


@router.post("/agent/chat")
def agent_chat(body: ChatBody, session: Session = Depends(get_session)):
    if not get_settings().ai_enabled:
        raise HTTPException(503, "AI assistant is not configured. Set OPENAI_API_KEY on the server.")
    try:
        return run_agent(session, body.cma, body.messages[-20:])
    except NotFound as exc:
        raise HTTPException(404, str(exc))
    except AgentUnavailable as exc:
        raise HTTPException(503, str(exc))


@router.post("/agent/narrative")
def agent_narrative(cma: CMARequest, prefer_ai: bool = True, session: Session = Depends(get_session)):
    try:
        if prefer_ai and get_settings().ai_enabled:
            try:
                return generate_narrative(session, cma)
            except AgentUnavailable as exc:
                result = run_cma(session, cma, with_hints=False)
                return {"narrative": template_narrative(result), "generated_by": "template",
                        "note": f"AI unavailable ({exc}); template narrative used."}
        result = run_cma(session, cma, with_hints=False)
        return {"narrative": template_narrative(result), "generated_by": "template"}
    except NotFound as exc:
        raise HTTPException(404, str(exc))


# --------------------------------------------------------------- saved CMAs
class SaveBody(BaseModel):
    title: str
    state: dict
    id: str | None = None


@router.post("/cma/saved")
def save_cma(body: SaveBody, session: Session = Depends(get_session)):
    cma = CMARequest(**body.state.get("cma", {}))
    row = session.get(SavedCMA, body.id) if body.id else None
    if row is None:
        row = SavedCMA(id=str(uuid.uuid4()), title=body.title, subject_pin=cma.subject_pin,
                       valuation_date=cma.valuation_date or today_local(), state=body.state)
        session.add(row)
    else:
        row.title, row.state, row.updated_at = body.title, body.state, utcnow()
        row.valuation_date = cma.valuation_date or row.valuation_date
    session.commit()
    return {"id": row.id, "title": row.title}


@router.get("/cma/saved")
def list_saved(session: Session = Depends(get_session)):
    rows = session.scalars(select(SavedCMA).order_by(SavedCMA.updated_at.desc()).limit(50))
    return [{"id": r.id, "title": r.title, "subject_pin": r.subject_pin, "valuation_date": r.valuation_date.isoformat(),
             "updated_at": r.updated_at.isoformat()} for r in rows]


@router.get("/cma/saved/{cma_id}")
def get_saved(cma_id: str, session: Session = Depends(get_session)):
    row = session.get(SavedCMA, cma_id)
    if row is None:
        raise HTTPException(404, "Saved CMA not found")
    return {"id": row.id, "title": row.title, "state": row.state}
