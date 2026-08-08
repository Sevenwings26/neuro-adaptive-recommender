# routers/auth_router.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from database import get_db
from schemas.auth_schemas import (
    UserCreate, UserLogin, UserResponse, 
    TokenResponse, TokenRefreshRequest, MessageResponse
)
from services.auth_service import AuthService, get_current_user
from repositories.user_repository import UserRepository
from models.auth_models import User

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user (Clinician or Parent)."""
    return AuthService.register_user(db, user_in)

@auth_router.post("/login", response_model=TokenResponse)
def login(login_in: UserLogin, db: Session = Depends(get_db)):
    """Authenticate credentials and return JWT access/refresh tokens."""
    user = AuthService.authenticate_user(db, login_in.username_or_email, login_in.password)
    tokens = AuthService.create_tokens(user)
    # Persist refresh token in DB
    UserRepository.update_refresh_token(db, user.id, tokens.refresh_token)
    return tokens

@auth_router.post("/refresh", response_model=TokenResponse)
def refresh(refresh_in: TokenRefreshRequest, db: Session = Depends(get_db)):
    """Refresh expired access token using a valid refresh token."""
    return AuthService.refresh_tokens(db, refresh_in.refresh_token)

@auth_router.post("/logout", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Invalidate current user refresh token (logout)."""
    UserRepository.update_refresh_token(db, current_user.id, None)
    return MessageResponse(detail="Logged out successfully.")

@auth_router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve details of the currently authenticated user."""
    return current_user
