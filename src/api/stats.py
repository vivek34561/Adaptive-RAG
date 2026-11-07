"""Usage statistics endpoint for the Adaptive RAG backend."""

from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["stats"])

_STARTED_AT = datetime.now(timezone.utc)


class StatsResponse(BaseModel):
    started_at: str
    uptime_seconds: int
    version: str


@router.get("/stats", response_model=StatsResponse)
def stats() -> StatsResponse:
    """Return when the server started and how long it has been running."""
    now = datetime.now(timezone.utc)
    return StatsResponse(
        started_at=_STARTED_AT.isoformat(timespec="seconds"),
        uptime_seconds=int((now - _STARTED_AT).total_seconds()),
        version="1.0.0",
    )
