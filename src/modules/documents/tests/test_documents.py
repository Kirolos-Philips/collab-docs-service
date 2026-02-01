"""Tests for documents module."""

import pytest
from httpx import AsyncClient

# We use the async_client fixture from conftest.py which handles db setup/teardown


@pytest.fixture
async def auth_headers(async_client: AsyncClient):
    """Register and login a test user to get auth headers."""
    user_data = {
        "email": "owner@example.com",
        "username": "owneruser",
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
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def other_auth_headers(async_client: AsyncClient):
    """Register and login another test user."""
    user_data = {
        "email": "other@example.com",
        "username": "otheruser",
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
    return {"Authorization": f"Bearer {token}"}


class TestDocumentCRUD:
    """Test document creation, listing, updating, and deletion."""

    @pytest.mark.asyncio
    async def test_create_document(self, async_client: AsyncClient, auth_headers: dict):
        """Test successful document creation."""
        doc_data = {"title": "Test Doc", "content": "Initial content"}
        response = await async_client.post(
            "/documents/", json=doc_data, headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == doc_data["title"]
        assert data["content"] == doc_data["content"]
        assert "id" in data
        assert "owner_id" in data

    @pytest.mark.asyncio
    async def test_list_documents(self, async_client: AsyncClient, auth_headers: dict):
        """Test listing documents."""
        # Create a doc first
        await async_client.post(
            "/documents/", json={"title": "Doc 1"}, headers=auth_headers
        )

        response = await async_client.get("/documents/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["title"] == "Doc 1"

    @pytest.mark.asyncio
    async def test_get_document_details(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test getting specific document."""
        create_res = await async_client.post(
            "/documents/", json={"title": "Detailed Doc"}, headers=auth_headers
        )
        doc_id = create_res.json()["id"]

        response = await async_client.get(f"/documents/{doc_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["title"] == "Detailed Doc"

    @pytest.mark.asyncio
    async def test_update_document(self, async_client: AsyncClient, auth_headers: dict):
        """Test updating document content."""
        create_res = await async_client.post(
            "/documents/", json={"title": "Old Title"}, headers=auth_headers
        )
        doc_id = create_res.json()["id"]

        update_data = {"title": "New Title", "content": "Updated content"}
        response = await async_client.patch(
            f"/documents/{doc_id}", json=update_data, headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["title"] == "New Title"
        assert response.json()["content"] == "Updated content"

    @pytest.mark.asyncio
    async def test_delete_document(self, async_client: AsyncClient, auth_headers: dict):
        """Test deleting document."""
        create_res = await async_client.post(
            "/documents/", json={"title": "To Delete"}, headers=auth_headers
        )
        doc_id = create_res.json()["id"]

        response = await async_client.delete(
            f"/documents/{doc_id}", headers=auth_headers
        )
        assert response.status_code == 204

        # Verify it's gone
        get_res = await async_client.get(f"/documents/{doc_id}", headers=auth_headers)
        assert get_res.status_code == 404


class TestDocumentPermissions:
    """Test document access control and collaborator roles."""

    @pytest.mark.asyncio
    async def test_unauthorized_access(
        self, async_client: AsyncClient, auth_headers: dict, other_auth_headers: dict
    ):
        """Test that user cannot access documents they don't own/collaborate on."""
        # User 1 creates a doc
        create_res = await async_client.post(
            "/documents/", json={"title": "Private Doc"}, headers=auth_headers
        )
        doc_id = create_res.json()["id"]

        # User 2 tries to access it
        response = await async_client.get(
            f"/documents/{doc_id}", headers=other_auth_headers
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_add_collaborator(
        self, async_client: AsyncClient, auth_headers: dict, other_auth_headers: dict
    ):
        """Test adding a collaborator."""
        # Create doc
        create_res = await async_client.post(
            "/documents/", json={"title": "Shared Doc"}, headers=auth_headers
        )
        doc_id = create_res.json()["id"]

        # Add User 2 as editor
        collab_data = {"email": "other@example.com", "role": "editor"}
        response = await async_client.post(
            f"/documents/{doc_id}/collaborators", json=collab_data, headers=auth_headers
        )
        assert response.status_code == 200
        assert len(response.json()["collaborators"]) == 1

        # Verify User 2 can now access it
        get_res = await async_client.get(
            f"/documents/{doc_id}", headers=other_auth_headers
        )
        assert get_res.status_code == 200

    @pytest.mark.asyncio
    async def test_viewer_cannot_edit(
        self, async_client: AsyncClient, auth_headers: dict, other_auth_headers: dict
    ):
        """Test that a viewer cannot update content."""
        # Create doc
        create_res = await async_client.post(
            "/documents/", json={"title": "View Only Doc"}, headers=auth_headers
        )
        doc_id = create_res.json()["id"]

        # Add User 2 as viewer
        await async_client.post(
            f"/documents/{doc_id}/collaborators",
            json={"email": "other@example.com", "role": "viewer"},
            headers=auth_headers,
        )

        # User 2 tries to update
        update_res = await async_client.patch(
            f"/documents/{doc_id}",
            json={"content": "Hacked!"},
            headers=other_auth_headers,
        )
        assert update_res.status_code == 403

    @pytest.mark.asyncio
    async def test_editor_can_edit_but_not_delete(
        self, async_client: AsyncClient, auth_headers: dict, other_auth_headers: dict
    ):
        """Test that an editor can update but not delete or add collaborators."""
        # Create doc
        create_res = await async_client.post(
            "/documents/", json={"title": "Collaborative Doc"}, headers=auth_headers
        )
        doc_id = create_res.json()["id"]

        # Add User 2 as editor
        await async_client.post(
            f"/documents/{doc_id}/collaborators",
            json={"email": "other@example.com", "role": "editor"},
            headers=auth_headers,
        )

        # User 2 updates content (should succeed)
        update_res = await async_client.patch(
            f"/documents/{doc_id}",
            json={"content": "Collaborative edit"},
            headers=other_auth_headers,
        )
        assert update_res.status_code == 200

        # User 2 tries to delete (should fail)
        delete_res = await async_client.delete(
            f"/documents/{doc_id}", headers=other_auth_headers
        )
        assert delete_res.status_code == 403

        # User 2 tries to add another collaborator (should fail)
        collab_res = await async_client.post(
            f"/documents/{doc_id}/collaborators",
            json={"email": "third@example.com", "role": "editor"},
            headers=other_auth_headers,
        )
        assert collab_res.status_code == 403
