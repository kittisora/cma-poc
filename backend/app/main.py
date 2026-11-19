"""FastAPI entry point.

    uvicorn app.main:app --port 8000

Serves the JSON API under /api and, when frontend/out exists, the exported Next.js app.
"""

from __future__ import annotations

import base64
import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from .api.routes import router
from .config import get_settings
from .migrate import upgrade_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    upgrade_db()
    yield


def create_app(run_migrations: bool = True) -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="CMA — Fairfax County 22308/22309", version="1.0.0",
                  lifespan=lifespan if run_migrations else None)
    app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
                       allow_methods=["*"], allow_headers=["*"], expose_headers=["Content-Disposition", "X-CMA-Fingerprint"])
    if settings.app_password:
        expected = (settings.app_username, settings.app_password)

        @app.middleware("http")
        async def basic_auth(request: Request, call_next):
            if request.url.path == "/api/health":
                return await call_next(request)
            header = request.headers.get("authorization", "")
            if header.lower().startswith("basic "):
                try:
                    user, _, pwd = base64.b64decode(header[6:]).decode().partition(":")
                    if secrets.compare_digest(user.encode(), expected[0].encode()) and \
                            secrets.compare_digest(pwd.encode(), expected[1].encode()):
                        return await call_next(request)
                except (ValueError, UnicodeDecodeError):
                    pass
            return Response("Authentication required", status_code=401,
                            headers={"WWW-Authenticate": 'Basic realm="CMA"'})

    app.include_router(router)

    # The exported Next.js app (frontend/out): one HTML file per route plus /_next assets.
    dist = Path(settings.frontend_dist).resolve()
    if dist.is_dir() and (dist / "index.html").exists():
        if (dist / "_next").is_dir():
            app.mount("/_next", StaticFiles(directory=dist / "_next"), name="next-assets")

        def _inside(f: Path) -> bool:
            return dist in f.resolve().parents

        # HEAD too: the Next.js router probes routes with HEAD when prefetching.
        @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
        def web(path: str):
            if path.startswith("api/"):
                return Response(status_code=404)
            clean = path.strip("/")
            candidates = ([dist / "index.html"] if not clean else
                          [dist / clean, dist / f"{clean}.html", dist / clean / "index.html"])
            # Segment prefetch files: the router asks for "data/__next.data.__PAGE__.txt" while the
            # export writes "data/__next.data/__PAGE__.txt".
            head, _, name = clean.rpartition("/")
            if name.startswith("__next.") and name.endswith(".txt") and name.count(".") > 2:
                first, *rest = name[len("__next."):-len(".txt")].split(".")
                candidates.append(dist / head / f"__next.{first}" / ("/".join(rest) + ".txt"))
            for f in candidates:
                if f.is_file() and _inside(f):
                    return FileResponse(f)
            not_found = dist / "404.html"
            return FileResponse(not_found, status_code=404) if not_found.exists() else Response(status_code=404)

    return app


app = create_app()
