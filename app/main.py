"""Application factory: middleware, error shapes, static files and routes."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware

from app import __version__
from app.config import PUBLIC_DIR, get_settings
from app.routers import api, views
from app.schemas import VALIDATION_MESSAGES
from app.templating import templates

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("qlonil")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create and seed the schema before the first request, if configured.

    A database that is briefly unreachable must not take the whole app down —
    the request path retries the bootstrap, and /api/health reports the truth in
    the meantime.
    """
    if settings.auto_init_db:
        try:
            from app.database import initialise_database

            initialise_database()
        except Exception:
            logger.exception("Database bootstrap failed; will retry on first request")

    yield


def _wants_html(request: Request) -> bool:
    """Page routes answer in HTML; the API and partials always answer in JSON."""
    if request.url.path.startswith(("/api/", "/partials/")):
        return False

    accept = request.headers.get("accept", "")
    return "text/html" in accept or "application/json" not in accept


def _problem(status: int, title: str, request: Request, detail: str | None = None) -> JSONResponse:
    body: dict[str, object] = {"title": title, "status": status, "instance": request.url.path}
    if detail:
        body["detail"] = detail

    return JSONResponse(body, status_code=status, media_type="application/problem+json")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Qlonil API",
        version=__version__,
        description="Storefront API and server-rendered pages.",
        docs_url="/docs" if settings.is_development else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )

    # ---------------------------------------------------------------- CORS
    if settings.cors_allow_any_origin:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_exact_origins,
            allow_origin_regex=settings.cors_origin_regex,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # -------------------------------------------------------------- routes
    app.include_router(api.router)
    app.include_router(views.router)

    # ------------------------------------------------------ static assets
    # On Vercel these paths are served straight from /public by the CDN and
    # never reach the function; locally the mounts below serve the same files
    # at the same URLs.
    for folder in ("css", "js", "images"):
        directory = PUBLIC_DIR / folder
        if directory.is_dir():
            app.mount(f"/{folder}", StaticFiles(directory=str(directory)), name=folder)

    @app.get("/favicon.svg", include_in_schema=False)
    async def favicon() -> Response:
        icon = PUBLIC_DIR / "favicon.svg"
        if icon.is_file():
            return FileResponse(icon, media_type="image/svg+xml")
        return Response(status_code=404)

    # ------------------------------------------------------------- errors
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        if _wants_html(request) and exc.status_code == 404:
            return templates.TemplateResponse(
                request, "404.html", {"page_title": "Page not found"}, status_code=404
            )

        title = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return _problem(exc.status_code, title, request)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors: dict[str, list[str]] = {}

        for error in exc.errors():
            field = str(error["loc"][-1])
            message = VALIDATION_MESSAGES.get(field, error.get("msg", "Invalid value."))
            errors.setdefault(field, []).append(message)

        return JSONResponse(
            {
                "title": "One or more validation errors occurred.",
                "status": 400,
                "instance": request.url.path,
                "errors": errors,
            },
            status_code=400,
            media_type="application/problem+json",
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s", request.url.path)

        if _wants_html(request):
            return templates.TemplateResponse(
                request,
                "error.html",
                {"page_title": "Something went wrong"},
                status_code=500,
            )

        return _problem(
            500,
            "An unexpected error occurred.",
            request,
            detail=str(exc) if settings.is_development else None,
        )

    return app


app = create_app()
