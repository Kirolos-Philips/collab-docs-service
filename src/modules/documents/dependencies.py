"""Auth dependencies for Documents Module."""

from fastapi import Depends, HTTPException, WebSocket, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.database import get_database
from modules.auth.dependencies import get_current_active_user
from modules.auth.models import UserInDB
from modules.auth.security import decode_access_token
from modules.auth.services import get_user_by_id
from modules.documents.models import DocumentInDB
from modules.documents.services import get_document_by_id


async def get_document_for_access(
    document_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: UserInDB = Depends(get_current_active_user),
) -> DocumentInDB:
    """Dependency to check if user has access to a document (owner or collaborator)."""
    doc = await get_document_by_id(db, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    user_id = str(current_user.id)
    is_owner = doc.owner_id == user_id
    is_collaborator = any(c.user_id == user_id for c in doc.collaborators)

    if not (is_owner or is_collaborator):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this document",
        )

    return doc


async def get_document_for_edit(
    doc: DocumentInDB = Depends(get_document_for_access),
    current_user: UserInDB = Depends(get_current_active_user),
) -> DocumentInDB:
    """Dependency to check if user has edit access (owner or editor role)."""
    user_id = str(current_user.id)

    if doc.owner_id == user_id:
        return doc

    collaborator = next((c for c in doc.collaborators if c.user_id == user_id), None)
    if not collaborator or collaborator.role != "editor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit this document",
        )

    return doc


async def get_document_for_owner(
    doc: DocumentInDB = Depends(get_document_for_access),
    current_user: UserInDB = Depends(get_current_active_user),
) -> DocumentInDB:
    """Dependency to check if user is the owner of the document."""
    if doc.owner_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can perform this action",
        )
    return doc


async def get_ws_authenticated_doc(
    websocket: WebSocket,
    document_id: str,
    token: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> tuple[UserInDB, DocumentInDB] | None:
    """Validate WebSocket token and document access. Closes connection on failure."""
    if not token:
        await websocket.close(code=4001, reason="Authentication token missing")
        return None

    user_id = decode_access_token(token)
    if not user_id:
        await websocket.close(code=4002, reason="Invalid token")
        return None

    user = await get_user_by_id(db, user_id)
    if not user or not user.is_active:
        await websocket.close(code=4003, reason="User unauthorized or inactive")
        return None

    doc = await get_document_by_id(db, document_id)
    if not doc:
        await websocket.close(code=4004, reason="Document not found")
        return None

    user_id_str = str(user.id)
    is_owner = doc.owner_id == user_id_str
    is_collaborator = any(c.user_id == user_id_str for c in doc.collaborators)

    if not (is_owner or is_collaborator):
        await websocket.close(code=4005, reason="Document access denied")
        return None

    return user, doc
