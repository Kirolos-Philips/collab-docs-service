"""Pydantic schemas for documents module."""

from datetime import datetime

from pydantic import BaseModel, Field


class CollaboratorBase(BaseModel):
    """Base schema for collaborator."""

    user_id: str
    role: str


class DocumentBase(BaseModel):
    """Base schema for document."""

    title: str = Field(..., min_length=1, max_length=255)
    content: str | None = ""


class DocumentCreate(DocumentBase):
    """Schema for document creation."""

    pass


class DocumentUpdate(BaseModel):
    """Schema for document update."""

    title: str | None = Field(None, min_length=1, max_length=255)
    content: str | None = None


class DocumentResponse(DocumentBase):
    """Schema for document response."""

    id: str
    owner_id: str
    collaborators: list[CollaboratorBase]
    created_at: datetime
    updated_at: datetime


class CollaboratorUpdate(BaseModel):
    """Schema for adding/updating a collaborator."""

    email: str
    role: str = Field("viewer", pattern="^(viewer|editor)$")
