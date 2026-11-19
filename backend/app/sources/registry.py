from __future__ import annotations

from ..config import Settings, get_settings
from .base import DataProvider


def get_provider(name: str | None = None, settings: Settings | None = None) -> DataProvider:
    settings = settings or get_settings()
    name = name or settings.data_provider
    if name == "fairfax_arcgis":
        from .fairfax_arcgis import FairfaxArcGISProvider

        return FairfaxArcGISProvider(
            base_url=settings.arcgis_base_url,
            token=settings.arcgis_token,
            timeout=settings.http_timeout_seconds,
            concurrency=settings.refresh_concurrency,
        )
    # Future: "bridge_reso" (approved MLS feed) or another licensed provider.
    raise ValueError(f"Unknown data provider: {name!r}")
