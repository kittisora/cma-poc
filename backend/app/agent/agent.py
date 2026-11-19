"""AI agent that explains a CMA.

The agent never ranks or calculates. Ranking and arithmetic happen in tested
backend code (`services.run_cma`); the agent's tools return slices of that one
precomputed result, so every number it can quote is the number the dashboard
and the reports show. The provider key stays on the server.

Providers (AI_PROVIDER, default "auto" = OpenAI when OPENAI_API_KEY is set):
- OpenAI: Responses API with strict function tools (OPENAI_MODEL, default gpt-6.2-sol).
- Anthropic: Messages API with strict tools and server-side refusal fallbacks
  (ANTHROPIC_MODEL, default claude-opus-5-5).
Both providers run the same tools against the same precomputed CMA.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import anthropic
import openai
from sqlalchemy.orm import Session

from .. import repository as repo
from ..config import get_settings
from ..services import CMARequest, run_cma

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the analysis assistant inside a Comparative Market Analysis (CMA) tool used by a residential real estate team in Fairfax County, Virginia (ZIP codes 22308 and 22309).

Your job is to explain results that the tool has already computed: the subject property's recorded facts, the ranked comparable sales, and the price-per-square-foot valuation. You do not choose comps or compute prices yourself.

Rules:
- Use the tools to read facts before making claims. Quote figures exactly as the tools return them; do not do new arithmetic beyond simple differences you show explicitly.
- Cite the record behind every material claim in square brackets, using the record_id the tool provides, e.g. [PARID 1022 03  0082A · Deed Book 27172 Page 2126]. Agent-entered values must be labelled as agent input, not public record.
- Data comes from Fairfax County public records (assessor and recorded deeds), not the MLS. County dwelling characteristics reflect the current record, not necessarily the house at the time of each sale. Say so when it matters.
- Keep the two area definitions separate: assessor above-grade living area (SFLA) versus total finished area (includes finished basement; only from listings or agent input).
- When describing the difference between the estimate and a past sale, call it "estimated change since the last sale".
- Condition: county records hold only a mass-appraisal condition rating and grade. When condition or repair evidence is missing, list what needs inspection. Never infer that a repair is needed from the year built alone.
- If comps are few or filters limited the search, say which filters and what widening would add, as reported by the tools.
- This is a CMA, not an appraisal. Do not present the estimate as a guaranteed price.
- Be concise and plain-spoken. Use short paragraphs or bullet lists. No marketing language."""

NARRATIVE_INSTRUCTION = """Write the narrative section for the client-facing CMA report on this subject property. Read the subject facts, the ranked comps, the valuation and the search explanation with your tools first.

Structure (plain text, short headed paragraphs, about 250-400 words total):
1. Summary — the estimate, range and which square-footage basis it uses.
2. Comparable sales — why these comps were chosen (location, size, recency, similarity) and any notable differences.
3. Method — the price-per-square-foot calculation and any adjustments or appreciation, labelled as assumptions.
4. Condition and limitations — what county records do and do not show, and what should be inspected.
Cite records in square brackets for material facts."""


def _tool(name: str, description: str, properties: dict | None = None, required: list[str] | None = None) -> dict:
    """Provider-neutral tool spec. Strict: every property is required and no others are allowed."""
    return {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties or {}, "required": required or [],
                       "additionalProperties": False},
    }


TOOL_SPECS = [
    _tool("get_subject_facts",
          "Recorded facts for the subject property (address, parcel ID, style, year built, beds, baths, "
          "above-grade sq ft, lot, assessor condition/grade, garage evidence, agent inputs), its full recorded sale "
          "history, the last market sale, and what condition evidence is missing. Includes source record IDs."),
    _tool("get_ranked_comps",
          "The comparable sales the agent selected for this CMA, in rank order, each with score, per-factor "
          "comparison, plain-language reason, sale price/date, $/sf, distance and source record ID. Set "
          "include_candidates to true to also get the next-ranked eligible sales that were not selected.",
          {"include_candidates": {"type": "boolean", "description": "Also return unselected eligible sales."}},
          ["include_candidates"]),
    _tool("get_valuation",
          "The computed valuation: estimate, range, the basis used (above-grade or total finished sq ft), "
          "average/median/high/low $/sf, step-by-step calculation lines, adjustments, appreciation, and the "
          "estimated change since the last sale."),
    _tool("get_search_explanation",
          "How the comp search ran: valuation date, search window, how many recorded transfers each eligibility "
          "rule removed, whether results were limited, and how many more sales widening each rule would add."),
    _tool("get_property_facts",
          "Recorded facts and sale history for any parcel in the loaded ZIP codes, by parcel ID (PARID), "
          "for example a comp you want to describe in more detail.",
          {"pin": {"type": "string", "description": "Parcel ID exactly as returned by other tools."}}, ["pin"]),
]

