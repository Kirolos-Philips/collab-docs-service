"""Documents module - document management and collaboration."""

from modules.documents.router import router
from modules.documents.websocket_router import router as ws_router

__all__ = ["router", "ws_router"]
