"""Document services - business logic for document management."""

from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.modules.auth.services import get_user_by_email
from src.modules.documents.models import Collaborator, DocumentInDB
from src.modules.documents.schemas import DocumentCreate, DocumentUpdate

DOCUMENTS_COLLECTION = "documents"


async def create_document(
    db: AsyncIOMotorDatabase, doc_data: DocumentCreate, owner_id: str
) -> DocumentInDB:
    """Create a new document."""
    now = datetime.utcnow()
    doc = DocumentInDB(
        title=doc_data.title,
        content=doc_data.content or "",
        owner_id=owner_id,
        collaborators=[],
        created_at=now,
        updated_at=now,
    )

    result = await db[DOCUMENTS_COLLECTION].insert_one(doc.to_mongo())
    doc.id = str(result.inserted_id)
    return doc


async def get_document_by_id(
    db: AsyncIOMotorDatabase, doc_id: str
) -> DocumentInDB | None:
    """Fetch document by ID."""
    if not ObjectId.is_valid(doc_id):
        return None
    doc = await db[DOCUMENTS_COLLECTION].find_one({"_id": ObjectId(doc_id)})
    return DocumentInDB.from_mongo(doc) if doc else None


async def list_user_documents(
    db: AsyncIOMotorDatabase, user_id: str
) -> list[DocumentInDB]:
    """List documents where user is owner or collaborator."""
    cursor = (
        db[DOCUMENTS_COLLECTION]
        .find(
            {
                "$or": [
                    {"owner_id": user_id},
                    {"collaborators.user_id": user_id},
                ]
            }
        )
        .sort("updated_at", -1)
    )

    docs = await cursor.to_list(length=100)
    return [DocumentInDB.from_mongo(d) for d in docs]


async def update_document(
    db: AsyncIOMotorDatabase, doc_id: str, update_data: DocumentUpdate
) -> DocumentInDB | None:
    """Update document content and metadata."""
    if not ObjectId.is_valid(doc_id):
        return None

    update_dict = update_data.model_dump(exclude_unset=True)
    if not update_dict:
        return await get_document_by_id(db, doc_id)

    update_dict["updated_at"] = datetime.utcnow()

    result = await db[DOCUMENTS_COLLECTION].find_one_and_update(
        {"_id": ObjectId(doc_id)},
        {"$set": update_dict},
        return_document=True,
    )

    return DocumentInDB.from_mongo(result) if result else None


async def delete_document(db: AsyncIOMotorDatabase, doc_id: str) -> bool:
    """Delete document by ID."""
    if not ObjectId.is_valid(doc_id):
        return False
    result = await db[DOCUMENTS_COLLECTION].delete_one({"_id": ObjectId(doc_id)})
    return result.deleted_count > 0


async def add_collaborator(
    db: AsyncIOMotorDatabase, doc_id: str, email: str, role: str
) -> DocumentInDB | None:
    """Add a collaborator to a document by email."""
    if not ObjectId.is_valid(doc_id):
        return None

    user = await get_user_by_email(db, email)
    if not user:
        return None

    user_id = str(user.id)

    # Check if already a collaborator
    doc = await get_document_by_id(db, doc_id)
    if not doc:
        return None

    if doc.owner_id == user_id:
        return doc  # Owner is already implied

    # Update or add collaborator
    # Using $set with arrayFilters if update, or $push if new?
    # Simplest: check if exists in list and update, else push.

    existing = next((c for c in doc.collaborators if c.user_id == user_id), None)

    if existing:
        await db[DOCUMENTS_COLLECTION].update_one(
            {"_id": ObjectId(doc_id), "collaborators.user_id": user_id},
            {"$set": {"collaborators.$.role": role, "updated_at": datetime.utcnow()}},
        )
    else:
        new_collaborator = Collaborator(user_id=user_id, role=role)
        await db[DOCUMENTS_COLLECTION].update_one(
            {"_id": ObjectId(doc_id)},
            {
                "$push": {"collaborators": new_collaborator.model_dump()},
                "$set": {"updated_at": datetime.utcnow()},
            },
        )

    return await get_document_by_id(db, doc_id)
