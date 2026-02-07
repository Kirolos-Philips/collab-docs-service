"""Document router - API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.database import get_database
from modules.auth.dependencies import get_current_active_user
from modules.auth.models import UserInDB
from modules.documents.dependencies import (
    get_document_for_access,
    get_document_for_edit,
    get_document_for_owner,
)
from modules.documents.models import DocumentInDB
from modules.documents.schemas import (
    CollaboratorUpdate,
    DocumentCreate,
    DocumentResponse,
    DocumentUpdate,
)
from modules.documents.services import (
    add_collaborator,
    create_document,
    delete_document,
    enrich_collaborators,
    list_user_documents,
    remove_collaborator,
    update_document,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_new_document(
    doc_data: DocumentCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: UserInDB = Depends(get_current_active_user),
):
    """Create a new document."""
    doc = await create_document(db, doc_data, str(current_user.id))
    return DocumentResponse(**doc.model_dump())


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: UserInDB = Depends(get_current_active_user),
):
    """List documents where user is owner or collaborator."""
    docs = await list_user_documents(db, str(current_user.id))
    return [DocumentResponse(**doc.model_dump()) for doc in docs]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document_details(
    db: AsyncIOMotorDatabase = Depends(get_database),
    doc: DocumentInDB = Depends(get_document_for_access),
):
    """Get document details."""
    enriched_collabs = await enrich_collaborators(db, doc)
    res = DocumentResponse(**doc.model_dump())
    res.collaborators = enriched_collabs
    return res


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document_content(
    document_id: str,
    update_data: DocumentUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    _doc: DocumentInDB = Depends(get_document_for_edit),
):
    """Update document content/title (Owner or Editor only)."""
    updated_doc = await update_document(db, document_id, update_data)
    if not updated_doc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update document",
        )
    return DocumentResponse(**updated_doc.model_dump())


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_document(
    document_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    _doc: DocumentInDB = Depends(get_document_for_owner),
):
    """Delete document (Owner only)."""
    success = await delete_document(db, document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document",
        )


@router.post("/{document_id}/collaborators", response_model=DocumentResponse)
async def manage_collaborators(
    document_id: str,
    collab_data: CollaboratorUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    _doc: DocumentInDB = Depends(get_document_for_owner),
):
    """Add or update a collaborator (Owner only)."""
    updated_doc = await add_collaborator(
        db, document_id, collab_data.email, collab_data.role
    )
    if not updated_doc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found or document error",
        )
    res = DocumentResponse(**updated_doc.model_dump())
    res.collaborators = await enrich_collaborators(db, updated_doc)
    return res


@router.delete(
    "/{document_id}/collaborators/{user_id}", response_model=DocumentResponse
)
async def remove_document_collaborator(
    document_id: str,
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    _doc: DocumentInDB = Depends(get_document_for_owner),
):
    """Remove a collaborator (Owner only)."""
    updated_doc = await remove_collaborator(db, document_id, user_id)
    if not updated_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document or collaborator not found",
        )
    enriched_collabs = await enrich_collaborators(db, updated_doc)
    res = DocumentResponse(**updated_doc.model_dump())
    res.collaborators = enriched_collabs
    return res
