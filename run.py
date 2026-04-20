from __future__ import annotations

import os

import uvicorn

from app.core.config import settings


def main() -> None:
    host = os.getenv("HOST", "").strip() or os.getenv("APP_HOST", "").strip() or "0.0.0.0"

    port_value = (
        os.getenv("PORT", "").strip()
        or os.getenv("APP_PORT", "").strip()
        or str(settings.app_port)
    )

    try:
        port = int(port_value)
    except ValueError:
        port = settings.app_port

    reload_enabled = settings.app_env == "development" and "PORT" not in os.environ

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload_enabled,
    )


if __name__ == "__main__":
    main()