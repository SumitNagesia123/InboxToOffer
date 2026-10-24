from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.errors import AuthenticationError, ConflictError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.preference import UserPreference
from app.models.user import User
from app.schemas.auth import TokenResponse, UserLoginRequest, UserRegisterRequest, UserUpdateRequest


class AuthService:
    """Service handling user account registration, authentication, and token generation."""

    @staticmethod
    def register_user(db: Session, req: UserRegisterRequest) -> User:
        """Registers a new user and sets up default preferences."""
        normalized_email = req.email.lower().strip()

        # Check existing user
        existing_user = db.scalar(select(User).where(User.email == normalized_email))
        if existing_user:
            raise ConflictError(f"An account with email '{normalized_email}' already exists")

        # Hash password and create User
        hashed_pw = hash_password(req.password)
        new_user = User(
            email=normalized_email,
            hashed_password=hashed_pw,
            full_name=req.full_name.strip() if req.full_name else None,
            is_active=True,
            is_superuser=False,
        )
        db.add(new_user)
        db.flush()  # Populates new_user.id

        # Initialize default user preference for daily digest
        default_pref = UserPreference(
            user_id=new_user.id,
            digest_enabled=True,
            digest_time="22:00",
            preferred_work_modes=["REMOTE", "HYBRID"],
        )
        db.add(default_pref)
        db.commit()
        db.refresh(new_user)
        return new_user

    @staticmethod
    def authenticate_user(db: Session, req: UserLoginRequest) -> User:
        """Validates credentials and returns the active user."""
        normalized_email = req.email.lower().strip()
        user = db.scalar(select(User).where(User.email == normalized_email))

        if not user or not verify_password(req.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("Your account has been deactivated")

        return user

    @staticmethod
    def create_token_response(user: User) -> TokenResponse:
        """Creates a signed JWT Bearer token for the user."""
        access_token = create_access_token(subject=str(user.id))
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @staticmethod
    def update_profile(db: Session, user: User, req: UserUpdateRequest) -> User:
        """Updates user profile details."""
        if req.full_name is not None:
            user.full_name = req.full_name.strip()
        db.commit()
        db.refresh(user)
        return user


auth_service = AuthService()
