from sqlalchemy.orm import Session
from backend.app.models.user import User
from backend.app.schemas.user import UserCreate
from backend.app.core.security import get_password_hash
from datetime import datetime, timezone


def get_user_by_email(db: Session, email: str) -> User:
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, user_in: UserCreate) -> User:
    hashed_password = get_password_hash(user_in.password)
    user = User(
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        email=user_in.email,
        password=hashed_password,
        role=user_in.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_user_with_password(db: Session, user_in: UserCreate, password: str) -> User:
    hashed_password = get_password_hash(password)
    db_user = User(
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        email=user_in.email,
        password=hashed_password,
        role=user_in.role,
        is_first_login=True,
        is_active=True,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_password(db: Session, user: User, new_password: str) -> User:
    user.password = get_password_hash(new_password)
    user.is_first_login = False
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user
