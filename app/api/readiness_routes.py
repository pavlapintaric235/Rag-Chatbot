from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.services.readiness_service import get_readiness_report

readiness_router = APIRouter()


@readiness_router.get("/ready")
def readiness_check() -> JSONResponse:
    report = get_readiness_report()
    status_code = 200 if report["status"] == "ready" else 503
    return JSONResponse(status_code=status_code, content=report)