# Anthropic Messages API shape.
TOOLS = [{"name": t["name"], "description": t["description"], "strict": True, "input_schema": t["parameters"]}
         for t in TOOL_SPECS]
# OpenAI Responses API shape.
OPENAI_TOOLS = [{"type": "function", "name": t["name"], "description": t["description"], "strict": True,
                 "parameters": t["parameters"]} for t in TOOL_SPECS]


class AgentUnavailable(Exception):
    pass


class CMAToolbox:
    """Executes tool calls against one precomputed CMA result."""

    def __init__(self, session: Session, req: CMARequest):
        self.session = session
        self.req = req
        self.cma = run_cma(session, req)
        self.records_cited: list[str] = []

    def _comp_view(self, c: dict) -> dict:
        p, s = c["property"], c["sale"]
        return {
            "rank": c["rank"], "score": c["score"], "selected": c["selected"], "address": c["address"],
            "pin": c["pin"], "sale_date": s["sale_date"], "price": s["price"], "validity": s["validity"],
            "distance_miles": c["distance_miles"], "months_before_valuation": c["months_before"],
            "above_grade_sf": p["above_grade_sf"], "ppsf_above_grade": c["ppsf_above_grade"],
            "total_finished_sf": c["total_finished_sf"], "total_finished_source": c["total_finished_source"],
            "beds": p["beds"], "baths_full_half": p["baths_label"], "year_built": p["year_built"],
            "style": p["style"], "lot_sf": p["lot_sf"], "condition": p["condition"], "grade": p["grade"],
            "reason": c["reason"], "factors": [{k: f[k] for k in ("label", "score", "detail")} for f in c["factors"]],
            "warnings": c["warnings"], "record_id": c["source"]["record_id"],
            "retrieved_at": c["source"]["retrieved_at"],
        }

    def run(self, name: str, args: dict) -> Any:
        cma = self.cma
        if name == "get_subject_facts":
            subj = dict(cma["subject"])
            subj.pop("agent_inputs", None)
            return {"subject": subj, "property_type": cma["subject_label"], "sources": cma["sources"],
                    "sale_history": [{k: s[k] for k in ("sale_date", "price", "validity", "deed_ref", "multi_parcel")}
                                     | {"record_id": f"PARID {s['pin']} · {s['deed_ref']}"} for s in cma["sale_history"]],
                    "last_market_sale": cma["last_market_sale"], "condition_evidence": cma["condition_evidence"],
                    "agent_inputs": cma["subject"].get("agent_inputs")}
        if name == "get_ranked_comps":
            comps = [c for c in cma["comps"] if c["selected"] or args.get("include_candidates")]
            return {"valuation_date": cma["valuation_date"], "selected_count": len(cma["selected_sale_ids"]),
                    "selection_mode": cma["selection_mode"],
                    "ranking_note": "Ranking is price-blind: it uses distance, recency, living area, beds, baths, "
                                    "lot, age, style, assessor condition/grade and features.",
                    "comps": [self._comp_view(c) for c in comps[:15]]}
        if name == "get_valuation":
            v = cma["valuation"]
            return {"estimate": v["estimate"], "range_low": v["range_low"], "range_high": v["range_high"],
                    "primary_basis": v["primary_basis"], "point_statistic": v["point_statistic"],
                    "appreciation_pct": v["appreciation_pct"], "adjustments": v["adjustments"],
                    "bases": {k: {kk: b[kk] for kk in ("label", "available", "reason_unavailable", "subject_area",
                                                       "subject_area_source", "n", "ppsf", "indicated", "estimate",
                                                       "range_low", "range_high", "lines", "warnings")}
                              for k, b in v["bases"].items()},
                    "change_since_last_sale": cma["change_since_last_sale"], "warnings": v["warnings"]}
        if name == "get_search_explanation":
            return {"valuation_date": cma["valuation_date"], "criteria": cma["criteria"], **cma["search"],
                    "warnings": cma["warnings"]}
        if name == "get_property_facts":
            pin = args.get("pin", "")
            facts = repo.get_property(self.session, pin)
            if facts is None:
                return {"error": f"Parcel {pin!r} is not in the loaded data."}
            d = facts.to_dict()
            d.pop("agent_inputs", None)
            return {"facts": d, "sale_history": [s.to_dict() for s in repo.get_sale_history(self.session, pin)][:10]}
        return {"error": f"Unknown tool {name}"}


