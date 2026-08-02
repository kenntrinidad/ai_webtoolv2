"""Health endpoint used by local checks and deployment probes."""

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    """Report that the web process is running without exposing sensitive settings."""
    return {"status": "ok", "environment": settings.app_env}
