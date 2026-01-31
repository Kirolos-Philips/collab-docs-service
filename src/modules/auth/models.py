"""User model for MongoDB."""

from datetime import datetime
from typing import Annotated

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field


def validate_object_id(v: str | ObjectId) -> str:
    """Validate and convert ObjectId to string."""
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str) and ObjectId.is_valid(v):
        return v
    raise ValueError("Invalid ObjectId")


PyObjectId = Annotated[str, BeforeValidator(validate_object_id)]


class UserInDB(BaseModel):
    """User document as stored in MongoDB."""

    model_config = ConfigDict(populate_by_name=True)

    id: PyObjectId = Field(default=None, alias="_id")
    email: EmailStr
    username: str
    hashed_password: str
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_mongo(self) -> dict:
        """Convert to MongoDB document format."""
        data = self.model_dump(by_alias=True, exclude_none=True)
        if data.get("_id"):
            data["_id"] = ObjectId(data["_id"])
        return data

    @classmethod
    def from_mongo(cls, doc: dict) -> "UserInDB":
        """Create instance from MongoDB document."""
        if doc is None:
            return None
        return cls(**doc)


class IdentityVerificationSession(BaseModel):
    """Temporary storage for verification data before user creation or sensitive actions."""

    model_config = ConfigDict(populate_by_name=True)

    id: PyObjectId = Field(default=None, alias="_id")
    email: EmailStr
    username: str
    hashed_password: str
    otp_code: str
    expires_at: datetime
    attempts: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_mongo(self) -> dict:
        """Convert to MongoDB document format."""
        data = self.model_dump(by_alias=True, exclude_none=True)
        if data.get("_id"):
            data["_id"] = ObjectId(data["_id"])
        return data

    @classmethod
    def from_mongo(cls, doc: dict) -> "IdentityVerificationSession":
        """Create instance from MongoDB document."""
        if doc is None:
            return None
        return cls(**doc)


class OTPCode(BaseModel):
    """OTP code for verification or password reset."""

    model_config = ConfigDict(populate_by_name=True)

    id: PyObjectId = Field(default=None, alias="_id")
    email: EmailStr
    code: str
    purpose: str  # "verification" or "reset"
    expires_at: datetime
    attempts: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_mongo(self) -> dict:
        """Convert to MongoDB document format."""
        data = self.model_dump(by_alias=True, exclude_none=True)
        if data.get("_id"):
            data["_id"] = ObjectId(data["_id"])
        return data

    @classmethod
    def from_mongo(cls, doc: dict) -> "OTPCode":
        """Create instance from MongoDB document."""
        if doc is None:
            return None
        return cls(**doc)
