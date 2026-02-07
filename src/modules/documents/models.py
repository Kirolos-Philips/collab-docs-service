"""Document model for MongoDB."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from core.models import PyObjectId


class Collaborator(BaseModel):
    """Collaborator model."""

    user_id: str
    role: str  # "viewer", "editor"


class DocumentInDB(BaseModel):
    """Document document as stored in MongoDB."""

    model_config = ConfigDict(populate_by_name=True)

    id: PyObjectId | None = Field(default=None, alias="_id")
    title: str
    content: str = ""
    state: bytes | None = None  # Binary CRDT state
    owner_id: str
    collaborators: list[Collaborator] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_mongo(self) -> dict:
        """Convert to MongoDB document format."""
        from bson import ObjectId

        data = self.model_dump(by_alias=True, exclude_none=True)
        if data.get("_id"):
            data["_id"] = ObjectId(data["_id"])
        return data

    @classmethod
    def from_mongo(cls, doc: dict) -> "DocumentInDB":
        """Create instance from MongoDB document."""
        if doc is None:
            return None
        return cls(**doc)
