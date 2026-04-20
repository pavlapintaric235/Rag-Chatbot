from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

app.include_router(router)

frontend_dir = settings.project_root / "frontend"
assets_dir = frontend_dir / "assets"


if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/", include_in_schema=False)
def frontend_index() -> FileResponse | dict[str, str]:
    index_file = frontend_dir / "index.html"

    if index_file.exists():
        return FileResponse(index_file)

    return {
        "message": f"{settings.app_name} is running.",
        "environment": settings.app_env,
    }