"""WebSocket router for document synchronization."""

import contextlib

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from src.core.redis_pubsub import redis_sync_manager
from src.core.websockets import manager
from src.modules.documents.dependencies import get_ws_authenticated_doc
from src.modules.documents.services import process_sync_message

router = APIRouter(prefix="/documents", tags=["documents_sync"])


@router.websocket("/{document_id}/sync")
async def sync_document(
    websocket: WebSocket,
    document_id: str,
    auth_data: tuple = Depends(get_ws_authenticated_doc),
):
    """
    WebSocket endpoint for real-time document synchronization.
    Authentication and permissions are handled by get_ws_authenticated_doc.
    """
    if not auth_data:
        # Dependency already closed the connection
        return

    user, _doc = auth_data

    # 1. Connection Setup
    await manager.connect(document_id, websocket)
    await redis_sync_manager.subscribe(document_id)

    try:
        while True:
            # Receive data from client
            data = await websocket.receive_json()

            # Process logic (Decoupled from pub/sub)
            processed_data = await process_sync_message(user, data)

            # Publish to Redis for other server instances
            await redis_sync_manager.publish(document_id, processed_data)

    except WebSocketDisconnect:
        manager.disconnect(document_id, websocket)
        # Only unsubscribe if no more local clients are listening to this doc
        if document_id not in manager.active_connections:
            await redis_sync_manager.unsubscribe(document_id)
    except Exception:
        manager.disconnect(document_id, websocket)
        with contextlib.suppress(RuntimeError):
            await websocket.close()
