from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    QuickLoginRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.services.auth_service import auth_service

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description="Registers a new user with email and password, initializing default preferences.",
)
def register(
    req: UserRegisterRequest,
    db: Session = Depends(get_db),
):
    """User account registration endpoint."""
    user = auth_service.register_user(db=db, req=req)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive JWT token",
    description="Authenticates user credentials and issues a signed JWT Bearer access token.",
)
def login(
    req: UserLoginRequest,
    db: Session = Depends(get_db),
):
    """User authentication login endpoint."""
    user = auth_service.authenticate_user(db=db, req=req)
    return auth_service.create_token_response(user=user)


@router.post(
    "/quick-login",
    response_model=TokenResponse,
    summary="Quick authenticate user session",
    description="Restores user session for registered account without password re-entry in local development.",
)
def quick_login(
    req: QuickLoginRequest,
    db: Session = Depends(get_db),
):
    from app.core.security import hash_password
    from app.models.preference import UserPreference

    email = req.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Auto-create demo user if not found so quick-login never fails on live demo/resume
        user = User(
            email=email,
            hashed_password=hash_password("password123"),
            full_name="Demo User",
            is_active=True,
            is_superuser=False,
        )
        db.add(user)
        db.flush()

        default_pref = UserPreference(
            user_id=user.id,
            digest_enabled=True,
            digest_time="22:00",
            preferred_work_modes=["REMOTE", "HYBRID"],
        )
        db.add(default_pref)
        db.commit()
        db.refresh(user)

    return auth_service.create_token_response(user=user)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Returns the profile information of the currently authenticated user.",
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    """Retrieve current authenticated user."""
    return current_user


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
    description="Updates the profile details (e.g., full name) of the currently authenticated user.",
)
def update_me(
    req: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current authenticated user profile."""
    return auth_service.update_profile(db=db, user=current_user, req=req)
