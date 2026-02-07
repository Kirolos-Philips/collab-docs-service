"""Document schemas - request and response models."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CollaboratorBase(BaseModel):
    """Base schema for collaborator info."""

    user_id: str
    role: str
    email: str | None = None
    username: str | None = None
    avatar_url: str | None = None


class DocumentBase(BaseModel):
    """Base schema for document properties."""

    title: str
    content: str = ""


class DocumentCreate(DocumentBase):
    """Schema for creating a new document."""

    pass


class DocumentUpdate(BaseModel):
    """Schema for updating a document."""

    title: str | None = None
    content: str | None = None


class DocumentResponse(DocumentBase):
    """Schema for document response."""

    id: str
    owner_id: str
    collaborators: list[CollaboratorBase] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "60b8d545f1d2a12345678901",
                "title": "My Document",
                "content": "Hello World",
                "owner_id": "60b8d545f1d2a12345678902",
                "collaborators": [
                    {"user_id": "60b8d545f1d2a12345678903", "role": "editor"}
                ],
                "created_at": "2024-05-20T10:00:00",
                "updated_at": "2024-05-21T10:00:00",
            }
        },
    )


class CollaboratorUpdate(BaseModel):
    """Schema for adding/updating a collaborator."""

    email: str
    role: str
