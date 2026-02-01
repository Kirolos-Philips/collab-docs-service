"""Document router - API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.core.database import get_database
from src.modules.auth.dependencies import get_current_active_user
from src.modules.auth.models import UserInDB
from src.modules.documents.dependencies import (
    get_document_for_access,
    get_document_for_edit,
    get_document_for_owner,
)
from src.modules.documents.models import DocumentInDB
from src.modules.documents.schemas import (
    CollaboratorUpdate,
    DocumentCreate,
    DocumentResponse,
    DocumentUpdate,
)
from src.modules.documents.services import (
    add_collaborator,
    create_document,
    delete_document,
    list_user_documents,
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
    doc: DocumentInDB = Depends(get_document_for_access),
):
    """Get document details."""
    return DocumentResponse(**doc.model_dump())


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
    return DocumentResponse(**updated_doc.model_dump())
