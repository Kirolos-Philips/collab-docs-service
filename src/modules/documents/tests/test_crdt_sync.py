"""Integration tests for CRDT WebSocket synchronization."""

import base64
import json

import pytest
import y_py as Y
from httpx import AsyncClient

from src.core.redis_pubsub import redis_sync_manager
from src.core.websockets import manager
from src.modules.documents.crdt import CRDTDocumentManager
from src.modules.documents.services import get_document_by_id


@pytest.fixture
async def auth_details(async_client: AsyncClient):
    """Register and login a test user."""
    user_data = {
        "email": "crdt_user@example.com",
        "username": "crdtuser",
        "password": "testpassword123",
    }
    await async_client.post("/auth/register", json=user_data)
    await async_client.post(
        "/auth/verify-email",
        json={"email": user_data["email"], "otp": "123456"},
    )

    login_res = await async_client.post(
        "/auth/login",
        data={"username": user_data["email"], "password": user_data["password"]},
    )
    token = login_res.json()["access_token"]
    return {"token": token, "email": user_data["email"]}


class MockWebSocket:
    def __init__(self):
        self.sent_messages = []
        self.closed = False

    async def accept(self):
        pass

    async def send_json(self, data):
        self.sent_messages.append(data)

    async def send_text(self, text):
        self.sent_messages.append(json.loads(text))

    async def close(self, code=None, reason=None):
        self.closed = True


@pytest.mark.asyncio
async def test_crdt_update_sync(
    async_client: AsyncClient, auth_details: dict, mongo_db
):
    """Test that CRDT updates are relayed and persisted."""
    # 1. Create a document
    doc_res = await async_client.post(
        "/documents/",
        json={"title": "CRDT Sync Doc", "content": "Initial"},
        headers={"Authorization": f"Bearer {auth_details['token']}"},
    )
    doc_id = doc_res.json()["id"]

    # 2. Setup mock sockets
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()

    await manager.connect(doc_id, ws1)
    await manager.connect(doc_id, ws2)

    # 3. Simulate an update from Client 1
    # Create a Yjs update: append " Update"
    doc_state = doc_res.json().get("state")
    # Initial state should be sent on connection (handled by router, but here we test the manager/service)

    # Create an update blob
    y_manager = CRDTDocumentManager.from_text("Initial")
    update = Y.encode_state_as_update(y_manager.doc)
    update_b64 = base64.b64encode(update).decode("utf-8")

    # Send update via broadcast (simulating what the router does)
    payload = {
        "type": "update",
        "update": update_b64,
        "user_id": "test_user",
        "username": "test_user",
    }

    await manager.broadcast(doc_id, payload)

    # 4. Verify propagation
    assert len(ws1.sent_messages) == 1
    assert len(ws2.sent_messages) == 1
    assert ws1.sent_messages[0]["type"] == "update"
    assert ws1.sent_messages[0]["update"] == update_b64

    # 5. Verify persistence (Manual call to service since we are mocking WS)
    from src.modules.documents.services import apply_crdt_update

    # Client adds "!!!"
    with y_manager.doc.begin_transaction() as tr:
        y_manager.text.extend(tr, "!!!")
    new_update = Y.encode_state_as_update(y_manager.doc, update)

    await apply_crdt_update(mongo_db, doc_id, new_update)

    # Fetch from DB and verify content
    updated_doc = await get_document_by_id(mongo_db, doc_id)
    assert "Initial!!!" in updated_doc.content
    assert updated_doc.state is not None
