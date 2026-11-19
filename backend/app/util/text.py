from __future__ import annotations

import re

# USPS street-suffix and directional abbreviations used by the county address file.
_ABBREV = {
    "STREET": "ST", "ROAD": "RD", "DRIVE": "DR", "AVENUE": "AVE", "COURT": "CT",
    "LANE": "LN", "PLACE": "PL", "BOULEVARD": "BLVD", "TERRACE": "TER",
    "CIRCLE": "CIR", "PARKWAY": "PKWY", "HIGHWAY": "HWY", "TRAIL": "TRL",
    "SQUARE": "SQ", "WAY": "WAY", "RUN": "RUN", "LOOP": "LOOP", "POINT": "PT",
    "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W",
    "APARTMENT": "APT", "UNIT": "UNIT", "SUITE": "STE", "#": "UNIT",
}


def normalize_address(text: str) -> str:
    """Uppercase, strip punctuation and apply USPS abbreviations to each token."""
    t = re.sub(r"[.,]", " ", text.upper())
    t = re.sub(r"#\s*", " UNIT ", t)
    tokens = [tok for tok in re.split(r"\s+", t) if tok]
    return " ".join(_ABBREV.get(tok, tok) for tok in tokens)


def search_tokens(query: str) -> list[str]:
    return [tok for tok in normalize_address(query).split(" ") if tok]


def property_type_from_land_use(land_use: str | None) -> str:
    """Map the county land-use description to a comparable-sale property group."""
    if not land_use:
        return "OTHER"
    lu = land_use.lower()
    if "townhouse" in lu:
        return "TOWNHOUSE"
    if "condominium" in lu and not any(k in lu for k in ("office", "commercial", "retail", "industrial")):
        return "CONDO"
    if "single-family" in lu and "inf com" not in lu:
        return "DETACHED"
    if "duplex" in lu:
        return "DUPLEX"
    return "OTHER"


PROPERTY_TYPE_LABELS = {
    "DETACHED": "Single-family detached",
    "TOWNHOUSE": "Townhouse",
    "CONDO": "Condominium",
    "DUPLEX": "Duplex",
    "OTHER": "Other / non-residential",
}

RESIDENTIAL_TYPES = {"DETACHED", "TOWNHOUSE", "CONDO", "DUPLEX"}


def fmt_money(v: float | int | None, cents: bool = False) -> str:
    if v is None:
        return "—"
    return f"${v:,.2f}" if cents else f"${round(v):,}"


def fmt_int(v: float | int | None) -> str:
    return "—" if v is None else f"{round(v):,}"
