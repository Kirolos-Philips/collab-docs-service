"""WebSocket router for document synchronization."""

import base64
import contextlib

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.database import get_database
from core.redis_pubsub import redis_sync_manager
from core.websockets import manager
from modules.documents.dependencies import get_ws_authenticated_doc
from modules.documents.services import apply_crdt_update, process_sync_message

router = APIRouter(prefix="/documents", tags=["documents_sync"])


@router.websocket("/{document_id}/sync")
async def sync_document(
    websocket: WebSocket,
    document_id: str,
    auth_data: tuple = Depends(get_ws_authenticated_doc),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    WebSocket endpoint for real-time document synchronization.
    Authentication and permissions are handled by get_ws_authenticated_doc.
    """
    if not auth_data:
        # Dependency already closed the connection
        return

    user, doc = auth_data

    # 1. Connection Setup
    await manager.connect(document_id, websocket)
    await redis_sync_manager.subscribe(document_id)

    # 2. Synchronize Initial State
    # Send the current full binary state to the newly connected client
    if doc.state:
        # Encode state as base64 for JSON transport
        initial_state_b64 = base64.b64encode(doc.state).decode("utf-8")
        await websocket.send_json(
            {
                "type": "sync_state",
                "state": initial_state_b64,
                "version": 0,  # Future-proofing
            }
        )

    try:
        while True:
            # Receive message from client
            message = await websocket.receive_json()
            msg_type = message.get("type")

            if msg_type == "update":
                # Handle Yjs binary update
                update_b64 = message.get("update")
                if update_b64:
                    try:
                        # Decode base64 to binary
                        binary_update = base64.b64decode(update_b64)

                        # Apply to database (via service)
                        await apply_crdt_update(db, document_id, binary_update)
                    except Exception as e:
                        print(f"Error processing CRDT update: {e}")
                        continue

                # Process additional logic (enrichment, etc.)
                processed_data = await process_sync_message(user, message)

                # Publish to Redis for other replicas
                await redis_sync_manager.publish(document_id, processed_data)

            elif msg_type == "awareness":
                # Handle Yjs Awareness updates (cursor positions, selections, user info)
                # Broadcast directly to other local clients (skip Redis — ephemeral data)
                awareness_update = message.get("update")
                if awareness_update:
                    conns = manager.active_connections.get(document_id, set())
                    print(
                        f"[Awareness] Received from {user.username}, broadcasting to {len(conns) - 1} other(s)"
                    )
                    await manager.broadcast_except(
                        document_id, message, exclude=websocket
                    )

            elif msg_type == "presence":
                # Handle presence logic (Position, status, etc.)
                message["user_id"] = str(user.id)
                message["username"] = user.username
                message["avatar_url"] = user.avatar_url
                message["color"] = user.color
                await redis_sync_manager.publish(document_id, message)

    except WebSocketDisconnect:
        manager.disconnect(document_id, websocket)
        if document_id not in manager.active_connections:
            await redis_sync_manager.unsubscribe(document_id)
    except Exception:
        manager.disconnect(document_id, websocket)
        with contextlib.suppress(RuntimeError):
            await websocket.close()
