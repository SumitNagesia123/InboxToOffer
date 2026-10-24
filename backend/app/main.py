import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import (
    AppException,
    app_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.core.logging import logger
from app.database.session import SessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for startup and shutdown procedures."""
    logger.info("Starting up %s (version %s, env: %s)...", settings.PROJECT_NAME, settings.VERSION, settings.ENVIRONMENT)

    # Verify database connectivity on startup
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        logger.info("Database connectivity established successfully.")
    except Exception as e:
        logger.error("Database connectivity failed on startup: %s", str(e))
    finally:
        db.close()

    yield

    logger.info("Shutting down %s...", settings.PROJECT_NAME)


def create_application() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
    )

    # CORS Middleware
    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Exception Handlers
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Mount API Routers
    app.include_router(api_router, prefix=settings.API_V1_STR)

    # Mount Static Files (Production Frontend if bundled)
    static_dir = os.path.join(os.getcwd(), "static")
    index_file = os.path.join(static_dir, "index.html")
    assets_dir = os.path.join(static_dir, "assets")

    if os.path.isdir(static_dir) and os.path.exists(index_file):
        from fastapi.staticfiles import StaticFiles
        from fastapi.responses import FileResponse

        if os.path.isdir(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            if full_path.startswith("api") or full_path.startswith("docs") or full_path.startswith("redoc") or full_path.startswith("openapi.json"):
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Not Found")
            file_path = os.path.join(static_dir, full_path)
            if full_path and os.path.isfile(file_path):
                return FileResponse(file_path)
            return FileResponse(index_file)
    else:
        @app.get("/", tags=["Root"])
        def root():
            """Root API welcome & health pointer."""
            return {
                "name": settings.PROJECT_NAME,
                "version": settings.VERSION,
                "docs": "/docs",
                "health": f"{settings.API_V1_STR}/health",
                "environment": settings.ENVIRONMENT,
            }

    return app


app = create_application()
