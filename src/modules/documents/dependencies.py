"""Auth dependencies for Documents Module."""

from fastapi import Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.core.database import get_database
from src.modules.auth.dependencies import get_current_active_user
from src.modules.auth.models import UserInDB
from src.modules.documents.models import DocumentInDB
from src.modules.documents.services import get_document_by_id


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