def _anthropic_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=get_settings().anthropic_api_key, max_retries=2, timeout=180)


def _openai_client() -> openai.OpenAI:
    return openai.OpenAI(api_key=get_settings().openai_api_key, max_retries=2, timeout=180)


def _run_tool(box: CMAToolbox, name: str, args: dict, trace: list[dict]) -> tuple[Any, bool]:
    try:
        out = box.run(name, args)
        is_error = isinstance(out, dict) and "error" in out
    except Exception as exc:  # report tool failures to the model instead of crashing the loop
        log.exception("tool %s failed", name)
        out, is_error = {"error": str(exc)}, True
    trace.append({"tool": name, "input": args, "error": is_error})
    return out, is_error


def _loop_anthropic(box: CMAToolbox, messages: list[dict], client: Any) -> tuple[str, list[dict], str | None]:
    settings = get_settings()
    convo: list[dict] = [{"role": m["role"], "content": m["content"]} for m in messages if m.get("content")]
    trace: list[dict] = []
    stop_reason = None
    for _ in range(settings.agent_max_turns):
        try:
            resp = client.beta.messages.create(
                model=settings.anthropic_model, max_tokens=16000, system=SYSTEM_PROMPT, tools=TOOLS,
                messages=convo, output_config={"effort": settings.anthropic_effort},
                betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            )
        except anthropic.AuthenticationError as exc:
            raise AgentUnavailable("The AI provider rejected the server's API key.") from exc
        except anthropic.RateLimitError as exc:
            raise AgentUnavailable("The AI provider is rate-limiting requests; try again shortly.") from exc
        except anthropic.APIStatusError as exc:
            raise AgentUnavailable(f"AI provider error ({exc.status_code}).") from exc
        except anthropic.APIConnectionError as exc:
            raise AgentUnavailable("Could not reach the AI provider.") from exc
        stop_reason = resp.stop_reason
        if stop_reason == "refusal":
            return "The AI assistant declined this request. The CMA figures above are unaffected.", trace, stop_reason
        convo.append({"role": "assistant", "content": resp.content})
        if stop_reason == "pause_turn":
            continue
        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        if not tool_uses:
            return "\n".join(b.text for b in resp.content if b.type == "text").strip(), trace, stop_reason
        results = []
        for tu in tool_uses:
            out, is_error = _run_tool(box, tu.name, dict(tu.input or {}), trace)
            results.append({"type": "tool_result", "tool_use_id": tu.id,
                            "content": json.dumps(out, default=str), "is_error": is_error})
        convo.append({"role": "user", "content": results})
    return "The assistant stopped before finishing (turn limit reached).", trace, stop_reason


NO_CREDIT_MESSAGE = ("The OpenAI account has no credits left. Add credits at platform.openai.com "
                     "(Settings > Billing); no restart is needed.")


def _openai_429_message(exc: Exception) -> str:
    """OpenAI uses HTTP 429 both for rate limits and for an account with no credit."""
    text = f"{getattr(exc, 'code', '')} {getattr(exc, 'message', '')}".lower()
    if "insufficient_quota" in text or "credit" in text or "quota" in text:
        return NO_CREDIT_MESSAGE
    return "OpenAI is rate-limiting requests; try again shortly."


