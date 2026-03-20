from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime
from backend.app.db.base import Base
from enum import Enum as PyEnum


class Role(str, PyEnum):
    # Rôles disponibles dans l'application — contrôlent les droits d'accès aux endpoints
    ADMIN = "admin"
    DOCTOR = "doctor"
    PHARMACIST = "pharmacist"


class User(Base):
    # Compte utilisateur de la plateforme SafeRx AI
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)
    password = Column(String, nullable=False)  # hash argon2
    role = Column(Enum(Role), nullable=False)
    is_active = Column(Boolean, default=True)
    is_first_login = Column(
        Boolean, default=True
    )  # True = doit changer son MDP à la première connexion
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
