"""Auth services - business logic for user management."""

from datetime import datetime, timedelta

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.core.email import send_email
from src.modules.auth.models import IdentityVerificationSession, OTPCode, UserInDB
from src.modules.auth.schemas import UserCreate
from src.modules.auth.security import hash_password, verify_password

USERS_COLLECTION = "users"
OTPS_COLLECTION = "otps"
IDENTITY_VERIFICATION_SESSIONS_COLLECTION = "identity_verification_sessions"


async def get_user_by_email(db: AsyncIOMotorDatabase, email: str) -> UserInDB | None:
    """Get user by email."""
    doc = await db[USERS_COLLECTION].find_one({"email": email})
    return UserInDB.from_mongo(doc) if doc else None


async def get_user_by_id(db: AsyncIOMotorDatabase, user_id: str) -> UserInDB | None:
    """Get user by ID."""
    if not ObjectId.is_valid(user_id):
        return None
    doc = await db[USERS_COLLECTION].find_one({"_id": ObjectId(user_id)})
    return UserInDB.from_mongo(doc) if doc else None


async def get_user_by_username(
    db: AsyncIOMotorDatabase, username: str
) -> UserInDB | None:
    """Get user by username."""
    doc = await db[USERS_COLLECTION].find_one({"username": username})
    return UserInDB.from_mongo(doc) if doc else None


async def initiate_registration(
    db: AsyncIOMotorDatabase, user_data: UserCreate
) -> bool:
    """Initiate registration by saving to verification session and sending OTP."""
    now = datetime.utcnow()
    otp_code = "123456"  # Static for testing

    # Upsert verification session (in case user retries)
    session = IdentityVerificationSession(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hash_password(user_data.password),
        otp_code=otp_code,
        expires_at=now + timedelta(minutes=10),
        attempts=0,
        created_at=now,
    )

    await db[IDENTITY_VERIFICATION_SESSIONS_COLLECTION].update_one(
        {"email": user_data.email}, {"$set": session.to_mongo()}, upsert=True
    )

    # Send email
    await send_email(
        recipient_email=user_data.email,
        subject="Verify your email",
        body=f"Your verification code is: {otp_code}",
    )

    return True


async def verify_email(db: AsyncIOMotorDatabase, email: str, otp: str) -> bool:
    """Verify email and finally create user in DB."""
    doc = await db[IDENTITY_VERIFICATION_SESSIONS_COLLECTION].find_one({"email": email})
    if not doc:
        return False

    session = IdentityVerificationSession.from_mongo(doc)
    now = datetime.utcnow()

    # Check expiration and trials
    if session.expires_at < now or session.attempts >= 3:
        await db[IDENTITY_VERIFICATION_SESSIONS_COLLECTION].delete_one({"email": email})
        return False

    if session.otp_code != otp:
        await db[IDENTITY_VERIFICATION_SESSIONS_COLLECTION].update_one(
            {"email": email}, {"$inc": {"attempts": 1}}
        )
        return False

    # Success: create real user and delete session data
    user = UserInDB(
        email=session.email,
        username=session.username,
        hashed_password=session.hashed_password,
        is_active=True,
        is_verified=True,
        created_at=now,
        updated_at=now,
    )

    await db[USERS_COLLECTION].insert_one(user.to_mongo())
    await db[IDENTITY_VERIFICATION_SESSIONS_COLLECTION].delete_one({"email": email})
    return True


async def authenticate_user(
    db: AsyncIOMotorDatabase, email: str, password: str
) -> UserInDB | None:
    """Authenticate user by email and password."""
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active or not user.is_verified:
        return None
    return user


async def initiate_password_reset(db: AsyncIOMotorDatabase, email: str) -> bool:
    """Initiate password reset by setting an OTP."""
    user = await get_user_by_email(db, email)
    if not user:
        return False

    now = datetime.utcnow()
    # Delete old reset OTPs if any
    await db[OTPS_COLLECTION].delete_many({"email": email, "purpose": "reset"})

    otp_code = "123456"  # Static for testing
    otp_doc = OTPCode(
        email=email,
        code=otp_code,
        purpose="reset",
        expires_at=now + timedelta(minutes=10),
    )
    await db[OTPS_COLLECTION].insert_one(otp_doc.to_mongo())

    # Send email
    await send_email(
        recipient_email=email,
        subject="Reset your password",
        body=f"Your password reset code is: {otp_code}",
    )

    return True


async def reset_password(
    db: AsyncIOMotorDatabase, email: str, otp: str, new_password: str
) -> bool:
    """Reset password with OTP verification."""
    otp_doc = await db[OTPS_COLLECTION].find_one({"email": email, "purpose": "reset"})
    if not otp_doc:
        return False

    otp_obj = OTPCode.from_mongo(otp_doc)
    now = datetime.utcnow()

    if otp_obj.expires_at < now or otp_obj.attempts >= 3:
        await db[OTPS_COLLECTION].delete_one({"_id": ObjectId(otp_obj.id)})
        return False

    if otp_obj.code != otp:
        await db[OTPS_COLLECTION].update_one(
            {"_id": ObjectId(otp_obj.id)}, {"$inc": {"attempts": 1}}
        )
        return False

    # Success: update password and delete OTP
    await db[USERS_COLLECTION].update_one(
        {"email": email},
        {
            "$set": {
                "hashed_password": hash_password(new_password),
                "updated_at": now,
            }
        },
    )
    await db[OTPS_COLLECTION].delete_one({"_id": ObjectId(otp_obj.id)})
    return True


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    """Create indexes for auth collections."""
    await db[USERS_COLLECTION].create_index("email", unique=True)
    await db[USERS_COLLECTION].create_index("username", unique=True)
    # OTP index for TTL and lookup
    await db[OTPS_COLLECTION].create_index([("email", 1), ("purpose", 1)])