def _loop_openai(box: CMAToolbox, messages: list[dict], client: Any) -> tuple[str, list[dict], str | None]:
    settings = get_settings()
    items: list[Any] = [{"role": m["role"], "content": m["content"]} for m in messages if m.get("content")]
    trace: list[dict] = []
    status = None
    kwargs: dict[str, Any] = {"model": settings.openai_model, "instructions": SYSTEM_PROMPT,
                              "tools": OPENAI_TOOLS, "max_output_tokens": 16000}
    if settings.openai_reasoning_effort.strip():
        kwargs["reasoning"] = {"effort": settings.openai_reasoning_effort.strip()}
    for _ in range(settings.agent_max_turns):
        try:
            resp = client.responses.create(input=items, **kwargs)
        except openai.AuthenticationError as exc:
            raise AgentUnavailable("OpenAI rejected the server's API key (OPENAI_API_KEY).") from exc
        except openai.PermissionDeniedError as exc:
            raise AgentUnavailable("The OpenAI key does not have access to this model or project.") from exc
        except openai.NotFoundError as exc:
            raise AgentUnavailable(f"OpenAI model {settings.openai_model!r} is not available to this key. "
                                   "Set OPENAI_MODEL in .env.") from exc
        except openai.RateLimitError as exc:
            raise AgentUnavailable(_openai_429_message(exc)) from exc
        except openai.BadRequestError as exc:
            raise AgentUnavailable(f"OpenAI rejected the request: {getattr(exc, 'message', exc)}") from exc
        except openai.APIStatusError as exc:
            raise AgentUnavailable(f"AI provider error ({exc.status_code}).") from exc
        except openai.APIConnectionError as exc:
            raise AgentUnavailable("Could not reach OpenAI.") from exc
        status = getattr(resp, "status", None)
        output = list(getattr(resp, "output", None) or [])
        calls = [it for it in output if getattr(it, "type", None) == "function_call"]
        if not calls:
            text = (getattr(resp, "output_text", "") or "").strip()
            refused = any(getattr(c, "type", None) == "refusal"
                          for it in output if getattr(it, "type", None) == "message"
                          for c in (getattr(it, "content", None) or []))
            if refused and not text:
                return "The AI assistant declined this request. The CMA figures above are unaffected.", trace, "refusal"
            if not text and status == "incomplete":
                text = "The assistant stopped before finishing (output limit reached)."
            return text, trace, status
        # Pass every output item back: reasoning items must accompany their function calls.
        items.extend(output)
        for call in calls:
            try:
                args = json.loads(call.arguments or "{}")
            except json.JSONDecodeError:
                args = None
            if isinstance(args, dict):
                out, _ = _run_tool(box, call.name, args, trace)
            else:
                out = {"error": "Tool arguments were not valid JSON; call the tool again."}
                trace.append({"tool": call.name, "input": {}, "error": True})
            items.append({"type": "function_call_output", "call_id": call.call_id,
                          "output": json.dumps(out, default=str)})
    return "The assistant stopped before finishing (turn limit reached).", trace, status


def run_agent(session: Session, req: CMARequest, messages: list[dict], client: Any = None,
              provider: str | None = None) -> dict:
    """Run the tool loop. `messages` are prior chat turns: [{"role": "user"|"assistant", "content": str}]."""
    settings = get_settings()
    provider = provider or settings.active_ai_provider
    if provider is None:
        raise AgentUnavailable("AI assistant is not configured. Set OPENAI_API_KEY on the server.")
    if provider not in ("openai", "anthropic"):
        raise AgentUnavailable(f"Unknown AI provider {provider!r}.")
    box = CMAToolbox(session, req)
    if provider == "openai":
        text, trace, stop = _loop_openai(box, messages, client or _openai_client())
        model = settings.openai_model
    else:
        text, trace, stop = _loop_anthropic(box, messages, client or _anthropic_client())
        model = settings.anthropic_model
    return {"reply": text, "tool_calls": trace, "stop_reason": stop, "provider": provider, "model": model,
            "estimate_shown": box.cma["valuation"]["estimate"]}


def generate_narrative(session: Session, req: CMARequest, client: Any = None, provider: str | None = None) -> dict:
    out = run_agent(session, req, [{"role": "user", "content": NARRATIVE_INSTRUCTION}], client=client,
                    provider=provider)
    if not out["reply"]:
        raise AgentUnavailable("The AI returned an empty narrative.")
    return {"narrative": out["reply"], "generated_by": "ai", "provider": out["provider"], "model": out["model"],
            "tool_calls": out["tool_calls"]}


def check_connection() -> dict:
    """One small request to confirm the configured key and model work. Used by `python -m app.agent.check`."""
    settings = get_settings()
    provider = settings.active_ai_provider
    if provider is None:
        raise AgentUnavailable("No AI key configured. Set OPENAI_API_KEY in .env.")
    prompt = "Reply with the single word OK."
    try:
        if provider == "openai":
            resp = _openai_client().responses.create(model=settings.openai_model, input=prompt, max_output_tokens=2000)
            text = (resp.output_text or "").strip()
        else:
            resp = _anthropic_client().messages.create(model=settings.anthropic_model, max_tokens=50,
                                                       messages=[{"role": "user", "content": prompt}])
            text = "".join(b.text for b in resp.content if b.type == "text").strip()
    except openai.RateLimitError as exc:
        raise AgentUnavailable(_openai_429_message(exc)) from exc
    except (openai.APIError, anthropic.APIError) as exc:
        raise AgentUnavailable(f"{provider} call failed: {type(exc).__name__}: {getattr(exc, 'message', exc)}") from exc
    return {"provider": provider, "model": settings.ai_model, "reply": text}
