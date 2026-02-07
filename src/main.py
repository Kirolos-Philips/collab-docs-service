"""
Collaborative Document Editor - FastAPI Application

Real-time collaborative document editing with WebSockets, MongoDB, and Redis.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.config import settings
from core.database import close_db_connections, init_db_connections


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Manage application lifecycle - startup and shutdown events."""
    # Startup
    await init_db_connections()

    # Initialize Redis sync for WebSockets
    from core.redis_pubsub import redis_sync_manager

    await redis_sync_manager.connect()
    await redis_sync_manager.start_listening()

    yield
    # Shutdown
    from core.redis_pubsub import redis_sync_manager

    await redis_sync_manager.stop()
    await close_db_connections()


def create_app() -> FastAPI:
    """Application factory for creating FastAPI instance."""
    app = FastAPI(
        title=settings.APP_NAME,
        description="Real-time collaborative document editing API",
        version="0.1.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        swagger_ui_parameters={"persistAuthorization": True},
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint for container orchestration."""
        return {"status": "healthy", "app": settings.APP_NAME}

    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint."""
        return {
            "message": "Collaborative Document Editor API",
            "docs": "/docs" if settings.DEBUG else "Disabled in production",
        }

    # Mount static files
    from pathlib import Path

    root_path = Path(__file__).resolve().parent.parent
    static_path = root_path / settings.STATIC_ROOT
    app.mount(
        settings.STATIC_URL, StaticFiles(directory=str(static_path)), name="static"
    )

    media_path = root_path / settings.MEDIA_ROOT
    app.mount(settings.MEDIA_URL, StaticFiles(directory=str(media_path)), name="media")

    # Register module routers
    from modules.auth.router import router as auth_router
    from modules.documents.router import router as documents_router
    from modules.documents.websocket_router import router as documents_ws_router

    app.include_router(auth_router)
    app.include_router(documents_router)
    app.include_router(documents_ws_router)

    return app


# Create application instance
app = create_app()
