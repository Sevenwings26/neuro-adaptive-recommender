# repositories/user_repository.py
from sqlalchemy.orm import Session
from typing import Optional
from models.auth_models import User
from schemas.auth_schemas import UserCreate

class UserRepository:
    @staticmethod
    def get_by_id(db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_username(db: Session, username: str) -> Optional[User]:
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_by_username_or_email(db: Session, username_or_email: str) -> Optional[User]:
        return db.query(User).filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()

    @staticmethod
    def create(db: Session, user_in: UserCreate, hashed_password: str) -> User:
        db_user = User(
            username=user_in.username,
            email=user_in.email,
            hashed_password=hashed_password,
            role=user_in.role.value
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def update_refresh_token(db: Session, user_id: int, refresh_token: Optional[str]) -> None:
        db.query(User).filter(User.id == user_id).update({User.refresh_token: refresh_token})
        db.commit()
