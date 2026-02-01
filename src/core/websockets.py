"""WebSocket connection manager - handles active connections and broadcasting."""

import json

from fastapi import WebSocket


class ConnectionManager:
    """Manages active WebSocket connections for documents."""

    def __init__(self):
        # Mapping: document_id -> set of active WebSockets
        self.active_connections: dict[str, set[WebSocket]] = {}

    async def connect(self, document_id: str, websocket: WebSocket):
        """Accept connection and track it under the document_id."""
        await websocket.accept()
        if document_id not in self.active_connections:
            self.active_connections[document_id] = set()
        self.active_connections[document_id].add(websocket)

    def disconnect(self, document_id: str, websocket: WebSocket):
        """Remove connection from tracking."""
        if document_id in self.active_connections:
            self.active_connections[document_id].discard(websocket)
            if not self.active_connections[document_id]:
                del self.active_connections[document_id]

    async def broadcast(self, document_id: str, message: dict):
        """Send message to all websockets connected to a specific document."""
        if document_id in self.active_connections:
            # Create a list to iterate safely in case connections drop
            connections = list(self.active_connections[document_id])
            message_json = json.dumps(message)
            for connection in connections:
                try:
                    await connection.send_text(message_json)
                except Exception:
                    # Connection might be closed already
                    self.disconnect(document_id, connection)


# Global instance
manager = ConnectionManager()
