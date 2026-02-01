"""Documents module - document management and collaboration."""

from src.modules.documents.router import router
from src.modules.documents.websocket_router import router as ws_router

__all__ = ["router", "ws_router"]
