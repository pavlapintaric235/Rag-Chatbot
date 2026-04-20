from fastapi import FastAPI

from app.api.readiness_routes import readiness_router
from app.api.routes import router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

app.include_router(router)
app.include_router(readiness_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": f"{settings.app_name} is running.",
        "environment": settings.app_env,
    }