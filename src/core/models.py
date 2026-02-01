"""Shared models and types for the whole application."""

from typing import Annotated

from bson import ObjectId
from pydantic import BeforeValidator


def validate_object_id(v: str | ObjectId) -> str:
    """Validate and convert ObjectId to string."""
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str) and ObjectId.is_valid(v):
        return v
    raise ValueError("Invalid ObjectId")


# Standard type for MongoDB ObjectIDs used across modules
PyObjectId = Annotated[str, BeforeValidator(validate_object_id)]
