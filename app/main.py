"""FastAPI application factory and route registration."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from secrets import token_urlsafe

from fastapi import FastAPI, Request, Response
from fastapi import Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.api.agents import router as agents_router
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.knowledge import router as knowledge_router
from app.api.knowledge_sync import router as knowledge_sync_router
from app.api.personas import router as personas_router
from app.api.users import router as users_router
from app.core.config import get_settings
from app.core.auth import require_password_change_complete
from app.core.database import SessionLocal, init_database
from app.core.security import add_security_headers
from app.services.user_service import bootstrap_initial_admin

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
STATIC_DIRECTORY = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Prepare local runtime paths before the server accepts requests."""
    settings = get_settings()
    settings.ensure_storage_directories()
    init_database()
    with SessionLocal() as db:
        bootstrap_initial_admin(db, settings)
    logger.info("Starting %s in %s", settings.app_name, settings.app_env)
    yield
    logger.info("Stopping %s", settings.app_name)


def create_app() -> FastAPI:
    """Create the application, keeping construction testable and modular."""
    settings = get_settings()
    # Keep debug pages disabled even in development so API clients never receive stack traces.
    app = FastAPI(title=settings.app_name, debug=False, lifespan=lifespan)
    session_secret = settings.session_secret_key.get_secret_value() if settings.session_secret_key else None
    if not session_secret:
        if settings.app_env.lower() == "production":
            raise RuntimeError("SESSION_SECRET_KEY must be configured in production")
        session_secret = token_urlsafe(48)
        logger.warning("SESSION_SECRET_KEY is unset; generated an ephemeral development session secret")
    app.add_middleware(
        SessionMiddleware,
        secret_key=session_secret,
        session_cookie=settings.session_cookie_name,
        https_only=settings.app_env.lower() == "production",
        same_site="lax",
    )
    add_security_headers(app)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, error: RequestValidationError) -> JSONResponse:
        """Return concise, field-focused validation errors without echoing raw inputs."""
        errors = [
            {"field": ".".join(str(part) for part in issue["loc"]), "message": issue["msg"]}
            for issue in error.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": "Invalid request data", "errors": errors})

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, error: Exception) -> JSONResponse:
        """Log unexpected errors server-side while returning a safe public response."""
        logger.exception("Unhandled request error on %s", request.url.path, exc_info=error)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
    app.mount("/static", StaticFiles(directory=STATIC_DIRECTORY), name="static")

    @app.get("/", include_in_schema=False)
    def landing_page() -> FileResponse:
        """Serve the lightweight browser-based administration interface."""
        return FileResponse(STATIC_DIRECTORY / "index.html")

    @app.get("/favicon.ico", include_in_schema=False, status_code=204)
    def favicon() -> Response:
        """Avoid a noisy 404 while no branded favicon has been added yet."""
        return Response(status_code=204)

    app.include_router(health_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    protected = [Depends(require_password_change_complete)]
    app.include_router(personas_router, prefix="/api", dependencies=protected)
    app.include_router(agents_router, prefix="/api", dependencies=protected)
    app.include_router(knowledge_router, prefix="/api", dependencies=protected)
    app.include_router(knowledge_sync_router, prefix="/api", dependencies=protected)
    app.include_router(chat_router, prefix="/api", dependencies=protected)
    app.include_router(users_router, prefix="/api", dependencies=protected)
    return app


app = create_app()
