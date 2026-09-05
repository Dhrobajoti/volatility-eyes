from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import (
    routes_images,
    routes_insights,
    routes_jobs,
    routes_legacy,
    routes_plugins,
    routes_ws,
)
from .config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Volatility Eyes API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(routes_plugins.router)
    app.include_router(routes_images.router)
    app.include_router(routes_jobs.router)
    app.include_router(routes_ws.router)
    app.include_router(routes_insights.router)
    app.include_router(routes_legacy.router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
